"""Stem splitter through the local ComfyUI Hybrid Demucs workflow."""

import json
import shutil
from pathlib import Path

from ...models.base import ModelPlugin, InputSpec, ParamSpec, ModelInputs
from ...utils.helpers import clean_filename, solve_path
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway


_MULTI_STEM_PREFIX = "MULTI_STEM:"

STEM_NAMES_4 = ["vocals", "drums", "bass", "other"]
STEM_NAMES_6 = ["vocals", "drums", "bass", "other", "guitar", "piano"]
COMFY_STEM_OUTPUT_ORDER = ["bass", "drums", "other", "vocals"]


def _selected_stems(scene) -> list[str]:
    model = getattr(scene, "stem_split_model", "htdemucs_ft")
    if model == "htdemucs_6s":
        raise ValueError(
            "The local Comfy workflow audio_stem_split_demucs uses Torchaudio "
            "Hybrid Demucs and exposes four stems: bass, drums, other, and vocals. "
            "The old six-stem htdemucs_6s option is blocked until a pinned Comfy "
            "six-stem workflow passes artifact certification."
        )
    selected = [stem for stem in STEM_NAMES_4 if getattr(scene, f"stem_split_{stem}", True)]
    if not selected:
        raise ValueError("No stems selected - check at least one stem checkbox.")
    return selected


def _stem_from_filename(path: str) -> str | None:
    lower = Path(path).name.lower()
    for stem in COMFY_STEM_OUTPUT_ORDER:
        if lower.startswith(stem + "_") or f"stem_{stem}" in lower or f"_{stem}_" in lower:
            return stem
    return None


def _map_comfy_outputs(paths) -> dict[str, str]:
    if isinstance(paths, (str, Path)):
        raw_paths = [str(paths)]
    else:
        raw_paths = [str(path) for path in paths]
    by_stem: dict[str, str] = {}
    for path in raw_paths:
        stem = _stem_from_filename(path)
        if stem and stem not in by_stem:
            by_stem[stem] = path
    if len(by_stem) < len(COMFY_STEM_OUTPUT_ORDER) and len(raw_paths) >= len(COMFY_STEM_OUTPUT_ORDER):
        for stem, path in zip(COMFY_STEM_OUTPUT_ORDER, raw_paths):
            by_stem.setdefault(stem, path)
    return by_stem


def _copy_selected_stems(stem_outputs: dict[str, str], selected: list[str], inputs: ModelInputs) -> dict[str, str]:
    source_name = getattr(inputs, "output_basename", "") or Path(inputs.audio_ref or "source_audio").stem
    source_name = clean_filename(source_name) or "source_audio"
    copied: dict[str, str] = {}
    missing: list[str] = []
    for stem in selected:
        src = stem_outputs.get(stem)
        if not src:
            missing.append(stem)
            continue
        suffix = Path(src).suffix or ".flac"
        dst = solve_path(f"{stem}_{source_name}{suffix}")
        if Path(src).resolve() != Path(dst).resolve():
            Path(dst).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        copied[stem] = dst
    if missing:
        raise RuntimeError(
            "Comfy stem workflow completed but did not return expected stem(s): "
            + ", ".join(missing)
        )
    return copied


class StemSplitterPlugin(ModelPlugin):
    MODEL_ID     = "StemSplitter"
    DISPLAY_NAME = "Stem Splitter (Local Comfy Demucs)"
    MODEL_TYPE   = "audio"
    DESCRIPTION  = "Split a selected audio/video strip into local Hybrid Demucs stems through ComfyUI"

    # Audio reference is the input strip; no text prompt needed.
    INPUTS       = InputSpec.AUDIO_REF
    UI_SECTIONS  = []
    PARAMS       = ParamSpec()
    REQUIRED_PACKAGES = []

    supports_inpaint      = False
    supports_img2img      = False
    show_enhance          = False
    requires_input_strip  = True
    supports_batch        = False  # deterministic stem split makes identical batch copies

    def load(self, prefs, scene, **kw):
        return {
            "gateway": SlopperlyRuntimeGateway(),
            "last_model_card": self.MODEL_ID,
        }

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs) -> str:
        audio_path = inputs.audio_ref
        if not audio_path:
            raise ValueError("No audio reference path - select a SOUND or MOVIE strip as input.")

        selected = _selected_stems(scene)
        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        self.set_phase(inputs, "Separating stems with local ComfyUI")
        result_paths = gateway.run_comfy_workflow(
            "audio_stem_split_demucs",
            inputs,
            scene,
            prefs,
            timeout=float(getattr(prefs, "comfyui_timeout", 3600.0) or 3600.0),
        )
        stem_paths = _copy_selected_stems(_map_comfy_outputs(result_paths), selected, inputs)

        # Return a multi-stem sentinel that _queue_insert_strip understands.
        return _MULTI_STEM_PREFIX + json.dumps(stem_paths)

    def draw_custom_ui(self, layout, context):
        scene = context.scene
        layout.prop(scene, "stem_split_model", text="Variant")
        col = layout.column(align=True)
        col.use_property_split = True
        col.prop(scene, "stem_split_vocals")
        col.prop(scene, "stem_split_drums")
        col.prop(scene, "stem_split_bass")
        col.prop(scene, "stem_split_other")
        if getattr(scene, "stem_split_model", "") == "htdemucs_6s":
            col.prop(scene, "stem_split_guitar")
            col.prop(scene, "stem_split_piano")
