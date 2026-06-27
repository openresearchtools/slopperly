"""Text-to-image and img2img via local ComfyUI Qwen-Image-2512 workflows."""

from ...models.base import ModelInputs, ModelPlugin, InputSpec, ParamSpec, UISection
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import clean_filename, solve_path


T2I_WORKFLOW_ID = "qwen_image_2512_t2i_gguf"
I2I_WORKFLOW_ID = "qwen_image_2512_i2i_gguf"


class QwenImagePlugin(ModelPlugin):
    MODEL_ID     = "Qwen/Qwen-Image-2512"
    DISPLAY_NAME = "Image: Qwen Image 2512"
    MODEL_TYPE   = "image"
    DESCRIPTION  = "High-quality text-to-image and img2img via local ComfyUI Qwen-Image-2512 Q5 GGUF"

    INPUTS       = InputSpec.PROMPT | InputSpec.IMAGE | InputSpec.LORA
    UI_SECTIONS  = [
        UISection.PROMPT, UISection.IMAGE_STRIP,
        UISection.RESOLUTION, UISection.FRAMES, UISection.STEPS, UISection.IMAGE_STRENGTH, UISection.SEED,
        UISection.LORA,
    ]
    PARAMS            = ParamSpec(steps=4, guidance=1.0)
    REQUIRED_PACKAGES = []
    supports_inpaint  = False

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
                "Qwen Image 2512 local Comfy workflows use the committed Lightning adapter. "
                "Project LoRA adapters remain visible in the UI but are not yet dynamically "
                "injected into these workflow packs."
            )

        workflow_id = T2I_WORKFLOW_ID
        stem = "qwen_image_2512"
        if inputs.mode == "img2img" and inputs.image is not None:
            workflow_id = I2I_WORKFLOW_ID
            stem = "qwen_image_2512_i2i"
            inputs.qwen_image_denoise = max(0.0, min(1.0, 1.0 - float(inputs.strength)))
        else:
            inputs.qwen_image_denoise = 1.0

        inputs.qwen_image_model = "qwen-image-2512-Q5_K_M.gguf"
        inputs.qwen_image_text_encoder = "qwen_2.5_vl_7b_fp8_scaled.safetensors"
        inputs.qwen_image_vae = "qwen_image_vae.safetensors"
        inputs.qwen_image_lightning_lora = "Qwen-Image-2512-Lightning-4steps-V1.0-bf16.safetensors"
        inputs.qwen_image_lora_strength = 1.0
        inputs.qwen_image_cfg = float(inputs.guidance or 1.0)
        inputs.qwen_image_sampler = "euler"
        inputs.qwen_image_scheduler = "simple"

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
