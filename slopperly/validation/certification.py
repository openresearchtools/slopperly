"""Certification evidence helpers for GPU artifact tests."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


PASS = "PASS"
BLOCKED = "BLOCKED"
FAIL = "FAIL"
VALID_STATUSES = {PASS, BLOCKED, FAIL}


def certification_root(root: str | Path, profile: str) -> Path:
    return Path(root) / ".slopperly" / "certification" / profile


def certification_record_path(root: str | Path, profile: str, logical_name: str) -> Path:
    safe_name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in logical_name)
    return certification_root(root, profile) / f"{safe_name}.json"


def write_certification_record(
    *,
    root: str | Path,
    profile: str,
    logical_name: str,
    status: str,
    command: str,
    artifact: str | None = None,
    validation: dict | None = None,
    reason: str = "",
    metadata: dict | None = None,
) -> Path:
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid certification status: {status}")
    root_path = Path(root).resolve()
    artifact_rel = _relative(root_path, artifact) if artifact else None
    record_path = certification_record_path(root_path, profile, logical_name)
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": 1,
        "logical_name": logical_name,
        "profile": profile,
        "status": status,
        "command": command,
        "artifact": artifact_rel,
        "validation": validation or {},
        "reason": reason,
        "metadata": metadata or {},
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record_path


def load_certification_record(path: str | Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid certification JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"invalid certification JSON {path}: root must be an object")
    return data


def discovered_certification_entries(profile: str, root: str | Path) -> dict:
    root_path = Path(root).resolve()
    entries: dict[str, dict] = {}
    for result_path in sorted(certification_root(root_path, profile).glob("*.json")):
        try:
            record = load_certification_record(result_path)
        except ValueError:
            continue
        logical_name = record.get("logical_name")
        if not logical_name:
            continue
        result_rel = result_path.relative_to(root_path).as_posix()
        entries[logical_name] = {
            "artifact": record.get("artifact"),
            "test_result": result_rel,
        }
    return entries


def validate_certification_entry(
    *,
    root: str | Path,
    profile: str,
    logical_name: str,
    cert: dict,
) -> str | None:
    root_path = Path(root).resolve()
    test_result = cert.get("test_result")
    if not test_result:
        return "certification test result missing from record"
    result_path = root_path / test_result
    if not result_path.is_file():
        return f"certification test result missing: {test_result!r}"

    try:
        record = load_certification_record(result_path)
    except ValueError as exc:
        return str(exc)
    if record.get("logical_name") != logical_name:
        return (
            f"test result logical_name {record.get('logical_name')!r} "
            f"!= {logical_name!r}"
        )
    if record.get("profile") != profile:
        return f"test result profile {record.get('profile')!r} != {profile!r}"
    if record.get("status") != PASS:
        reason = record.get("reason") or "no reason recorded"
        return f"test result status {record.get('status')!r}: {reason}"

    artifact = cert.get("artifact")
    if not artifact:
        return "certification artifact missing from record"
    artifact_path = root_path / artifact
    if not artifact_path.is_file():
        return f"certification artifact missing: {artifact!r}"
    record_artifact = record.get("artifact")
    if record_artifact and record_artifact != artifact:
        return f"test result artifact {record_artifact!r} != dropdown artifact {artifact!r}"
    return None


def _relative(root: Path, path: str | Path | None) -> str | None:
    if not path:
        return None
    artifact_path = Path(path)
    if not artifact_path.is_absolute():
        return artifact_path.as_posix()
    try:
        return artifact_path.resolve().relative_to(root).as_posix()
    except ValueError:
        return artifact_path.as_posix()
