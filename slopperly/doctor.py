"""Slopperly local-only runtime doctor."""

from __future__ import annotations

import argparse
import json
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from slopperly.audit.local_only_surface import audit as local_only_surface_audit
from slopperly.audit.no_cloud import scan as no_cloud_scan
from slopperly.audit.workflow_packs import validate_workflow_pack
from slopperly.config.registry import load_runtimes_config
from slopperly.runtime.local_url import assert_local_http_url


@dataclass
class DoctorCheck:
    status: str
    name: str
    detail: str


def _runtime_url(config: dict, runtime_id: str) -> str:
    data = config.get(runtime_id) or {}
    host = data.get("host", "127.0.0.1")
    port = data.get("port")
    if not port:
        return ""
    return f"http://{host}:{port}"


def _get_json(url: str, path: str, timeout: float) -> dict:
    with urllib.request.urlopen(url.rstrip("/") + path, timeout=timeout) as resp:
        body = resp.read()
    return json.loads(body.decode("utf-8")) if body else {}


def check_local_only(root: Path) -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    remote_failures = local_only_surface_audit(root)
    if remote_failures:
        checks.append(DoctorCheck("FAIL", "local_only_surface", "; ".join(remote_failures[:5])))
    else:
        checks.append(DoctorCheck("PASS", "local_only_surface", "no legacy remote backend production surface"))

    cloud_hits = no_cloud_scan(root)
    if cloud_hits:
        first = cloud_hits[0]
        checks.append(
            DoctorCheck(
                "FAIL",
                "no_cloud",
                f"{first[0]}:{first[1]} matched {first[2]!r}",
            )
        )
    else:
        checks.append(DoctorCheck("PASS", "no_cloud", "no production cloud inference references"))
    return checks


def check_cuda() -> DoctorCheck:
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader",
            ],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=10,
        ).strip()
    except FileNotFoundError:
        return DoctorCheck("BLOCKED", "cuda", "nvidia-smi is not installed or not on PATH")
    except subprocess.CalledProcessError as exc:
        return DoctorCheck("BLOCKED", "cuda", f"nvidia-smi failed: {exc.output.strip()}")
    except subprocess.TimeoutExpired:
        return DoctorCheck("BLOCKED", "cuda", "nvidia-smi timed out")
    if not out:
        return DoctorCheck("BLOCKED", "cuda", "nvidia-smi returned no GPU rows")
    return DoctorCheck("PASS", "cuda", out.splitlines()[0])


def check_workflow_packs(root: Path) -> list[DoctorCheck]:
    workflow_root = root / "slopperly" / "workflows" / "comfy"
    if not workflow_root.is_dir():
        return [DoctorCheck("FAIL", "workflow_packs", f"missing {workflow_root}")]
    checks: list[DoctorCheck] = []
    count = 0
    failures: list[str] = []
    for pack in sorted(p for p in workflow_root.iterdir() if p.is_dir()):
        count += 1
        failures.extend(validate_workflow_pack(pack))
    if failures:
        checks.append(DoctorCheck("FAIL", "workflow_packs", "; ".join(failures[:5])))
    else:
        checks.append(DoctorCheck("PASS", "workflow_packs", f"validated {count} Comfy workflow pack(s)"))
    return checks


def check_runtime(root: Path, runtime_id: str, timeout: float) -> DoctorCheck:
    config = load_runtimes_config(root)
    url = _runtime_url(config, runtime_id)
    if not url:
        return DoctorCheck("BLOCKED", runtime_id, "runtime URL missing in slopperly/config/runtimes.yaml")
    try:
        assert_local_http_url(url, label=runtime_id)
    except Exception as exc:
        return DoctorCheck("FAIL", runtime_id, str(exc))

    probes = {
        "comfyui": ("/object_info", "ComfyUI /object_info"),
        "vllm": ("/v1/models", "vLLM /v1/models"),
        "vllm_omni": ("/v1/models", "vLLM-Omni /v1/models"),
        "llamacpp": ("/health", "llama.cpp /health"),
    }
    path, label = probes.get(runtime_id, ("/health", f"{runtime_id} /health"))
    try:
        _get_json(url, path, timeout)
    except urllib.error.URLError as exc:
        if runtime_id == "llamacpp" and path == "/health":
            try:
                _get_json(url, "/v1/models", timeout)
            except Exception as fallback_exc:
                return DoctorCheck("BLOCKED", runtime_id, f"{label} unavailable at {url}: {fallback_exc}")
            return DoctorCheck("PASS", runtime_id, f"llama.cpp /v1/models reachable at {url}")
        return DoctorCheck("BLOCKED", runtime_id, f"{label} unavailable at {url}: {exc}")
    except Exception as exc:
        return DoctorCheck("BLOCKED", runtime_id, f"{label} unavailable at {url}: {exc}")
    return DoctorCheck("PASS", runtime_id, f"{label} reachable at {url}")


def selected_runtimes(value: str) -> list[str]:
    if value in {"", "none", "skip"}:
        return []
    if value == "all":
        return ["comfyui", "vllm", "vllm_omni", "llamacpp"]
    return [item.strip() for item in value.split(",") if item.strip()]


def run_checks(
    *,
    root: Path,
    local_only: bool = False,
    cuda: bool = False,
    runtimes: str = "none",
    timeout: float = 2.0,
) -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    if local_only:
        checks.extend(check_local_only(root))
    checks.extend(check_workflow_packs(root))
    if cuda:
        checks.append(check_cuda())
    for runtime_id in selected_runtimes(runtimes):
        checks.append(check_runtime(root, runtime_id, timeout))
    return checks


def print_checks(checks: list[DoctorCheck]) -> None:
    for check in checks:
        print(f"{check.status} {check.name}: {check.detail}")
    counts = {status: sum(1 for c in checks if c.status == status) for status in {"PASS", "FAIL", "BLOCKED"}}
    print(f"Doctor checks: {counts['PASS']} passed, {counts['FAIL']} failed, {counts['BLOCKED']} blocked.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Slopperly local-only runtime readiness")
    parser.add_argument("--root", default=".")
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--cuda", action="store_true")
    parser.add_argument("--runtimes", default="none", help="'all', 'none', or comma-separated runtime ids")
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args(argv)

    checks = run_checks(
        root=Path(args.root).resolve(),
        local_only=args.local_only,
        cuda=args.cuda,
        runtimes=args.runtimes,
        timeout=args.timeout,
    )
    print_checks(checks)
    bad = any(check.status in {"FAIL", "BLOCKED"} for check in checks)
    return 0 if args.report_only or not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
