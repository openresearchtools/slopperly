"""Audit production dropdown certification evidence."""

from __future__ import annotations

import argparse
from pathlib import Path

from slopperly.config.registry import load_dropdown_profiles, model_entries
from slopperly.validation.certification import (
    discovered_certification_entries,
    validate_certification_entry,
)


def certified_entries(profile: str, root: Path) -> dict:
    data = load_dropdown_profiles(root)
    profiles = data.get("certified_dropdown_entries", {}) if isinstance(data, dict) else {}
    profile_data = profiles.get(profile, {}) if isinstance(profiles, dict) else {}
    configured = profile_data if isinstance(profile_data, dict) else {}
    discovered = discovered_certification_entries(profile, root)
    return {**configured, **discovered}


def audit(profile: str, root: Path) -> tuple[list[str], list[str]]:
    certs = certified_entries(profile, root)
    failures: list[str] = []
    passes: list[str] = []
    for entry in model_entries(root):
        name = entry.get("logical_name", "<unnamed>")
        validation_command = entry.get("validation_command")
        if not validation_command:
            failures.append(f"{name}: missing validation_command")
            continue
        entry_failures: list[str] = []
        for cert_name in required_certifications(entry):
            cert = certs.get(cert_name)
            if not cert:
                entry_failures.append(
                    f"required certification {cert_name}: no certification record "
                    f"for profile {profile!r}"
                )
                continue
            failure = validate_certification_entry(
                root=root,
                profile=profile,
                logical_name=cert_name,
                cert=cert,
            )
            if failure:
                entry_failures.append(f"required certification {cert_name}: {failure}")
        if entry_failures:
            failures.extend(f"{name}: {failure}" for failure in entry_failures)
            continue
        passes.append(name)
    return passes, failures


def required_certifications(entry: dict) -> list[str]:
    required = entry.get("required_certifications")
    if isinstance(required, list) and required:
        return [str(name) for name in required]
    return [str(entry.get("logical_name", "<unnamed>"))]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit dropdown artifact certification")
    parser.add_argument("--profile", default="smoke_16gb")
    parser.add_argument("--root", default=".")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    passes, failures = audit(args.profile, root)
    for name in passes:
        print(f"PASS {name}")
    for failure in failures:
        print(f"BLOCKED {failure}")
    if failures and not args.report_only:
        return 1
    print(f"Certification records: {len(passes)} passed, {len(failures)} blocked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
