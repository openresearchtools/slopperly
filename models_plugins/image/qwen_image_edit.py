"""Multi-image editing via the local ComfyUI Qwen-Image-Edit-2511 workflow."""

from pathlib import Path

from ...models.base import ModelInputs, ModelPlugin, InputSpec, ParamSpec, UISection
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import clean_filename, find_strip_by_name, get_strip_path, solve_path


WORKFLOW_ID = "qwen_image_edit_2511_multi_gguf"


class QwenImageEditPlugin(ModelPlugin):
    MODEL_ID     = "Qwen/Qwen-Image-Edit-2511"
    DISPLAY_NAME = "Image: Qwen Image Edit (multi-image)"
    MODEL_TYPE   = "image"
    DESCRIPTION  = "Multi-image instruction editing via local ComfyUI Qwen-Image-Edit-2511 Q5 GGUF"

    INPUTS       = InputSpec.PROMPT | InputSpec.NEG_PROMPT | InputSpec.MULTI_IMAGE | InputSpec.LORA
    UI_SECTIONS  = [
        UISection.PROMPT, UISection.NEG_PROMPT, UISection.MULTI_IMAGES,
        UISection.RESOLUTION, UISection.FRAMES, UISection.STEPS, UISection.SEED, UISection.LORA,
    ]
    PARAMS       = ParamSpec(steps=4, max_multi_images=3)
    REQUIRED_PACKAGES          = []
    supports_inpaint           = False
    supports_img2img           = True
    requires_input_strip       = True
    uses_standard_input_strip  = False

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

    def draw_custom_ui(self, col, context) -> bool:
        scene = context.scene
        try:
            col.prop(scene, "input_strips", text="Input")
        except Exception:
            pass
        if scene.sequence_editor is None:
            return True
        for attr, action in [
            ("qwen_strip_1", "qwen_select1"),
            ("qwen_strip_2", "qwen_select2"),
            ("qwen_strip_3", "qwen_select3"),
        ]:
            row = col.row(align=True)
            row.prop_search(
                scene, attr, scene.sequence_editor, "strips",
                text="Ref.", icon="FILE_IMAGE",
            )
            row.operator("sequencer.strip_picker", text="", icon="EYEDROPPER").action = action
        return True

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs):
        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        images = []
        if getattr(inputs, "image", None) is not None:
            images.append(inputs.image)
        images.extend(self._scene_reference_paths(scene))
        images = [image for image in images if image][:3]

        if not images:
            raise ValueError(
                "Qwen Image Edit requires at least one image input. "
                "Select an image or movie strip and set Input to 'Strip', "
                "or pick strips using the image pickers below."
            )

        custom_loras = pipe_obj.get("enabled_loras", []) if isinstance(pipe_obj, dict) else []
        if custom_loras:
            inputs.usage_note = (
                (getattr(inputs, "usage_note", "") + "\n") if getattr(inputs, "usage_note", "") else ""
            ) + (
                "Qwen Image Edit local Comfy workflow uses the committed Lightning adapter. "
                "Project LoRA adapters remain visible in the UI but are not yet dynamically "
                "injected into this workflow pack."
            )

        inputs.images = images
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

        self.set_phase(inputs, "Generating with local ComfyUI Qwen Image Edit")
        filename = clean_filename(f"{inputs.seed}_qwen_image_edit") or "qwen_image_edit"
        destination = solve_path(filename + ".png")
        return gateway.run_comfy_workflow(
            WORKFLOW_ID,
            inputs,
            scene,
            prefs,
            destination=destination,
            timeout=float(getattr(prefs, "comfyui_timeout", 3600.0) or 3600.0),
        )

    def _scene_reference_paths(self, scene) -> list[str]:
        paths: list[str] = []
        for path_attr, strip_attr in [
            ("qwen_strip_1_path", "qwen_strip_1"),
            ("qwen_strip_2_path", "qwen_strip_2"),
            ("qwen_strip_3_path", "qwen_strip_3"),
        ]:
            path = getattr(scene, path_attr, "") or ""
            if path and Path(path).is_file():
                paths.append(path)
                continue
            strip_name = getattr(scene, strip_attr, "") or ""
            if not strip_name:
                continue
            strip = find_strip_by_name(scene, strip_name)
            if strip is None:
                continue
            strip_path = get_strip_path(strip)
            if strip_path:
                paths.append(strip_path)
        return paths
