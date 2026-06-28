"""LTX image-to-video routed through the owned local ComfyUI runtime."""

from ...models.base import InputSpec, ModelInputs, ModelPlugin, ParamSpec, UISection
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import clean_filename, solve_path

try:
    from ...utils.helpers import load_first_frame
except ImportError:  # GPU plugin harness only supplies helpers used by the exercised path.
    load_first_frame = None


WORKFLOW_ID = "ltx23_i2v"
LTX_GGUF_MODEL = "ltx-2.3-22b-distilled-1.1-Q5_K_M.gguf"
LTX_TEXT_ENCODER = "gemma_3_12B_it_fp4_mixed.safetensors"
LTX_CONNECTOR = "ltx-2.3-22b-distilled_embeddings_connectors.safetensors"
LTX_VIDEO_VAE = "ltx-2.3-22b-distilled_video_vae.safetensors"
LTX_AUDIO_VAE = "ltx-2.3-22b-distilled_audio_vae.safetensors"
LTX_LORA = "ltx-2.3-22b-distilled-lora-384.safetensors"


def _normalize_ltx_frames(frames: int) -> int:
    requested = max(9, int(frames or 49))
    return ((requested - 1) // 8) * 8 + 1


def _safe_ltx_dimensions(width: int, height: int) -> tuple[int, int]:
    safe_width = max(64, (int(width or 1280) // 32) * 32)
    safe_height = max(64, (int(height or 720) // 32) * 32)
    return safe_width, safe_height


def prepare_ltx23_i2v_inputs(inputs: ModelInputs) -> None:
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


class LTX2Plugin(ModelPlugin):
    MODEL_ID = "rootonchair/LTX-2-19b-distilled"
    DISPLAY_NAME = "Video: LTX-2 19b (Local Q5)"
    MODEL_TYPE = "video"
    DESCRIPTION = "Local LTX image-to-video through owned ComfyUI using the LTX 2.3 Q5 GGUF workflow."

    INPUTS = InputSpec.PROMPT | InputSpec.NEG_PROMPT | InputSpec.IMAGE | InputSpec.LORA
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
    supports_batch = False

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

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs):
        image = inputs.image
        if image is None and inputs.video_path:
            if load_first_frame is None:
                raise ValueError("LTX video-strip input requires load_first_frame helper availability.")
            image = load_first_frame(inputs.video_path)
        if image is None:
            raise ValueError("LTX local image-to-video requires an image or video strip input.")
        inputs.image = image
        prepare_ltx23_i2v_inputs(inputs)

        custom_loras = pipe_obj.get("enabled_loras", []) if isinstance(pipe_obj, dict) else []
        if custom_loras:
            note = (
                "LTX local Q5 workflow uses the committed distilled LTX LoRA. "
                "Project LoRA adapters remain visible in the UI but are not dynamically injected yet."
            )
            inputs.usage_note = ((inputs.usage_note + "\n") if inputs.usage_note else "") + note

        if inputs.steps:
            inputs.usage_note = (
                (inputs.usage_note + "\n") if inputs.usage_note else ""
            ) + "LTX local Q5 workflow uses its committed ManualSigmas schedule; the steps slider is preserved."
        if inputs.guidance:
            inputs.usage_note = (
                (inputs.usage_note + "\n") if inputs.usage_note else ""
            ) + "LTX local Q5 workflow uses BasicGuider without a direct CFG input; the guidance slider is preserved."

        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        self.set_phase(inputs, f"Running local Comfy workflow: {WORKFLOW_ID}")
        filename = clean_filename(f"{inputs.seed}_ltx23_q5_i2v") or "ltx23_q5_i2v"
        destination = solve_path(filename + ".mp4")
        return gateway.run_comfy_workflow(
            WORKFLOW_ID,
            inputs,
            scene,
            prefs,
            destination=destination,
            timeout=float(getattr(prefs, "comfyui_timeout", 7200.0) or 7200.0),
        )
