"""Background removal via the local ComfyUI BiRefNet/RMBG workflow."""

from ...models.base import ModelPlugin, InputSpec, UISection, ParamSpec, ModelInputs
from ...utils.helpers import clean_filename, solve_path
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway


class BiRefNetPlugin(ModelPlugin):
    MODEL_ID     = "ZhengPeng7/BiRefNet_HR"
    DISPLAY_NAME = "Image: Remove Background (BiRefNet)"
    MODEL_TYPE   = "image"
    DESCRIPTION  = "AI background removal via BiRefNet-HR"

    INPUTS       = InputSpec.IMAGE
    UI_SECTIONS  = [UISection.FRAMES]
    PARAMS       = ParamSpec()
    REQUIRED_PACKAGES          = []
    supports_inpaint           = False
    supports_img2img           = True
    requires_input_strip       = True
    uses_standard_input_strip  = False

    def load(self, prefs, scene, **kw):
        return {
            "gateway": SlopperlyRuntimeGateway(),
            "last_model_card": self.MODEL_ID,
        }

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs):
        image = inputs.image
        if image is None:
            raise ValueError("BiRefNet requires an input image.")
        if getattr(image, "mode", "RGB") != "RGB":
            image = image.convert("RGB")
        inputs.image = image

        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        self.set_phase(inputs, "Removing background with local ComfyUI")
        filename = clean_filename(f"{inputs.seed}_birefnet_rmbg") or "birefnet_rmbg"
        destination = solve_path(filename + ".png")
        return gateway.run_comfy_workflow(
            "birefnet_rmbg",
            inputs,
            scene,
            prefs,
            destination=destination,
            timeout=float(getattr(prefs, "comfyui_timeout", 3600.0) or 3600.0),
        )
