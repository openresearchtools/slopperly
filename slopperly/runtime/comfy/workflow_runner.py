"""Workflow-pack validation, parameter patching, and Comfy execution."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from .api_client import ComfyApiClient
from ..errors import WorkflowValidationError


class ComfyWorkflowRunner:
    REQUIRED_PACK_FILES = {
        "workflow.editable.json",
        "workflow.api.json",
        "params.schema.json",
        "models.yaml",
        "test_payload.json",
        "README.md",
    }

    def __init__(self, client: ComfyApiClient):
        self.client = client

    @classmethod
    def from_preferences(cls, prefs):
        return cls(ComfyApiClient(getattr(prefs, "comfyui_url", "http://127.0.0.1:8188")))

    def validate_pack(self, pack: Path) -> tuple[dict, dict]:
        missing = sorted(name for name in self.REQUIRED_PACK_FILES if not (pack / name).is_file())
        if missing:
            raise WorkflowValidationError(f"{pack.name} is missing required files: {missing}")
        workflow = json.loads((pack / "workflow.api.json").read_text(encoding="utf-8"))
        schema = json.loads((pack / "params.schema.json").read_text(encoding="utf-8"))
        if not isinstance(workflow, dict) or not workflow:
            raise WorkflowValidationError(f"{pack.name}/workflow.api.json is not a Comfy API graph")
        for node_id, node in workflow.items():
            if not isinstance(node, dict) or "class_type" not in node or "inputs" not in node:
                raise WorkflowValidationError(
                    f"{pack.name}/workflow.api.json node {node_id!r} is not API format"
                )
        return workflow, schema

    def patched_workflow(self, workflow: dict, schema: dict, inputs, scene) -> dict:
        patched = json.loads(json.dumps(workflow))
        mappings = schema.get("inputs", {})
        values = self._input_values(inputs, scene)
        for field, targets in mappings.items():
            if field not in values:
                continue
            for target in targets:
                node_id = str(target["node"])
                input_name = target["input"]
                if node_id not in patched:
                    raise WorkflowValidationError(f"schema points to missing node {node_id!r}")
                patched[node_id].setdefault("inputs", {})[input_name] = values[field]
        return patched

    @staticmethod
    def _input_values(inputs, scene) -> dict:
        return {
            "prompt": getattr(inputs, "prompt", ""),
            "negative_prompt": getattr(inputs, "neg_prompt", ""),
            "width": int(getattr(inputs, "width", 0) or 0),
            "height": int(getattr(inputs, "height", 0) or 0),
            "frames": int(getattr(inputs, "frames", 0) or 0),
            "fps": float(getattr(inputs, "fps", 24.0) or 24.0),
            "steps": int(getattr(inputs, "steps", 0) or 0),
            "guidance": float(getattr(inputs, "guidance", 0.0) or 0.0),
            "strength": float(getattr(inputs, "strength", 0.0) or 0.0),
            "seed": int(getattr(inputs, "seed", 0) or 0),
        }

    def run_pack(
        self,
        pack: Path,
        inputs,
        scene,
        *,
        destination: str | None = None,
        timeout: float = 3600.0,
    ):
        workflow, schema = self.validate_pack(pack)
        workflow = self.patched_workflow(workflow, schema, inputs, scene)
        prompt_id = self.client.queue_prompt(workflow)
        history = self.client.wait_for_history(prompt_id, timeout=timeout)
        outputs = self._collect_outputs(history, destination=destination)
        if not outputs:
            raise WorkflowValidationError(f"Comfy workflow {pack.name!r} completed with no file outputs")
        return outputs[0] if len(outputs) == 1 else outputs

    def _collect_outputs(self, history: dict, *, destination: str | None = None) -> list[str]:
        output_root = Path(destination).parent if destination else Path(tempfile.gettempdir()) / "slopperly_outputs"
        output_root.mkdir(parents=True, exist_ok=True)
        results: list[str] = []
        for node_out in (history.get("outputs") or {}).values():
            for kind in ("images", "videos", "audio"):
                for item in node_out.get(kind, []) or []:
                    filename = item.get("filename")
                    if not filename:
                        continue
                    blob = self.client.view(
                        filename,
                        item.get("subfolder", ""),
                        item.get("type", "output"),
                    )
                    out_path = Path(destination) if destination and not results else output_root / filename
                    out_path.write_bytes(blob)
                    results.append(str(out_path))
        if destination and results and results[0] != destination:
            shutil.copyfile(results[0], destination)
            results[0] = destination
        return results
