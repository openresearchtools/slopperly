"""Text-to-image via the local ComfyUI Ideogram 4 workflow."""

from ...models.base import InputSpec, ModelInputs, ModelPlugin, ParamSpec, UISection
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import clean_filename, solve_path


WORKFLOW_ID = "ideogram4_t2i"


class Ideogram4Plugin(ModelPlugin):
    MODEL_ID = "ideogram-ai/ideogram-4-nf4-diffusers"
    DISPLAY_NAME = "Image: Ideogram 4"
    DESCRIPTION = "Text-to-image via the local ComfyUI Ideogram 4 workflow"
    MODEL_TYPE = "image"
    INPUTS = InputSpec.PROMPT | InputSpec.LORA
    UI_SECTIONS = [
        UISection.PROMPT,
        UISection.RESOLUTION,
        UISection.FRAMES,
        UISection.STEPS,
        UISection.GUIDANCE,
        UISection.SEED,
        UISection.LORA,
    ]
    PARAMS = ParamSpec(steps=20, guidance=4.0)
    REQUIRED_PACKAGES = []
    supports_inpaint = False
    supports_img2img = False
    uses_standard_input_strip = False

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

    def draw_post_enhance_ui(self, col, context) -> None:
        col2 = col.column(heading="Prompt Upsampling", align=True)
        row = col2.row()
        row.prop(context.scene, "ideogram_prompt_upsampling", text="Enable")

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs):
        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        _record_unmapped_ui_notes(pipe_obj, inputs, scene)
        _prepare_ideogram_inputs(inputs, steps_default=self.PARAMS.steps, guidance_default=self.PARAMS.guidance)
        self.set_phase(inputs, "Generating with local ComfyUI Ideogram 4")
        filename = clean_filename(f"{inputs.seed}_ideogram4") or "ideogram4"
        destination = solve_path(filename + ".png")
        return gateway.run_comfy_workflow(
            WORKFLOW_ID,
            inputs,
            scene,
            prefs,
            destination=destination,
            timeout=float(getattr(prefs, "comfyui_timeout", 3600.0) or 3600.0),
        )


def _prepare_ideogram_inputs(
    inputs: ModelInputs,
    *,
    steps_default: int,
    guidance_default: float,
) -> None:
    inputs.ideogram_model = "ideogram4_fp8_scaled.safetensors"
    inputs.ideogram_unconditional_model = "ideogram4_unconditional_fp8_scaled.safetensors"
    inputs.ideogram_text_encoder = "qwen3vl_8b_fp8_scaled.safetensors"
    inputs.ideogram_clip_type = "ideogram4"
    inputs.ideogram_vae = "flux2-vae.safetensors"
    inputs.ideogram_sampler = "euler"
    inputs.ideogram_steps = int(inputs.steps or steps_default)
    inputs.ideogram_guidance = float(inputs.guidance or guidance_default)
    inputs.ideogram_scheduler_mu = 0.0
    inputs.ideogram_scheduler_std = 1.75
    inputs.ideogram_cfg_override = 3.0
    inputs.ideogram_cfg_override_start = 0.7
    inputs.ideogram_cfg_override_end = 1.0


def _record_unmapped_ui_notes(pipe_obj, inputs: ModelInputs, scene) -> None:
    notes = []
    custom_loras = pipe_obj.get("enabled_loras", []) if isinstance(pipe_obj, dict) else []
    if custom_loras:
        notes.append(
            "Ideogram 4 local Comfy workflow preserves the LoRA UI, but dynamic "
            "project LoRA injection is not mapped in this certified graph yet."
        )
    if getattr(scene, "ideogram_prompt_upsampling", False):
        notes.append(
            "Ideogram 4 prompt upsampling UI is preserved, but this local Comfy "
            "graph sends the prompt directly. Use structured JSON prompts until "
            "a local llama.cpp prompt-builder path is certified."
        )
    if notes:
        existing = getattr(inputs, "usage_note", "")
        prefix = (existing + "\n") if existing else ""
        inputs.usage_note = prefix + "\n".join(notes)
