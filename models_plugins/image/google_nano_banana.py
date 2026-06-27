"""Saved-project image alias routed to the local Qwen Image Edit workflow."""

from ...models.base import InputSpec, ModelInputs, ModelPlugin, ParamSpec, UISection
from ...utils.helpers import clean_filename, solve_path
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway


class GoogleNanoBananaPlugin(ModelPlugin):
    MODEL_ID = "google/nano-banana"
    DISPLAY_NAME = "Image: Local Qwen Edit (legacy alias)"
    MODEL_TYPE = "image"
    DESCRIPTION = (
        "Hidden compatibility alias for saved projects; production dropdowns use "
        "the local Qwen Image Edit entry."
    )
    INPUTS = InputSpec.PROMPT | InputSpec.IMAGE
    UI_SECTIONS = [UISection.PROMPT]
    PARAMS = ParamSpec(width=1024, height=1024)
    REQUIRED_PACKAGES = []
    production_visible = False
    alias_target = "qwen_image_edit_2511_multi_gguf"

    supports_inpaint = False
    supports_img2img = True
    show_enhance = False
    uses_strip_power = False
    supports_batch = False

    def load(self, prefs, scene, **kw):
        return {"pipe": None, "last_model_card": self.MODEL_ID}

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs):
        self.set_phase(inputs, "Running local Qwen Image Edit alias")
        if getattr(inputs, "image", None) is not None and not getattr(inputs, "images", None):
            inputs.images = [inputs.image]
        inputs.qwen_image_edit_enable_lightning = True
        inputs.qwen_image_edit_lightning_lora = "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"
        inputs.qwen_image_edit_lora_strength = 1.0
        inputs.qwen_image_edit_cfg = 1.0
        inputs.qwen_image_edit_sampler = "euler"
        inputs.qwen_image_edit_scheduler = "simple"
        inputs.qwen_image_edit_denoise = 1.0
        inputs.qwen_image_edit_model = "qwen-image-edit-2511-Q5_K_M.gguf"
        inputs.qwen_image_edit_text_encoder = "qwen_2.5_vl_7b_fp8_scaled.safetensors"
        inputs.qwen_image_edit_vae = "qwen_image_vae.safetensors"
        stem = clean_filename((inputs.prompt or "qwen_edit")[:30]) or "qwen_edit"
        destination = solve_path(stem + ".png")
        return SlopperlyRuntimeGateway().run_comfy_workflow(
            self.alias_target,
            inputs,
            scene,
            prefs,
            destination=destination,
        )
