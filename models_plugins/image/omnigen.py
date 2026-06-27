"""Multi-image generation via the local ComfyUI OmniGen workflow."""

from ...models.base import ModelPlugin, InputSpec, UISection, ParamSpec, ModelInputs
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import clean_filename, find_strip_by_name, get_strip_path, solve_path


WORKFLOW_ID = "omnigen_v1_multi_image"


class OmniGenPlugin(ModelPlugin):
    MODEL_ID     = "Shitao/OmniGen-v1-diffusers"
    DISPLAY_NAME = "Image: OmniGen (multi-image)"
    MODEL_TYPE   = "image"
    DESCRIPTION  = "Multi-image / instruction-based generation via local ComfyUI OmniGen"

    INPUTS       = InputSpec.PROMPT | InputSpec.MULTI_IMAGE
    UI_SECTIONS  = [
        UISection.TRIPLE_PROMPT_IMG,
        UISection.RESOLUTION, UISection.FRAMES, UISection.STEPS, UISection.GUIDANCE, UISection.SEED,
    ]
    PARAMS       = ParamSpec(steps=50, guidance=3.0, max_multi_images=3)
    REQUIRED_PACKAGES          = []
    supports_inpaint           = False
    supports_img2img           = False
    uses_standard_input_strip  = False

    def load(self, prefs, scene, **kw):
        return {
            "gateway": SlopperlyRuntimeGateway(),
            "last_model_card": self.MODEL_ID,
        }

    def draw_custom_ui(self, col, context) -> bool:
        scene = context.scene
        if scene.sequence_editor is None:
            return True
        for idx in range(1, 4):
            col.prop(scene, f"omnigen_prompt_{idx}", text="", icon="ADD")
            row = col.row(align=True)
            row.prop_search(
                scene, f"omnigen_strip_{idx}", scene.sequence_editor, "strips",
                text="", icon="FILE_IMAGE",
            )
            row.operator("sequencer.strip_picker", text="", icon="EYEDROPPER").action = f"omni_select{idx}"
        return True

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs):
        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        images = [None, None, None]
        image_prompts = ["", "", ""]
        prompt = getattr(scene, "omnigen_prompt_1", inputs.prompt) or inputs.prompt
        for idx, strip_attr in enumerate(["omnigen_strip_1", "omnigen_strip_2", "omnigen_strip_3"], start=1):
            prompt_attr = f"omnigen_prompt_{idx}"
            slot_prompt = getattr(scene, prompt_attr, "") or ""
            image_prompts[idx - 1] = slot_prompt
            if idx > 1:
                prompt += slot_prompt
            strip_name = getattr(scene, strip_attr, None)
            if strip_name:
                strip = find_strip_by_name(scene, strip_name)
                if strip:
                    image_path = get_strip_path(strip)
                    if not image_path:
                        raise ValueError(f"OmniGen could not resolve strip path for {strip_name!r}.")
                    images[idx - 1] = image_path
                    prompt += f" <img><|image_{idx}|></img> "

        inputs.prompt = prompt.strip()
        inputs.images = images
        inputs.image_prompts = image_prompts
        inputs.omnigen_img_guidance_scale = float(getattr(scene, "img_guidance_scale", 1.6) or 1.6)
        inputs.omnigen_use_input_image_size_as_output = any(images)
        inputs.omnigen_model_precision = getattr(scene, "omnigen_model_precision", "Auto") or "Auto"
        inputs.omnigen_memory_management = getattr(
            scene,
            "omnigen_memory_management",
            "Memory Priority",
        ) or "Memory Priority"
        inputs.omnigen_separate_cfg_infer = bool(
            getattr(scene, "omnigen_separate_cfg_infer", True)
        )
        inputs.omnigen_max_input_image_size = int(
            getattr(scene, "omnigen_max_input_image_size", 1024) or 1024
        )

        self.set_phase(inputs, "Generating with local ComfyUI OmniGen")
        filename = clean_filename(f"{inputs.seed}_omnigen") or "omnigen"
        destination = solve_path(filename + ".png")
        return gateway.run_comfy_workflow(
            WORKFLOW_ID,
            inputs,
            scene,
            prefs,
            destination=destination,
            timeout=float(getattr(prefs, "comfyui_timeout", 3600.0) or 3600.0),
        )
