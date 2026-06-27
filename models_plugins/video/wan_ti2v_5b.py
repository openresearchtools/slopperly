"""Local Wan2.2 TI2V-5B default routed through the owned ComfyUI runtime."""

from ...models.base import InputSpec, ModelInputs, ModelPlugin, ParamSpec, UISection
from ...utils.helpers import clean_filename, solve_path
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway


WORKFLOW_ID = "wan22_ti2v_5b_720p24_gguf"
WAN_MODEL = "Wan2.2-TI2V-5B-Q5_K_M.gguf"
WAN_TEXT_ENCODER = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
WAN_VAE = "wan2.2_vae.safetensors"


def _safe_720p_family(width: int, height: int) -> tuple[int, int]:
    """Map arbitrary UI resolution choices to the certified Wan 720P family."""
    if int(height or 0) > int(width or 0):
        return 704, 1280
    return 1280, 704


def prepare_wan22_ti2v_inputs(inputs: ModelInputs) -> None:
    width, height = _safe_720p_family(inputs.width, inputs.height)
    inputs.width = width
    inputs.height = height
    inputs.fps = 24.0
    inputs.wan_model = WAN_MODEL
    inputs.wan_text_encoder = WAN_TEXT_ENCODER
    inputs.wan_vae = WAN_VAE
    inputs.wan_clip_type = "wan"
    inputs.wan_sampler = "euler"
    inputs.wan_scheduler = "simple"
    inputs.wan_shift = 5.0
    inputs.wan_denoise = 1.0
    inputs.wan_video_format = "video/h264-mp4"
    inputs.wan_output_prefix = "slopperly_wan22_ti2v_5b"


class WanTI2V5BPlugin(ModelPlugin):
    MODEL_ID = "Wan-AI/Wan2.2-TI2V-5B"
    DISPLAY_NAME = "Video: Wan2.2 TI2V 5B (Local)"
    MODEL_TYPE = "video"
    DESCRIPTION = "Local 24fps text/image-to-video through ComfyUI-GGUF."

    INPUTS = InputSpec.PROMPT | InputSpec.NEG_PROMPT | InputSpec.IMAGE
    UI_SECTIONS = [
        UISection.PROMPT,
        UISection.NEG_PROMPT,
        UISection.IMAGE_STRIP,
        UISection.RESOLUTION,
        UISection.FRAMES,
        UISection.STEPS,
        UISection.GUIDANCE,
        UISection.SEED,
    ]
    PARAMS = ParamSpec(width=1280, height=704, frames=49, steps=25, guidance=5.0)
    REQUIRED_PACKAGES = []
    supports_batch = False

    def load(self, prefs, scene, **kw):
        return {"gateway": SlopperlyRuntimeGateway(), "last_model_card": self.MODEL_ID}

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs):
        prepare_wan22_ti2v_inputs(inputs)
        self.set_phase(inputs, f"Running local Comfy workflow: {WORKFLOW_ID}")
        stem = clean_filename(str(inputs.seed) + "_" + (inputs.prompt[:30] or "wan22_ti2v_5b"))
        destination = solve_path(stem + ".mp4")
        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()
        return gateway.run_comfy_workflow(
            WORKFLOW_ID,
            inputs,
            scene,
            prefs,
            destination=destination,
        )
