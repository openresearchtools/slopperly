"""Validate Slopperly runtime/model registry completeness."""

from __future__ import annotations

import argparse
from pathlib import Path

from slopperly.config.registry import model_entries
from slopperly.models.download import (
    auxiliary_entries,
    hf_file_source_and_target,
    huggingface_repo_id,
    is_exact_file,
    is_safe_relative_file,
)

ALLOWED_RUNTIMES = {"comfy", "vllm", "vllm_omni", "llamacpp"}
ALLOWED_DOWNLOAD_MODES = {"hf_file", "hf_snapshot"}
REQUIRED_FIELDS = (
    "logical_name",
    "legacy_aliases",
    "task",
    "runtime",
    "model_source",
    "download_mode",
    "local_cache_path",
    "required_files",
    "required_node_pack",
    "default_parameters",
    "minimum_vram_gb",
    "validation_command",
    "workflows",
)


def validate_model_registry(root: Path) -> list[str]:
    errors: list[str] = []
    entries = model_entries(root)
    if not entries:
        return ["slopperly/config/models.yaml has no model entries"]
    seen: set[str] = set()
    for entry in entries:
        name = str(entry.get("logical_name") or "<unnamed>")
        if name in seen:
            errors.append(f"{name}: duplicate logical_name")
        seen.add(name)
        for field in REQUIRED_FIELDS:
            if field not in entry:
                errors.append(f"{name}: missing required field {field!r}")
        runtime = str(entry.get("runtime") or "")
        if runtime not in ALLOWED_RUNTIMES:
            errors.append(f"{name}: unsupported runtime {runtime!r}")
        _validate_artifact_spec(name, entry, errors)
        aux_sources = entry.get("auxiliary_sources")
        if aux_sources is not None and not isinstance(aux_sources, list):
            errors.append(f"{name}: auxiliary_sources must be a list")
        for auxiliary in auxiliary_entries(entry):
            aux_name = f"{name}:{auxiliary.get('id') or 'auxiliary'}"
            if "id" not in auxiliary:
                errors.append(f"{aux_name}: auxiliary artifact missing required field 'id'")
            _validate_artifact_spec(aux_name, auxiliary, errors)
        legacy_aliases = entry.get("legacy_aliases")
        if not isinstance(legacy_aliases, list):
            errors.append(f"{name}: legacy_aliases must be a list")
        default_parameters = entry.get("default_parameters")
        if not isinstance(default_parameters, dict):
            errors.append(f"{name}: default_parameters must be a mapping")
        workflows = entry.get("workflows")
        if not isinstance(workflows, list) or not workflows:
            errors.append(f"{name}: workflows must be a non-empty list")
        validation = str(entry.get("validation_command") or "")
        if not validation.startswith("pytest tests/gpu/"):
            errors.append(f"{name}: validation_command must call a GPU plugin-path pytest")
        required_certifications = entry.get("required_certifications")
        if required_certifications is not None:
            if (
                not isinstance(required_certifications, list)
                or not required_certifications
                or not all(isinstance(item, str) and item.strip() for item in required_certifications)
            ):
                errors.append(f"{name}: required_certifications must be a non-empty list of names")
        try:
            if float(entry.get("minimum_vram_gb", 0)) <= 0:
                errors.append(f"{name}: minimum_vram_gb must be positive")
        except (TypeError, ValueError):
            errors.append(f"{name}: minimum_vram_gb must be numeric")
    return errors


def _validate_artifact_spec(name: str, entry: dict, errors: list[str]) -> None:
    for field in ("model_source", "download_mode", "local_cache_path", "required_files"):
        if field not in entry:
            errors.append(f"{name}: missing artifact field {field!r}")
    source = str(entry.get("model_source") or "")
    mode = str(entry.get("download_mode") or "")
    if mode not in ALLOWED_DOWNLOAD_MODES:
        errors.append(f"{name}: unsupported download_mode {mode!r}")
    if mode.startswith("hf_") and not huggingface_repo_id(source):
        errors.append(f"{name}: model_source must be a Hugging Face artifact URL")
    local_cache = Path(str(entry.get("local_cache_path") or ""))
    if not str(local_cache) or local_cache.is_absolute() or ".." in local_cache.parts:
        errors.append(f"{name}: local_cache_path must be a relative path inside the model cache")
    required_files = entry.get("required_files")
    if not isinstance(required_files, list) or not required_files:
        errors.append(f"{name}: required_files must be a non-empty list")
    elif mode == "hf_file":
        for filename in required_files:
            file_spec = hf_file_source_and_target(filename)
            if file_spec is None:
                errors.append(f"{name}: hf_file required file is not exact: {filename!r}")
                continue
            source_file, target_file = file_spec
            if not is_safe_relative_file(source_file) or not is_exact_file(target_file):
                errors.append(f"{name}: hf_file required file is not exact: {filename!r}")
    elif mode == "hf_snapshot":
        for filename in required_files:
            if not is_safe_relative_file(str(filename)):
                errors.append(
                    f"{name}: hf_snapshot evidence file is unsafe or generic: {filename!r}"
                )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Slopperly model registry")
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    errors = validate_model_registry(root)
    if errors:
        for error in errors:
            print(f"FAIL {error}")
        return 1
    print(f"Validated {len(model_entries(root))} model registry entries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
