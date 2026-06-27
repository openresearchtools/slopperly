"""Workflow-pack validation, parameter patching, and Comfy execution."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from .api_client import ComfyApiClient
from ..errors import WorkflowValidationError


def _token(*parts: str) -> str:
    return "".join(parts)


class ComfyWorkflowRunner:
    REQUIRED_PACK_FILES = {
        "workflow.editable.json",
        "workflow.api.json",
        "params.schema.json",
        "models.yaml",
        "test_payload.json",
        "README.md",
    }
    URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
    INDEXED_FIELD_RE = re.compile(
        r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?:\[(?P<bracket>\d+)\]|\.(?P<dot>\d+))"
        r"(?:\.(?P<attr>[A-Za-z_][A-Za-z0-9_]*))?$"
    )
    MISSING = object()
    BANNED_WORKFLOW_STRINGS = (
        _token("queue.", "fal", ".run"),
        _token("fal", ".ai"),
        _token("FAL", "_KEY"),
        _token("google.", "genai"),
        _token("GEMINI", "_API_KEY"),
        _token("api.", "minimaxi.", "chat"),
        _token("OPENAI", "_API_KEY"),
        _token("ANTHROPIC", "_API_KEY"),
        _token("ELEVENLABS", "_API_KEY"),
        _token("REPLICATE", "_API_TOKEN"),
        _token("api.", "stability.", "ai"),
        _token("run", "way"),
        _token("ver", "tex"),
        _token("bed", "rock"),
        _token("huggingface.", "co/inference"),
    )
    BANNED_NODE_CLASS_FRAGMENTS = (
        "anthropic",
        _token("bed", "rock"),
        "cloud",
        "elevenlabs",
        "fal",
        "gemini",
        "google",
        "minimax",
        "openai",
        "partner",
        "replicate",
        _token("run", "way"),
        "stability",
        _token("ver", "tex"),
    )

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
        self.validate_local_only_workflow(pack.name, workflow)
        for field, targets in self._schema_targets(schema, "inputs"):
            self._validate_targets(pack.name, workflow, field, targets, section="inputs")
        for field, targets in self._schema_targets(schema, "uploads"):
            self._validate_targets(pack.name, workflow, field, targets, section="uploads")
        return workflow, schema

    @classmethod
    def validate_local_only_workflow(cls, pack_name: str, workflow: dict) -> None:
        for node_id, node in workflow.items():
            class_type = str(node.get("class_type", ""))
            lower_class = class_type.lower()
            for fragment in cls.BANNED_NODE_CLASS_FRAGMENTS:
                if fragment in lower_class:
                    raise WorkflowValidationError(
                        f"{pack_name}: node {node_id} uses forbidden cloud/partner "
                        f"class {class_type!r}"
                    )

        for path, value in cls._walk_strings(workflow):
            lower_value = value.lower()
            for banned in cls.BANNED_WORKFLOW_STRINGS:
                if banned.lower() in lower_value:
                    raise WorkflowValidationError(
                        f"{pack_name}: workflow string at {path} contains forbidden "
                        f"cloud token {banned!r}"
                    )
            for url in cls.URL_RE.findall(value):
                parsed = urlparse(url)
                host = (parsed.hostname or "").lower()
                if host not in {"127.0.0.1", "localhost", "::1"}:
                    raise WorkflowValidationError(
                        f"{pack_name}: workflow string at {path} references non-local URL {url!r}"
                    )

    @classmethod
    def _walk_strings(cls, value, path: str = "$"):
        if isinstance(value, str):
            yield path, value
            return
        if isinstance(value, dict):
            for key, item in value.items():
                yield from cls._walk_strings(item, f"{path}.{key}")
            return
        if isinstance(value, list):
            for idx, item in enumerate(value):
                yield from cls._walk_strings(item, f"{path}[{idx}]")

    def patched_workflow(self, workflow: dict, schema: dict, inputs, scene) -> dict:
        patched = json.loads(json.dumps(workflow))
        mappings = schema.get("inputs", {})
        for field, targets in mappings.items():
            value = self._input_value(inputs, scene, field)
            if value is self.MISSING:
                continue
            for target in targets:
                node_id = str(target["node"])
                input_name = target["input"]
                if node_id not in patched:
                    raise WorkflowValidationError(f"schema points to missing node {node_id!r}")
                patched[node_id].setdefault("inputs", {})[input_name] = value
        return patched

    def patch_media_uploads(self, workflow: dict, schema: dict, inputs) -> list[Path]:
        temp_paths: list[Path] = []
        try:
            for field, targets in self._schema_targets(schema, "uploads"):
                value = self._media_input_value(inputs, field)
                if value is None:
                    continue
                upload_path, cleanup = self._coerce_media_file(value, field)
                if cleanup:
                    temp_paths.append(upload_path)
                upload_options = self._upload_options(field, targets)
                response = self.client.upload_file(
                    str(upload_path),
                    image_type=upload_options["type"],
                    endpoint=upload_options["endpoint"],
                    form_field=upload_options["form_field"],
                    type_field=upload_options["type_field"],
                )
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

    @classmethod
    def _input_value(cls, inputs, scene, field: str):
        explicit = {
            "prompt": getattr(inputs, "prompt", ""),
            "negative_prompt": getattr(inputs, "neg_prompt", ""),
            "text_ref": getattr(inputs, "text_ref", ""),
            "mode": getattr(inputs, "mode", ""),
            "width": int(getattr(inputs, "width", 0) or 0),
            "height": int(getattr(inputs, "height", 0) or 0),
            "frames": int(getattr(inputs, "frames", 0) or 0),
            "fps": float(getattr(inputs, "fps", 24.0) or 24.0),
            "steps": int(getattr(inputs, "steps", 0) or 0),
            "guidance": float(getattr(inputs, "guidance", 0.0) or 0.0),
            "strength": float(getattr(inputs, "strength", 0.0) or 0.0),
            "seed": int(getattr(inputs, "seed", 0) or 0),
            "batch": int(getattr(inputs, "batch", 1) or 1),
            "audio_length": float(getattr(inputs, "audio_length", 0.0) or 0.0),
            "speed": float(getattr(inputs, "speed", 0.0) or 0.0),
            "exaggeration": float(getattr(inputs, "exaggeration", 0.0) or 0.0),
            "pace": float(getattr(inputs, "pace", 0.0) or 0.0),
            "temperature": float(getattr(inputs, "temperature", 0.0) or 0.0),
            "illumination_style": getattr(inputs, "illumination_style", ""),
            "light_direction": getattr(inputs, "light_direction", ""),
        }
        if field in explicit:
            return explicit[field]
        value = cls._indexed_or_direct_value(inputs, field)
        if value is cls.MISSING:
            return cls._scene_value(scene, field)
        return value

    @classmethod
    def _indexed_or_direct_value(cls, inputs, field: str):
        match = cls.INDEXED_FIELD_RE.match(field)
        if match:
            sequence = getattr(inputs, match.group("name"), None)
            if sequence is None:
                return cls.MISSING
            index = int(match.group("bracket") or match.group("dot"))
            try:
                value = sequence[index]
            except (IndexError, TypeError):
                return cls.MISSING
            attr = match.group("attr")
            return cls._extract_indexed_attr(value, attr) if attr else value
        return getattr(inputs, field, cls.MISSING)

    @classmethod
    def _extract_indexed_attr(cls, value, attr: str | None):
        if attr is None:
            return value
        if isinstance(value, dict):
            return value.get(attr, cls.MISSING)
        if hasattr(value, attr):
            return getattr(value, attr)
        if isinstance(value, (list, tuple)):
            tuple_aliases = {
                "path": 0,
                "file": 0,
                "value": 0,
                "image": 0,
                "fraction": 1,
                "time": 1,
                "weight": 1,
            }
            offset = tuple_aliases.get(attr)
            if offset is not None and len(value) > offset:
                return value[offset]
        return cls.MISSING

    @classmethod
    def _scene_value(cls, scene, field: str):
        if scene is None:
            return cls.MISSING
        return getattr(scene, field, cls.MISSING)

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

    @classmethod
    def _media_input_value(cls, inputs, field: str):
        aliases = {
            "input_image": "image",
            "video": "video_path",
            "audio": "audio_ref",
        }
        value = cls._indexed_or_direct_value(inputs, aliases.get(field, field))
        if value is cls.MISSING:
            return None
        if isinstance(value, (list, tuple)) and value and isinstance(value[0], (str, Path)):
            return value[0]
        return value

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

    @classmethod
    def _upload_options(cls, field: str, targets) -> dict:
        first = targets[0] if targets else {}
        options = {
            "type": first.get("type", "input"),
            "endpoint": first.get("endpoint", "/upload/image"),
            "form_field": first.get("form_field", "image"),
            "type_field": first.get("type_field", "type"),
        }
        cls._validate_upload_options(field, options)
        for target in targets[1:]:
            for key, expected in options.items():
                actual = target.get(key, expected)
                if actual != expected:
                    raise WorkflowValidationError(
                        f"upload field {field!r} has inconsistent {key!r}: "
                        f"{actual!r} != {expected!r}"
                    )
        return options

    @staticmethod
    def _validate_upload_options(field: str, options: dict) -> None:
        endpoint = options.get("endpoint")
        if not isinstance(endpoint, str) or not endpoint.startswith("/") or "://" in endpoint:
            raise WorkflowValidationError(
                f"upload field {field!r} endpoint must be a local Comfy path, got {endpoint!r}"
            )
        for key in ("form_field", "type_field", "type"):
            value = options.get(key)
            if value is not None and not isinstance(value, str):
                raise WorkflowValidationError(
                    f"upload field {field!r} option {key!r} must be a string"
                )
        if options.get("type_field") and not isinstance(options.get("type"), str):
            raise WorkflowValidationError(
                f"upload field {field!r} option 'type' must be a string when type_field is set"
            )

    @staticmethod
    def _schema_targets(schema: dict, section: str):
        mappings = schema.get(section, {})
        if not mappings:
            return []
        if not isinstance(mappings, dict):
            raise WorkflowValidationError(f"schema section {section!r} must be a mapping")
        return mappings.items()

    @classmethod
    def _validate_targets(
        cls,
        pack_name: str,
        workflow: dict,
        field: str,
        targets,
        *,
        section: str,
    ) -> None:
        if not isinstance(targets, list):
            raise WorkflowValidationError(f"{pack_name}: schema field {field!r} must map to a list")
        if section == "uploads":
            cls._upload_options(field, targets)
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
            self._collect_text_outputs(node_out, results, output_root, destination)
            for kind in ("images", "videos", "gifs", "audio"):
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

    def _collect_text_outputs(
        self,
        node_out: dict,
        results: list[str],
        output_root: Path,
        destination: str | None,
    ) -> None:
        for key in ("text", "texts", "caption", "captions", "string", "strings", "data", "json"):
            if key not in node_out:
                continue
            for value in self._as_output_items(node_out.get(key)):
                text = self._stringify_text_output(value)
                if text is None:
                    continue
                if destination and not results:
                    Path(destination).write_text(text, encoding="utf-8")
                    results.append(destination)
                else:
                    results.append(text)

    @staticmethod
    def _as_output_items(value):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    @staticmethod
    def _stringify_text_output(value) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            text = value.strip()
            return text if text else None
        if isinstance(value, (dict, list)):
            return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
        text = str(value).strip()
        return text if text else None
