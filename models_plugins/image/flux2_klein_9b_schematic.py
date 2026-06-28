"""Image to schematic maps via local ComfyUI FLUX.2 Klein 9B base LoRAs."""

from ...models.base import ModelInputs, ModelPlugin, InputSpec, ParamSpec, UISection
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import clean_filename, solve_path


WORKFLOW_ID = "flux2_klein_9b_schematic_lora"
_LORA_REPO = "nomadoor/flux-2-klein-9B-schematic-lora"
_LORA_FILES = {
    "DEPTH":      "flux2-klein-schematic-relative-depth-lora.safetensors",
    "NORMAL":     "flux2-klein-schematic-surface-normal-lora.safetensors",
    "BODY_POSE":  "flux2-klein-schematic-body-pose-lora.safetensors",
    "FULL_POSE":  "flux2-klein-schematic-full-pose-lora.safetensors",
    "BINARY_SEG": "flux2-klein-schematic-binary-segmentation-lora.safetensors",
    "AMODAL_SEG": "flux2-klein-schematic-amodal-segmentation-lora.safetensors",
}
_TRIGGER_PROMPTS = {
    "DEPTH":      "Generate a relative depth map of the input image.",
    "NORMAL":     "Generate a surface normal map of the input image.",
    "BODY_POSE":  "Generate a body pose map of all visible people in the input image.",
    "FULL_POSE":  "Generate a full pose map of all visible people in the input image.",
    "BINARY_SEG": "Generate a binary segmentation mask of {target} in the input image.",
    "AMODAL_SEG": "Generate an amodal segmentation mask of {target} in the input image.",
}
_FIXED_NEGATIVE = "text, worst quality, blurry, ugly"


class Flux2Klein9BSchematicPlugin(ModelPlugin):
    MODEL_ID     = _LORA_REPO
    DISPLAY_NAME = "Image: FLUX.2 Klein 9B Schematic"
    DESCRIPTION  = "Transform images into schematic maps via local ComfyUI Klein 9B LoRAs"
    MODEL_TYPE   = "image"
    INPUTS       = InputSpec.PROMPT | InputSpec.IMAGE
    UI_SECTIONS  = [
        UISection.PROMPT, UISection.IMAGE_STRIP,
        UISection.FRAMES, UISection.STEPS, UISection.GUIDANCE, UISection.SEED,
    ]
    PARAMS            = ParamSpec(steps=20, guidance=5.0)
    REQUIRED_PACKAGES = []
    supports_inpaint  = False
    supports_img2img  = True
    requires_input_strip       = True
    requires_no_style          = True
    preserve_image_dimensions  = True

    def on_model_selected(self, scene, context):
        mode   = self._mode(scene)
        target = (getattr(scene, "klein_schematic_target", "person") or "person").strip()
        trigger = _TRIGGER_PROMPTS[mode].format(target=target)
        current = scene.generate_movie_prompt or ""
        has_trigger = any(
            current.startswith(t.split("{")[0]) for t in _TRIGGER_PROMPTS.values()
        )
        if not has_trigger:
            scene.generate_movie_prompt = trigger + (" " + current if current else "")

    def load(self, prefs, scene, **kw):
        return {
            "gateway": SlopperlyRuntimeGateway(),
            "last_model_card": self.MODEL_ID,
        }

    def draw_custom_ui(self, col, context) -> bool:
        scene = context.scene
        row = col.row()
        row.enabled = False
        try:
            row.prop(scene, "input_strips", text="Input")
        except Exception:
            pass
        col.prop(scene, "klein_schematic_mode", text="Mode")
        if getattr(scene, "klein_schematic_mode", "DEPTH") in ("BINARY_SEG", "AMODAL_SEG"):
            col.prop(scene, "klein_schematic_target", text="Target")
        return True

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs):
        if inputs.image is None:
            raise ValueError("FLUX.2 Klein Schematic requires an image strip as input.")

        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        width, height = self._input_dimensions(inputs)
        inputs.width = width
        inputs.height = height
        inputs.flux2_klein_schematic_model = "flux-2-klein-base-9b-Q5_K_M.gguf"
        inputs.flux2_klein_schematic_lora = self._lora_file(scene)
        inputs.flux2_klein_schematic_lora_strength = 0.8
        inputs.flux2_klein_schematic_text_encoder = "qwen_3_8b.safetensors"
        inputs.flux2_klein_schematic_clip_type = "flux2"
        inputs.flux2_klein_schematic_vae = "flux2-vae.safetensors"
        inputs.flux2_klein_schematic_sampler = "euler"
        inputs.schematic_negative_prompt = _FIXED_NEGATIVE

        self.set_phase(inputs, f"Generating with local ComfyUI {self.DISPLAY_NAME}")
        filename = clean_filename(f"{inputs.seed}_flux2_klein_9b_schematic") or "flux2_klein_9b_schematic"
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
    def _mode(scene) -> str:
        mode = getattr(scene, "klein_schematic_mode", "DEPTH") if scene is not None else "DEPTH"
        return mode if mode in _LORA_FILES else "DEPTH"

    def _lora_file(self, scene) -> str:
        return _LORA_FILES[self._mode(scene)]

    @staticmethod
    def _input_dimensions(inputs: ModelInputs) -> tuple[int, int]:
        image = getattr(inputs, "image", None)
        if hasattr(image, "size"):
            width, height = image.size
            return int(width), int(height)
        return int(getattr(inputs, "width", 1024) or 1024), int(getattr(inputs, "height", 1024) or 1024)
