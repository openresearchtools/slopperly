"""LTX 2.3 multi-anchor video routed through the owned local ComfyUI Q5 workflow."""

from __future__ import annotations

from ...models.base import InputSpec, ModelInputs, ModelPlugin, ParamSpec, UISection
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import clean_filename, solve_path

try:
    from ...utils.helpers import load_first_frame
except ImportError:  # GPU plugin harness only supplies helpers used by the exercised path.
    load_first_frame = None


MULTI_WORKFLOW_ID = "ltx23_multi_staged"
T2V_WORKFLOW_ID = "ltx23_t2v"
LTX_GGUF_MODEL = "ltx-2.3-22b-distilled-1.1-Q5_K_M.gguf"
LTX_TEXT_ENCODER = "gemma_3_12B_it_fp4_mixed.safetensors"
LTX_CONNECTOR = "ltx-2.3-22b-distilled_embeddings_connectors.safetensors"
LTX_VIDEO_VAE = "ltx-2.3-22b-distilled_video_vae.safetensors"
LTX_AUDIO_VAE = "ltx-2.3-22b-distilled_audio_vae.safetensors"
LTX_LORA = "ltx-2.3-22b-distilled-lora-384.safetensors"

_MIDDLE_GUIDES = (
    ("24", "25", "26", "27", "28"),
    ("40", "41", "42", "43", "44"),
    ("45", "46", "47", "48", "49"),
)
_LAST_GUIDE = ("29", "30", "31", "32", "33")


def _normalize_ltx_frames(frames: int) -> int:
    requested = max(9, int(frames or 49))
    return ((requested - 1) // 8) * 8 + 1


def _safe_ltx_dimensions(width: int, height: int) -> tuple[int, int]:
    safe_width = max(64, (int(width or 1280) // 32) * 32)
    safe_height = max(64, (int(height or 720) // 32) * 32)
    return safe_width, safe_height


def _prepare_ltx23_inputs(inputs: ModelInputs) -> None:
    width, height = _safe_ltx_dimensions(inputs.width, inputs.height)
    inputs.width = width
    inputs.height = height
    inputs.frames = _normalize_ltx_frames(inputs.frames)
    inputs.fps = float(getattr(inputs, "fps", 24.0) or 24.0)
    inputs.ltx_model = LTX_GGUF_MODEL
    inputs.ltx_text_encoder = LTX_TEXT_ENCODER
    inputs.ltx_connector = LTX_CONNECTOR
    inputs.ltx_video_vae = LTX_VIDEO_VAE
    inputs.ltx_audio_vae = LTX_AUDIO_VAE
    inputs.ltx_lora = LTX_LORA


def _note(inputs: ModelInputs, message: str) -> None:
    inputs.usage_note = ((inputs.usage_note + "\n") if inputs.usage_note else "") + message


def _clamped_fraction(value) -> float:
    try:
        fraction = float(value)
    except (TypeError, ValueError):
        fraction = 0.5
    return max(0.001, min(0.999, fraction))


def _middle_frame(fraction: float, frames: int) -> int:
    frame_idx = round(_clamped_fraction(fraction) * (frames - 1))
    return max(1, min(frames - 2, frame_idx))


def _anchor_path_and_fraction(item) -> tuple[object | None, float]:
    if isinstance(item, dict):
        path = item.get("path") or item.get("file") or item.get("image") or item.get("value")
        fraction = item.get("fraction", item.get("time", 0.5))
        return path, _clamped_fraction(fraction)
    if isinstance(item, (list, tuple)):
        if not item:
            return None, 0.5
        path = item[0]
        fraction = item[1] if len(item) > 1 else 0.5
        return path, _clamped_fraction(fraction)
    return item, 0.5


def _resolve_start_image(inputs: ModelInputs):
    image = getattr(inputs, "image", None)
    if image is not None:
        return image
    video_path = getattr(inputs, "video_path", None)
    if video_path:
        if load_first_frame is None:
            raise ValueError("LTX multi video-strip input requires load_first_frame helper availability.")
        return load_first_frame(video_path)
    for item in getattr(inputs, "middle_images_paths", []) or []:
        candidate, _ = _anchor_path_and_fraction(item)
        if candidate is not None:
            return candidate
    return getattr(inputs, "last_image", None)


def _prepare_anchor_slots(inputs: ModelInputs) -> None:
    raw_middle = list(getattr(inputs, "middle_images_paths", []) or [])
    normalized = []
    for item in raw_middle:
        path, fraction = _anchor_path_and_fraction(item)
        if path is not None:
            normalized.append((path, fraction))

    if len(normalized) > len(_MIDDLE_GUIDES):
        _note(
            inputs,
            "LTX Multi local Q5 maps the first three middle anchors; extra middle anchors "
            "need a larger certified Comfy graph before they can affect generation.",
        )
    normalized = normalized[: len(_MIDDLE_GUIDES)]
    inputs.middle_images_paths = normalized
    inputs.ltx_active_middle_count = len(normalized)
    for index, (_, fraction) in enumerate(normalized, start=1):
        setattr(inputs, f"ltx_middle_frame_{index}", _middle_frame(fraction, inputs.frames))
    inputs.ltx_has_last_anchor = getattr(inputs, "last_image", None) is not None
    inputs.ltx_last_frame_idx = -1
    inputs.ltx_guide_strength = 1.0
    inputs._slopperly_comfy_workflow_mutator = _mutate_ltx_multi_workflow


def _remove_branch(workflow: dict, branch: tuple[str, ...]) -> None:
    for node_id in branch:
        workflow.pop(str(node_id), None)


def _connect_guide(
    workflow: dict,
    guide_id: str,
    *,
    positive_node: str,
    negative_node: str,
    latent_node: str,
    latent_port: int,
) -> None:
    guide_inputs = workflow[guide_id]["inputs"]
    guide_inputs["positive"] = [positive_node, 0]
    guide_inputs["negative"] = [negative_node, 1]
    guide_inputs["latent"] = [latent_node, latent_port]


def _mutate_ltx_multi_workflow(workflow: dict, schema: dict, inputs, scene) -> dict:
    active_middle = max(0, min(len(_MIDDLE_GUIDES), int(getattr(inputs, "ltx_active_middle_count", 0) or 0)))
    has_last = bool(getattr(inputs, "ltx_has_last_anchor", False))

    positive_node = "13"
    negative_node = "13"
    latent_node = "15"
    latent_port = 0
    guide_count = 0

    for index, branch in enumerate(_MIDDLE_GUIDES):
        guide_id = branch[-1]
        if index >= active_middle:
            _remove_branch(workflow, branch)
            continue
        _connect_guide(
            workflow,
            guide_id,
            positive_node=positive_node,
            negative_node=negative_node,
            latent_node=latent_node,
            latent_port=latent_port,
        )
        positive_node = guide_id
        negative_node = guide_id
        latent_node = guide_id
        latent_port = 2
        guide_count += 1

    last_guide_id = _LAST_GUIDE[-1]
    if has_last:
        _connect_guide(
            workflow,
            last_guide_id,
            positive_node=positive_node,
            negative_node=negative_node,
            latent_node=latent_node,
            latent_port=latent_port,
        )
        positive_node = last_guide_id
        negative_node = last_guide_id
        latent_node = last_guide_id
        latent_port = 2
        guide_count += 1
    else:
        _remove_branch(workflow, _LAST_GUIDE)

    workflow["17"]["inputs"]["video_latent"] = [latent_node, latent_port]
    workflow["18"]["inputs"]["conditioning"] = [positive_node, 0]
    if guide_count:
        workflow["39"]["inputs"]["positive"] = [positive_node, 0]
        workflow["39"]["inputs"]["negative"] = [negative_node, 1]
        workflow["39"]["inputs"]["latent"] = ["23", 0]
        workflow["34"]["inputs"]["samples"] = ["39", 2]
    else:
        workflow.pop("39", None)
        workflow["34"]["inputs"]["samples"] = ["23", 0]
    return workflow


class LTX2_3MultiStagedPlugin(ModelPlugin):
    MODEL_ID = "LTX-2.3 Multi-Input Staged"
    DISPLAY_NAME = "Video: LTX-2.3 Multimodal (Local Q5)"
    MODEL_TYPE = "video"
    DESCRIPTION = "Local LTX 2.3 Q5 GGUF multi-anchor video through owned ComfyUI."

    INPUTS = (
        InputSpec.PROMPT
        | InputSpec.NEG_PROMPT
        | InputSpec.IMAGE
        | InputSpec.VIDEO
        | InputSpec.LORA
        | InputSpec.AUDIO_REF
    )
    UI_SECTIONS = [
        UISection.PROMPT,
        UISection.NEG_PROMPT,
        UISection.VIDEO_STRIP,
        UISection.RESOLUTION,
        UISection.FRAMES,
        UISection.SEED,
        UISection.LORA,
    ]
    PARAMS = ParamSpec(width=1280, height=720, frames=49, steps=8, guidance=1.0, strength=0.7)
    REQUIRED_PACKAGES = []
    supports_inpaint = False
    supports_batch = False

    def draw_custom_ui(self, col, context) -> bool:
        row = col.row(align=True)
        row.prop(context.scene, "ref_audio_path", text="Audio Ref.")
        row.operator("sequencer.open_audio_filebrowser", text="", icon="FILEBROWSER")
        return False

    def draw_post_seed_ui(self, col, context):
        col.prop(context.scene, "ltx23_stage_mode")

    def load(self, prefs, scene, **kw):
        enabled_loras = [
            (getattr(item, "name", ""), float(getattr(item, "weight_value", 1.0) or 1.0))
            for item in kw.get("enabled_items", [])
            if getattr(item, "enabled", True) and getattr(item, "name", "")
        ]
        return {
            "gateway": SlopperlyRuntimeGateway(),
            "enabled_loras": enabled_loras,
            "last_model_card": self.MODEL_ID,
        }

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs) -> str:
        _prepare_ltx23_inputs(inputs)
        stage_mode = str(getattr(scene, "ltx23_stage_mode", "FULL") or "FULL").upper()
        if stage_mode != "FULL":
            _note(
                inputs,
                "LTX Multi STEP1/STEP2 legacy modes used the removed direct Diffusers path. "
                "Slopperly local Q5 runs the certified full Comfy graph until separate "
                "STEP1/STEP2 Comfy profiles pass artifact tests.",
            )

        custom_loras = pipe_obj.get("enabled_loras", []) if isinstance(pipe_obj, dict) else []
        if custom_loras:
            _note(
                inputs,
                "LTX Multi local Q5 uses the committed distilled LTX LoRA. Project LoRA "
                "adapters remain visible in the UI but are not dynamically injected yet.",
            )
        if inputs.steps:
            _note(inputs, "LTX Multi local Q5 uses its committed ManualSigmas schedule; the steps slider is preserved.")
        if inputs.guidance:
            _note(inputs, "LTX Multi local Q5 uses BasicGuider without a direct CFG input; the guidance slider is preserved.")

        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        image = _resolve_start_image(inputs)
        if image is None:
            _note(inputs, "No anchor strip was supplied; routed through the certified local LTX Q5 text-to-video workflow.")
            workflow_id = T2V_WORKFLOW_ID
            suffix = "t2v"
        else:
            inputs.image = image
            _prepare_anchor_slots(inputs)
            workflow_id = MULTI_WORKFLOW_ID
            suffix = "multi"

        self.set_phase(inputs, f"Running local Comfy workflow: {workflow_id}")
        filename = clean_filename(f"{inputs.seed}_ltx23_q5_{suffix}") or f"ltx23_q5_{suffix}"
        destination = solve_path(filename + ".mp4")
        return gateway.run_comfy_workflow(
            workflow_id,
            inputs,
            scene,
            prefs,
            destination=destination,
            timeout=float(getattr(prefs, "comfyui_timeout", 7200.0) or 7200.0),
        )
