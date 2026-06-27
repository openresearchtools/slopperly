"""Local image super-resolution through a ComfyUI upscale workflow."""

from ...models.base import ModelPlugin, InputSpec, UISection, ParamSpec, ModelInputs
from ...utils.helpers import clean_filename, solve_path
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway


class MaxineVSRPlugin(ModelPlugin):
    MODEL_ID     = "nvidia/maxine-vsr"
    DISPLAY_NAME = "Image: Local Super Resolution"
    MODEL_TYPE   = "image"
    DESCRIPTION  = "Local ComfyUI image super-resolution using Real-ESRGAN"

    INPUTS      = InputSpec.IMAGE
    UI_SECTIONS = [UISection.RESOLUTION, UISection.FRAMES, UISection.SEED]
    PARAMS      = ParamSpec(width=1920, height=1080)

    REQUIRED_PACKAGES          = []
    supports_inpaint           = False
    supports_img2img           = True
    requires_input_strip       = True
    uses_standard_input_strip  = False
    show_enhance               = False
    supports_batch             = False

    def load(self, prefs, scene, **kw):
        return {
            "gateway": SlopperlyRuntimeGateway(),
            "last_model_card": self.MODEL_ID,
        }

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs):
        image = inputs.image
        if image is None:
            raise ValueError("Local Super Resolution requires an input image.")
        if getattr(image, "mode", "RGB") != "RGB":
            image = image.convert("RGB")
        inputs.image = image

        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        self.set_phase(inputs, "Upscaling with local ComfyUI")
        filename = clean_filename(f"{inputs.seed}_local_super_resolution") or "local_super_resolution"
        destination = solve_path(filename + ".png")
        return gateway.run_comfy_workflow(
            "local_image_vsr_upscale",
            inputs,
            scene,
            prefs,
            destination=destination,
            timeout=float(getattr(prefs, "comfyui_timeout", 3600.0) or 3600.0),
        )
