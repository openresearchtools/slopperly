"""Text-to-image and img2img via local ComfyUI Z-Image workflows."""

from ...models.base import ModelInputs, ModelPlugin, InputSpec, ParamSpec, UISection
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import clean_filename, solve_path


BASE_T2I_WORKFLOW_ID = "zimage_t2i_i2i"
BASE_I2I_WORKFLOW_ID = "zimage_t2i_i2i_img2img"
TURBO_T2I_WORKFLOW_ID = "zimage_turbo_t2i_i2i"
TURBO_I2I_WORKFLOW_ID = "zimage_turbo_t2i_i2i_img2img"


class _ZImageBase(ModelPlugin):
    MODEL_TYPE = "image"
    REQUIRED_PACKAGES = []
    supports_inpaint = False

    INPUTS = InputSpec.PROMPT | InputSpec.NEG_PROMPT | InputSpec.IMAGE
    UI_SECTIONS = [
        UISection.PROMPT,
        UISection.NEG_PROMPT,
        UISection.IMAGE_STRIP,
        UISection.RESOLUTION,
        UISection.FRAMES,
        UISection.STEPS,
        UISection.GUIDANCE,
        UISection.IMAGE_STRENGTH,
        UISection.SEED,
    ]

    COMFY_MODEL = ""
    T2I_WORKFLOW_ID = ""
    I2I_WORKFLOW_ID = ""
    TURBO_PROFILE = False

    def load(self, prefs, scene, **kw):
        return {
            "gateway": SlopperlyRuntimeGateway(),
            "last_model_card": self.MODEL_ID,
        }

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs):
        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        workflow_id = self.T2I_WORKFLOW_ID
        stem = self.COMFY_MODEL.removesuffix(".safetensors")
        if inputs.mode == "img2img" and inputs.image is not None:
            workflow_id = self.I2I_WORKFLOW_ID
            stem = f"{stem}_i2i"
            inputs.zimage_denoise = max(0.0, min(1.0, 1.0 - float(inputs.strength)))
        else:
            inputs.zimage_denoise = 1.0

        inputs.zimage_model = self.COMFY_MODEL
        inputs.zimage_text_encoder = "qwen_3_4b.safetensors"
        inputs.zimage_vae = "ae.safetensors"
        inputs.zimage_sampler = "res_multistep"
        inputs.zimage_scheduler = "simple"
        if self.TURBO_PROFILE:
            inputs.zimage_cfg = max(1.0, float(inputs.guidance or 0.0))
            if inputs.neg_prompt:
                inputs.usage_note = (
                    (getattr(inputs, "usage_note", "") + "\n")
                    if getattr(inputs, "usage_note", "")
                    else ""
                ) + (
                    "Z-Image Turbo uses the official Comfy no-CFG graph with "
                    "ConditioningZeroOut; the negative prompt field is preserved "
                    "in the UI but not consumed by this Turbo workflow."
                )
        else:
            inputs.zimage_cfg = float(inputs.guidance or self.PARAMS.guidance)

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


class ZImagePlugin(_ZImageBase):
    MODEL_ID = "Tongyi-MAI/Z-Image"
    DISPLAY_NAME = "Image: Z-Image"
    DESCRIPTION = "Text-to-image and img2img via local ComfyUI Z-Image"
    PARAMS = ParamSpec(steps=30, guidance=7.0)
    COMFY_MODEL = "z_image_bf16.safetensors"
    T2I_WORKFLOW_ID = BASE_T2I_WORKFLOW_ID
    I2I_WORKFLOW_ID = BASE_I2I_WORKFLOW_ID


class ZImageTurboPlugin(_ZImageBase):
    MODEL_ID = "Tongyi-MAI/Z-Image-Turbo"
    DISPLAY_NAME = "Image: Z-Image Turbo (fast)"
    DESCRIPTION = "Fast text-to-image and img2img via local ComfyUI Z-Image Turbo"
    PARAMS = ParamSpec(steps=8, guidance=0.0)
    COMFY_MODEL = "z_image_turbo_bf16.safetensors"
    T2I_WORKFLOW_ID = TURBO_T2I_WORKFLOW_ID
    I2I_WORKFLOW_ID = TURBO_I2I_WORKFLOW_ID
    TURBO_PROFILE = True
