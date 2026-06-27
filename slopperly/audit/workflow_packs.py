"""Validate committed Comfy workflow packs."""

from __future__ import annotations

import argparse
from pathlib import Path

from slopperly.runtime.comfy.workflow_runner import ComfyWorkflowRunner

README_SECTIONS = [
    "Required Nodes",
    "Model Files",
    "UI Parameter Mapping",
    "Output Contract",
    "Test Command",
    "Expected Validation",
]


def validate_workflow_pack(pack: Path) -> list[str]:
    errors: list[str] = []
    try:
        workflow, schema = ComfyWorkflowRunner(None).validate_pack(pack)
    except Exception as exc:
        return [str(exc)]

    for field, targets in (schema.get("inputs") or {}).items():
        if not isinstance(targets, list):
            errors.append(f"{pack.name}: schema field {field!r} must map to a list")
            continue
        for target in targets:
            node_id = str(target.get("node"))
            input_name = target.get("input")
            node = workflow.get(node_id)
            if node is None:
                errors.append(f"{pack.name}: {field} maps to missing node {node_id}")
                continue
            if input_name not in (node.get("inputs") or {}):
                errors.append(f"{pack.name}: {field} maps to missing input {node_id}.{input_name}")

    readme = (pack / "README.md").read_text(encoding="utf-8")
    for section in README_SECTIONS:
        if section not in readme:
            errors.append(f"{pack.name}: README missing section {section!r}")

    models_text = (pack / "models.yaml").read_text(encoding="utf-8")
    for required in ("required_custom_nodes", "model_files", "artifact_contract"):
        if required not in models_text:
            errors.append(f"{pack.name}: models.yaml missing {required}")

    return errors


def iter_packs(root: Path):
    if not root.is_dir():
        return
    for pack in sorted(p for p in root.iterdir() if p.is_dir()):
        yield pack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Slopperly Comfy workflow packs")
    parser.add_argument("--root", default="slopperly/workflows/comfy")
    args = parser.parse_args(argv)
    root = Path(args.root)
    all_errors: list[str] = []
    count = 0
    for pack in iter_packs(root) or []:
        count += 1
        errors = validate_workflow_pack(pack)
        if errors:
            all_errors.extend(errors)
        else:
            print(f"PASS {pack.name}")
    if all_errors:
        for error in all_errors:
            print(f"FAIL {error}")
        return 1
    print(f"Validated {count} workflow pack(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
