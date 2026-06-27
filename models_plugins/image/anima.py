"""Text-to-image and img2img via local ComfyUI Anima workflows."""

from ...models.base import ModelInputs, ModelPlugin, InputSpec, ParamSpec, UISection
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import clean_filename, solve_path


T2I_WORKFLOW_ID = "anima_t2i_i2i"
I2I_WORKFLOW_ID = "anima_t2i_i2i_img2img"


class AnimaPlugin(ModelPlugin):
    MODEL_ID     = "mrfatso/anima-preview3-diffusers"
    DISPLAY_NAME = "Image: Anima"
    MODEL_TYPE   = "image"
    DESCRIPTION  = "Anime-style generation via Anima with txt2img, img2img, and LoRA support"

    INPUTS       = InputSpec.PROMPT | InputSpec.NEG_PROMPT | InputSpec.IMAGE | InputSpec.LORA
    UI_SECTIONS  = [
        UISection.PROMPT, UISection.NEG_PROMPT, UISection.IMAGE_STRIP,
        UISection.RESOLUTION, UISection.FRAMES, UISection.STEPS, UISection.GUIDANCE,
        UISection.IMAGE_STRENGTH, UISection.SEED, UISection.LORA,
    ]
    PARAMS            = ParamSpec(steps=25, guidance=4.0)
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
        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        custom_loras = pipe_obj.get("enabled_loras", []) if isinstance(pipe_obj, dict) else []
        if custom_loras:
            inputs.usage_note = (
                (getattr(inputs, "usage_note", "") + "\n") if getattr(inputs, "usage_note", "") else ""
            ) + (
                "Anima local Comfy workflows preserve the LoRA UI, but dynamic project "
                "LoRA injection is not mapped in this certified graph yet."
            )

        workflow_id = T2I_WORKFLOW_ID
        stem = "anima_preview3"
        if inputs.mode == "img2img" and inputs.image is not None:
            workflow_id = I2I_WORKFLOW_ID
            stem = "anima_preview3_i2i"
            inputs.anima_denoise = max(0.0, min(1.0, 1.0 - float(inputs.strength)))
        else:
            inputs.anima_denoise = 1.0

        inputs.anima_model = "anima-preview3-base.safetensors"
        inputs.anima_text_encoder = "qwen_3_06b_base.safetensors"
        inputs.anima_clip_type = "stable_diffusion"
        inputs.anima_vae = "qwen_image_vae.safetensors"
        inputs.anima_sampler = "er_sde"
        inputs.anima_scheduler = "simple"

        self.set_phase(inputs, f"Generating with local ComfyUI {self.DISPLAY_NAME}")
        filename = clean_filename(f"{inputs.seed}_{stem}") or stem
        destination = solve_path(filename + ".png")
        return gateway.run_comfy_workflow(
            workflow_id,
            inputs,
            scene,
            prefs,
            destination=destination,
            timeout=float(getattr(prefs, "comfyui_timeout", 3600.0) or 3600.0),
        )
