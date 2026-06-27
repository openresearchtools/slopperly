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
        for field, targets in self._schema_targets(schema, "inputs"):
            self._validate_targets(pack.name, workflow, field, targets)
        for field, targets in self._schema_targets(schema, "uploads"):
            self._validate_targets(pack.name, workflow, field, targets)
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

    def patch_media_uploads(self, workflow: dict, schema: dict, inputs) -> list[Path]:
        temp_paths: list[Path] = []
        media_values = self._media_input_values(inputs)
        try:
            for field, targets in self._schema_targets(schema, "uploads"):
                value = media_values.get(field)
                if value is None:
                    continue
                upload_path, cleanup = self._coerce_media_file(value, field)
                if cleanup:
                    temp_paths.append(upload_path)
                upload_type = targets[0].get("type", "input") if targets else "input"
                response = self.client.upload_file(str(upload_path), image_type=upload_type)
                uploaded_name = response.get("name") or response.get("filename")
                if not uploaded_name:
                    raise WorkflowValidationError(
                        f"Comfy upload for {field!r} returned no file name: {response}"
                    )
                for target in targets:
                    node_id = str(target["node"])
                    input_name = target["input"]
                    workflow[node_id].setdefault("inputs", {})[input_name] = uploaded_name
            return temp_paths
        except Exception:
            for temp_path in temp_paths:
                temp_path.unlink(missing_ok=True)
            raise

    def validate_runtime_nodes(self, workflow: dict) -> None:
        info = self.client.object_info()
        available = set(info)
        required = {str(node.get("class_type")) for node in workflow.values()}
        missing = sorted(required - available)
        if missing:
            raise WorkflowValidationError(
                "ComfyUI is missing required workflow node classes: " + ", ".join(missing)
            )

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

    @staticmethod
    def _set_phase(inputs, label: str) -> None:
        phase_fn = getattr(inputs, "phase_fn", None)
        if phase_fn is not None:
            phase_fn(label)

    @staticmethod
    def _set_progress(inputs, step: int, total: int) -> None:
        progress_fn = getattr(inputs, "progress_fn", None)
        if progress_fn is not None:
            progress_fn(step, total)

    @staticmethod
    def _media_input_values(inputs) -> dict:
        return {
            "image": getattr(inputs, "image", None),
            "input_image": getattr(inputs, "image", None),
            "last_image": getattr(inputs, "last_image", None),
            "video": getattr(inputs, "video_path", None),
            "video_path": getattr(inputs, "video_path", None),
            "audio": getattr(inputs, "audio_ref", None),
            "audio_ref": getattr(inputs, "audio_ref", None),
        }

    @staticmethod
    def _coerce_media_file(value, field: str) -> tuple[Path, bool]:
        if isinstance(value, (str, Path)):
            path = Path(value)
            if not path.is_file():
                raise WorkflowValidationError(f"media input {field!r} does not exist: {path}")
            return path, False
        if hasattr(value, "save"):
            handle = tempfile.NamedTemporaryFile(
                prefix=f"slopperly_{field}_",
                suffix=".png",
                delete=False,
            )
            handle.close()
            path = Path(handle.name)
            value.save(str(path))
            return path, True
        raise WorkflowValidationError(
            f"media input {field!r} must be a file path or image object with save()"
        )

    @staticmethod
    def _schema_targets(schema: dict, section: str):
        mappings = schema.get(section, {})
        if not mappings:
            return []
        if not isinstance(mappings, dict):
            raise WorkflowValidationError(f"schema section {section!r} must be a mapping")
        return mappings.items()

    @staticmethod
    def _validate_targets(pack_name: str, workflow: dict, field: str, targets) -> None:
        if not isinstance(targets, list):
            raise WorkflowValidationError(f"{pack_name}: schema field {field!r} must map to a list")
        for target in targets:
            node_id = str(target.get("node"))
            input_name = target.get("input")
            node = workflow.get(node_id)
            if node is None:
                raise WorkflowValidationError(f"{pack_name}: {field} maps to missing node {node_id}")
            if input_name not in (node.get("inputs") or {}):
                raise WorkflowValidationError(
                    f"{pack_name}: {field} maps to missing input {node_id}.{input_name}"
                )

    def run_pack(
        self,
        pack: Path,
        inputs,
        scene,
        *,
        destination: str | None = None,
        timeout: float = 3600.0,
    ):
        total_steps = 5
        self._set_phase(inputs, f"Preparing Comfy workflow {pack.name}")
        workflow, schema = self.validate_pack(pack)
        self._set_progress(inputs, 1, total_steps)
        self._set_phase(inputs, "Patching Comfy workflow parameters")
        workflow = self.patched_workflow(workflow, schema, inputs, scene)
        self._set_phase(inputs, "Checking Comfy workflow nodes")
        self.validate_runtime_nodes(workflow)
        self._set_progress(inputs, 2, total_steps)
        self._set_phase(inputs, "Uploading Comfy workflow inputs")
        temp_paths = self.patch_media_uploads(workflow, schema, inputs)
        self._set_progress(inputs, 3, total_steps)
        try:
            self._set_phase(inputs, "Queueing Comfy workflow")
            prompt_id = self.client.queue_prompt(workflow)
            self._set_progress(inputs, 4, total_steps)
            self._set_phase(inputs, "Waiting for Comfy workflow output")
            history = self.client.wait_for_history(prompt_id, timeout=timeout)
            self._set_phase(inputs, "Collecting Comfy workflow artifacts")
            outputs = self._collect_outputs(history, destination=destination)
        finally:
            for temp_path in temp_paths:
                temp_path.unlink(missing_ok=True)
        if not outputs:
            raise WorkflowValidationError(f"Comfy workflow {pack.name!r} completed with no file outputs")
        self._set_progress(inputs, total_steps, total_steps)
        self._set_phase(inputs, "Comfy workflow complete")
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
