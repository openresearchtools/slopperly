"""FLUX.1 Canny control generation via local ComfyUI."""

from ...models.base import ModelInputs, ModelPlugin, InputSpec, ParamSpec, UISection
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import clean_filename, solve_path


WORKFLOW_ID = "flux1_canny_control"


class FluxCannyPlugin(ModelPlugin):
    MODEL_ID     = "fuliucansheng/FLUX.1-Canny-dev-diffusers-lora"
    DISPLAY_NAME = "Image: FLUX Canny ControlNet"
    MODEL_TYPE   = "image"
    DESCRIPTION  = "Edge-guided generation through local ComfyUI FLUX.1 Canny"

    INPUTS       = InputSpec.PROMPT | InputSpec.IMAGE | InputSpec.LORA
    UI_SECTIONS  = [
        UISection.PROMPT, UISection.IMAGE_STRIP,
        UISection.RESOLUTION, UISection.FRAMES, UISection.STEPS, UISection.GUIDANCE,
        UISection.IMAGE_STRENGTH, UISection.SEED,
        UISection.LORA,
    ]
    PARAMS       = ParamSpec(steps=28, guidance=3.5)
    REQUIRED_PACKAGES = []
    supports_inpaint  = False
    supports_img2img  = True

    def load(self, prefs, scene, **kw):
        enabled = [
            (getattr(item, "name", ""), float(getattr(item, "weight_value", 1.0) or 1.0))
            for item in kw.get("enabled_items", [])
            if getattr(item, "enabled", True) and getattr(item, "name", "")
        ]
        return {
            "gateway": SlopperlyRuntimeGateway(),
            "last_model_card": self.MODEL_ID,
            "enabled_loras": enabled,
        }

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs):
        if inputs.image is None:
            raise ValueError("FLUX Canny requires an input image.")

        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        if isinstance(pipe_obj, dict) and pipe_obj.get("enabled_loras"):
            self._append_usage_note(
                inputs,
                "FLUX.1 Canny local Comfy workflow preserves the LoRA UI, but "
                "dynamic project LoRA injection is not mapped in this certified graph yet.",
            )
        self._append_usage_note(
            inputs,
            "The official FLUX.1 Canny Comfy graph uses InstructPixToPixConditioning "
            "and does not expose a separate conditioning-strength input; the image "
            "strength slider is preserved in the UI and recorded as unmapped.",
        )

        inputs.flux1_canny_model = "flux1-canny-dev.safetensors"
        inputs.flux1_canny_weight_dtype = "fp8_e4m3fn"
        inputs.flux1_canny_clip_l = "clip_l.safetensors"
        inputs.flux1_canny_t5 = "t5xxl_fp16.safetensors"
        inputs.flux1_canny_clip_type = "flux"
        inputs.flux1_canny_vae = "ae.safetensors"
        inputs.flux1_canny_negative_prompt = ""
        inputs.flux1_canny_flux_guidance = float(inputs.guidance or 3.5)
        inputs.flux1_canny_cfg = 1.0
        inputs.flux1_canny_sampler = "euler"
        inputs.flux1_canny_scheduler = "normal"
        inputs.flux1_canny_denoise = 1.0
        inputs.flux1_canny_low_threshold = 50
        inputs.flux1_canny_high_threshold = 200
        inputs.flux1_canny_resolution = int(inputs.width or 1024)

        self.set_phase(inputs, f"Generating with local ComfyUI {self.DISPLAY_NAME}")
        filename = clean_filename(f"{inputs.seed}_flux1_canny_control") or "flux1_canny_control"
        destination = solve_path(filename + ".png")
        return gateway.run_comfy_workflow(
            WORKFLOW_ID,
            inputs,
            scene,
            prefs,
            destination=destination,
            timeout=float(getattr(prefs, "comfyui_timeout", 3600.0) or 3600.0),
        )

    @staticmethod
    def _append_usage_note(inputs: ModelInputs, message: str) -> None:
        prefix = (getattr(inputs, "usage_note", "") + "\n") if getattr(inputs, "usage_note", "") else ""
        inputs.usage_note = prefix + message
