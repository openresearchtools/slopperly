"""AI relighting through local ComfyUI FLUX Kontext + Relight LoRA."""

from ...models.base import ModelInputs, ModelPlugin, InputSpec, ParamSpec, UISection
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import ILLUMINATION_OPTIONS, clean_filename, solve_path


WORKFLOW_ID = "kontext_relight"


class KontextRelightPlugin(ModelPlugin):
    MODEL_ID     = "kontext-community/relighting-kontext-dev-lora-v3"
    DISPLAY_NAME = "Image: Kontext Relight"
    MODEL_TYPE   = "image"
    DESCRIPTION  = "AI image relighting via local ComfyUI FLUX Kontext + Relight LoRA"

    INPUTS       = InputSpec.PROMPT | InputSpec.IMAGE
    UI_SECTIONS  = [
        UISection.PROMPT, UISection.IMAGE_STRIP,
        UISection.RESOLUTION, UISection.FRAMES, UISection.STEPS, UISection.GUIDANCE,
        UISection.ILLUMINATION, UISection.SEED,
    ]
    PARAMS       = ParamSpec(steps=28, guidance=3.5)
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
            raise ValueError("Kontext Relight requires an input image.")

        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        inputs.kontext_relight_prompt = self._build_relight_prompt(inputs, scene)
        inputs.kontext_relight_model = "flux1-kontext-dev-Q5_K_M.gguf"
        inputs.kontext_relight_lora = "relighting-kontext-dev-lora-v3-comfy.safetensors"
        inputs.kontext_relight_lora_strength = 0.75
        inputs.kontext_relight_clip_l = "clip_l.safetensors"
        inputs.kontext_relight_t5 = "t5xxl_fp8_e4m3fn_scaled.safetensors"
        inputs.kontext_relight_clip_type = "flux"
        inputs.kontext_relight_vae = "ae.safetensors"
        inputs.kontext_relight_flux_guidance = float(inputs.guidance or 3.5)
        inputs.kontext_relight_cfg = 1.0
        inputs.kontext_relight_sampler = "euler"
        inputs.kontext_relight_scheduler = "simple"
        inputs.kontext_relight_denoise = 1.0

        self.set_phase(inputs, f"Generating with local ComfyUI {self.DISPLAY_NAME}")
        filename = clean_filename(f"{inputs.seed}_kontext_relight") or "kontext_relight"
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
    def _build_relight_prompt(inputs: ModelInputs, scene) -> str:
        if inputs.prompt:
            prompt_desc = inputs.prompt
            style_parts = ["with custom lighting"]
        else:
            illum_style = getattr(scene, "illumination_style", "")
            prompt_desc = ILLUMINATION_OPTIONS.get(illum_style, "")
            style_parts = [f"with {illum_style} lighting"] if illum_style else ["with relit lighting"]

        light_dir = getattr(scene, "light_direction", "auto")
        if light_dir != "auto":
            style_parts.append(f"coming from the {light_dir}")

        return (
            f"Relight the image {' '.join(style_parts)}. "
            f"{prompt_desc} "
            "Maintain the identity of the foreground subjects."
        )
