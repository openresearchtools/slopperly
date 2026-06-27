"""High-quality text-to-image via the local ERNIE-Image Comfy workflow."""

from ...models.base import ModelPlugin, InputSpec, UISection, ParamSpec, ModelInputs
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import clean_filename, solve_path


WORKFLOW_ID = "ernie_image_t2i"


class ErniePlugin(ModelPlugin):
    MODEL_ID = "baidu/ERNIE-Image"
    DISPLAY_NAME = "Image: ERNIE-Image"
    MODEL_TYPE = "image"
    DESCRIPTION = "High-quality text-to-image via the local ERNIE-Image Comfy workflow"

    USE_PROMPT_ENHANCER = True

    INPUTS = InputSpec.PROMPT | InputSpec.NEG_PROMPT
    UI_SECTIONS = [
        UISection.PROMPT,
        UISection.NEG_PROMPT,
        UISection.RESOLUTION,
        UISection.FRAMES,
        UISection.STEPS,
        UISection.GUIDANCE,
        UISection.SEED,
    ]
    PARAMS = ParamSpec(steps=50, guidance=4.0)
    REQUIRED_PACKAGES = []
    supports_inpaint = False
    supports_img2img = False
    uses_standard_input_strip = False

    def load(self, prefs, scene, **kw):
        return {
            "gateway": SlopperlyRuntimeGateway(),
            "use_pe": self.USE_PROMPT_ENHANCER,
            "last_model_card": self.MODEL_ID,
        }

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs):
        gateway = (pipe_obj or {}).get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        use_pe = bool((pipe_obj or {}).get("use_pe", self.USE_PROMPT_ENHANCER))
        _prepare_ernie_inputs(
            inputs,
            model_name="ernie-image.safetensors",
            use_prompt_enhancer=use_pe,
        )
        stem = clean_filename((inputs.prompt or "ernie_image")[:40]) or "ernie_image"
        destination = solve_path(f"ernie_image_{stem}.png")
        return gateway.run_comfy_workflow(
            WORKFLOW_ID,
            inputs,
            scene,
            prefs,
            destination=destination,
            timeout=float(getattr(prefs, "comfyui_timeout", 3600.0) or 3600.0),
        )


def _prepare_ernie_inputs(inputs: ModelInputs, *, model_name: str, use_prompt_enhancer: bool):
    inputs.ernie_model = model_name
    inputs.ernie_text_encoder = "ministral-3-3b.safetensors"
    inputs.ernie_prompt_enhancer = "ernie-image-prompt-enhancer.safetensors"
    inputs.ernie_clip_type = "flux2"
    inputs.ernie_vae = "flux2-vae.safetensors"
    inputs.ernie_sampler = "euler"
    inputs.ernie_scheduler = "simple"
    inputs.ernie_denoise = 1.0
    inputs.ernie_prompt_request = _prompt_enhancement_request(inputs)
    inputs.ernie_textgen_max_length = 2048
    inputs.ernie_textgen_sampling_mode = "on" if use_prompt_enhancer else "off"
    inputs.ernie_textgen_temperature = 0.6
    inputs.ernie_textgen_top_k = 64
    inputs.ernie_textgen_top_p = 0.8
    inputs.ernie_textgen_min_p = 0.05
    inputs.ernie_textgen_repetition_penalty = 1.05
    inputs.ernie_textgen_presence_penalty = 0.0
    inputs.ernie_textgen_seed = int(inputs.seed or 0)
    inputs.ernie_textgen_thinking = False
    inputs.ernie_textgen_use_default_template = True


def _prompt_enhancement_request(inputs: ModelInputs) -> str:
    prompt = (inputs.prompt or "").replace("{", "{{").replace("}", "}}")
    return (
        "You are a professional text-to-image prompt enhancement assistant. "
        "Expand the user's short visual description into one rich, concrete image "
        "prompt for a local ERNIE-Image generation model. Return only the enhanced "
        "visual prompt, without labels or explanation.\n\n"
        f'User prompt: "{prompt}"\n'
        f"Target size: {int(inputs.width)}x{int(inputs.height)}"
    )
