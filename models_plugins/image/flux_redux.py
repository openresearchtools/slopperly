"""FLUX Redux image restyling through local ComfyUI."""

from ...models.base import ModelInputs, ModelPlugin, InputSpec, ParamSpec, UISection
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import clean_filename, solve_path


WORKFLOW_ID = "flux_redux_restyle"


class FluxReduxPlugin(ModelPlugin):
    MODEL_ID     = "Runware/FLUX.1-Redux-dev"
    DISPLAY_NAME = "Image: FLUX Redux (image restyle)"
    MODEL_TYPE   = "image"
    DESCRIPTION  = "Image restyling via local ComfyUI FLUX Redux"

    INPUTS       = InputSpec.IMAGE
    UI_SECTIONS  = [
        UISection.IMAGE_STRIP,
        UISection.RESOLUTION, UISection.FRAMES, UISection.STEPS, UISection.GUIDANCE, UISection.SEED,
    ]
    PARAMS       = ParamSpec(steps=25, guidance=3.5)
    REQUIRED_PACKAGES          = []
    supports_inpaint           = False
    supports_img2img           = False
    uses_standard_input_strip  = False

    def load(self, prefs, scene, **kw):
        return {
            "gateway": SlopperlyRuntimeGateway(),
            "last_model_card": self.MODEL_ID,
        }

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs):
        if inputs.image is None:
            raise ValueError("FLUX Redux requires an input image.")

        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        inputs.flux_redux_prompt = ""
        inputs.flux_redux_model = "flux1-dev.safetensors"
        inputs.flux_redux_weight_dtype = "fp8_e4m3fn"
        inputs.flux_redux_clip_l = "clip_l.safetensors"
        inputs.flux_redux_t5 = "t5xxl_fp16.safetensors"
        inputs.flux_redux_clip_type = "flux"
        inputs.flux_redux_vae = "ae.safetensors"
        inputs.flux_redux_style_model = "flux1-redux-dev.safetensors"
        inputs.flux_redux_clip_vision = "sigclip_vision_patch14_384.safetensors"
        inputs.flux_redux_flux_guidance = float(inputs.guidance or 3.5)
        inputs.flux_redux_sampler = "euler"
        inputs.flux_redux_scheduler = "simple"
        inputs.flux_redux_denoise = 1.0
        inputs.flux_redux_max_shift = 1.15
        inputs.flux_redux_base_shift = 0.5

        self.set_phase(inputs, f"Generating with local ComfyUI {self.DISPLAY_NAME}")
        filename = clean_filename(f"{inputs.seed}_flux_redux_restyle") or "flux_redux_restyle"
        destination = solve_path(filename + ".png")
        return gateway.run_comfy_workflow(
            WORKFLOW_ID,
            inputs,
            scene,
            prefs,
            destination=destination,
            timeout=float(getattr(prefs, "comfyui_timeout", 3600.0) or 3600.0),
        )
