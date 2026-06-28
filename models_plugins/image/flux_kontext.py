"""Instruction-based FLUX Kontext image editing through local ComfyUI."""

from pathlib import Path

from ...models.base import ModelInputs, ModelPlugin, InputSpec, ParamSpec, UISection
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import clean_filename, find_strip_by_name, get_strip_path, solve_path


WORKFLOW_ID = "flux_kontext_edit"


class FluxKontextPlugin(ModelPlugin):
    MODEL_ID     = "yuvraj108c/FLUX.1-Kontext-dev"
    DISPLAY_NAME = "Image: FLUX Kontext (image editing)"
    MODEL_TYPE   = "image"
    DESCRIPTION  = "Instruction-based image editing via local ComfyUI FLUX.1 Kontext"

    INPUTS       = InputSpec.PROMPT | InputSpec.IMAGE | InputSpec.LORA
    UI_SECTIONS  = [
        UISection.PROMPT, UISection.IMAGE_STRIP,
        UISection.RESOLUTION, UISection.FRAMES, UISection.STEPS, UISection.GUIDANCE,
        UISection.IMAGE_STRENGTH, UISection.SEED, UISection.LORA,
    ]
    PARAMS       = ParamSpec(steps=28, guidance=3.5)
    REQUIRED_PACKAGES = []
    supports_inpaint  = True
    inpaint_uses_strength = True
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
        image_input = self._resolve_input_image(inputs, scene)
        if image_input is None:
            raise ValueError("FLUX Kontext requires an input image or movie strip.")
        inputs.image = image_input

        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        if isinstance(pipe_obj, dict) and pipe_obj.get("enabled_loras"):
            self._append_usage_note(
                inputs,
                "FLUX Kontext local Comfy workflow preserves the LoRA UI, but "
                "dynamic project LoRA injection is not mapped in this certified graph yet.",
            )
        if inputs.mode == "inpaint" or inputs.inpaint_mask is not None:
            self._append_usage_note(
                inputs,
                "The committed FLUX Kontext Comfy graph is the official reference-latent "
                "image-edit graph. The inpaint mask UI is preserved, but masked inpaint "
                "requires a separately certified local workflow before production exposure.",
            )
        self._append_usage_note(
            inputs,
            "The official FLUX Kontext Comfy graph uses reference-latent conditioning and "
            "fixed KSampler denoise. The image strength slider is preserved in the UI and "
            "recorded as unmapped until a certified strength-aware graph is added.",
        )

        inputs.flux_kontext_model = "flux1-kontext-dev-Q5_K_M.gguf"
        inputs.flux_kontext_clip_l = "clip_l.safetensors"
        inputs.flux_kontext_t5 = "t5xxl_fp8_e4m3fn_scaled.safetensors"
        inputs.flux_kontext_clip_type = "flux"
        inputs.flux_kontext_vae = "ae.safetensors"
        inputs.flux_kontext_flux_guidance = float(inputs.guidance or 3.5)
        inputs.flux_kontext_cfg = 1.0
        inputs.flux_kontext_sampler = "euler"
        inputs.flux_kontext_scheduler = "simple"
        inputs.flux_kontext_denoise = 1.0

        self.set_phase(inputs, f"Generating with local ComfyUI {self.DISPLAY_NAME}")
        filename = clean_filename(f"{inputs.seed}_flux_kontext_edit") or "flux_kontext_edit"
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
    def _resolve_input_image(inputs: ModelInputs, scene):
        if isinstance(inputs.image, (str, Path)) and Path(inputs.image).is_file():
            return str(inputs.image)
        if inputs.image is not None and hasattr(inputs.image, "save"):
            return inputs.image

        strip_name = getattr(scene, "kontext_strip_1", None) if scene is not None else None
        if strip_name:
            strip = find_strip_by_name(scene, strip_name)
            strip_path = get_strip_path(strip) if strip is not None else None
            if strip_path and Path(strip_path).is_file():
                return strip_path

        explicit_path = getattr(scene, "kontext_strip_1_path", "") if scene is not None else ""
        if explicit_path and Path(explicit_path).is_file():
            return str(explicit_path)
        return None

    @staticmethod
    def _append_usage_note(inputs: ModelInputs, message: str) -> None:
        prefix = (getattr(inputs, "usage_note", "") + "\n") if getattr(inputs, "usage_note", "") else ""
        inputs.usage_note = prefix + message
