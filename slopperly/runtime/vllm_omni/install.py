"""Installer recipe for the Slopperly vLLM-Omni runtime venv."""

from __future__ import annotations

import argparse
from pathlib import Path

from slopperly.runtime.install_utils import (
    InstallStep,
    create_venv,
    has_blockers,
    pip_install,
    print_steps,
    venv_pip,
    write_manifest,
)

VLLM_OMNI_VERSION = "0.22.0"
VLLM_VERSION = "0.22.0"
VLLM_OMNI_PACKAGES = [
    f"vllm-omni=={VLLM_OMNI_VERSION}",
    f"vllm=={VLLM_VERSION}",
]

OMNIVOICE_PIPELINE_RELATIVE = (
    "site-packages/vllm_omni/diffusion/models/omnivoice/pipeline_omnivoice.py"
)
OMNIVOICE_CONTROL_PATCH_MARKER = "Slopperly patch: request-time OmniVoice sampling controls"


def _site_packages_roots(venv_dir: Path) -> list[Path]:
    lib_dir = venv_dir / "lib"
    if not lib_dir.is_dir():
        return []
    return [path for path in lib_dir.glob("python*/site-packages") if path.is_dir()]


def patch_omnivoice_sampling_controls(venv_dir: Path, *, dry_run: bool = False) -> InstallStep:
    """Patch vLLM-Omni 0.22 OmniVoice to honor request steps/guidance extras."""
    candidates = [root / OMNIVOICE_PIPELINE_RELATIVE.removeprefix("site-packages/") for root in _site_packages_roots(venv_dir)]
    pipeline_path = next((path for path in candidates if path.is_file()), None)
    if dry_run:
        return InstallStep(
            "PLAN",
            "omnivoice-patch",
            f"patch {venv_dir}/lib/python*/{OMNIVOICE_PIPELINE_RELATIVE}",
        )
    if pipeline_path is None:
        return InstallStep(
            "BLOCKED",
            "omnivoice-patch",
            f"missing vLLM-Omni OmniVoice pipeline under {venv_dir}",
        )

    source = pipeline_path.read_text(encoding="utf-8")
    if OMNIVOICE_CONTROL_PATCH_MARKER in source:
        return InstallStep("PASS", "omnivoice-patch", f"already patched {pipeline_path}")

    seed_block = '''        extra = req.sampling_params.extra_args or {}
        seed = extra.get("seed", None)
'''
    patched_seed_block = f'''        extra = req.sampling_params.extra_args or {{}}
        seed = extra.get("seed", None)
        # {OMNIVOICE_CONTROL_PATCH_MARKER}.
        num_step = int(extra.get("num_step", self.num_step))
        guidance_scale = float(extra.get("guidance_scale", self.guidance_scale))
'''
    generator_block = '''            num_step=self.num_step,
            guidance_scale=self.guidance_scale,
'''
    patched_generator_block = '''            num_step=num_step,
            guidance_scale=guidance_scale,
'''
    if seed_block not in source or generator_block not in source:
        return InstallStep(
            "BLOCKED",
            "omnivoice-patch",
            f"vLLM-Omni OmniVoice pipeline changed; manual patch review required at {pipeline_path}",
        )
    source = source.replace(seed_block, patched_seed_block, 1)
    source = source.replace(generator_block, patched_generator_block, 1)
    pipeline_path.write_text(source, encoding="utf-8")
    return InstallStep("PASS", "omnivoice-patch", f"patched {pipeline_path}")


def install_vllm_omni(
    *,
    venv_dir: Path,
    dry_run: bool = False,
    skip_pip: bool = False,
) -> list[InstallStep]:
    steps = [create_venv(venv_dir, dry_run=dry_run)]
    if not skip_pip:
        steps.append(pip_install(venv_pip(venv_dir), VLLM_OMNI_PACKAGES, dry_run=dry_run))
    steps.append(patch_omnivoice_sampling_controls(venv_dir, dry_run=dry_run))
    steps.append(
        write_manifest(
            venv_dir.parent / "vllm-omni-install-manifest.json",
            {
                "runtime": "vllm_omni",
                "venv": str(venv_dir),
                "packages": VLLM_OMNI_PACKAGES,
                "patches": [OMNIVOICE_CONTROL_PATCH_MARKER],
            },
            dry_run=dry_run,
        )
    )
    return steps


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create/install Slopperly vLLM-Omni venv")
    parser.add_argument("--venv", default=".slopperly/vllm-omni-venv")
    parser.add_argument("--skip-pip", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args(argv)

    steps = install_vllm_omni(
        venv_dir=Path(args.venv),
        dry_run=args.dry_run,
        skip_pip=args.skip_pip,
    )
    print_steps(steps, title="vLLM-Omni install")
    if has_blockers(steps) and not args.report_only:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
