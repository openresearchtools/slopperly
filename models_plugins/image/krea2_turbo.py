"""Text-to-image via the local ComfyUI Krea 2 Turbo workflow."""

from ...models.base import ModelInputs, ModelPlugin, InputSpec, ParamSpec, UISection
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import clean_filename, solve_path
from ._krea2_base import (
    _append_usage_note,
    _clear_krea_lora_mutator,
    _prepare_krea_inputs,
    _set_krea_lora_mutator,
)


WORKFLOW_ID = "krea2_turbo_t2i"


class Krea2TurboPlugin(ModelPlugin):
    MODEL_ID = "OzzyGT/Krea_2_Turbo_sdnq_dynamic_8bit"
    DISPLAY_NAME = "Image: Krea 2 Turbo"
    DESCRIPTION = "Fast text-to-image via the local ComfyUI Krea 2 Turbo workflow"
    MODEL_TYPE = "image"
    INPUTS = InputSpec.PROMPT | InputSpec.NEG_PROMPT | InputSpec.LORA
    UI_SECTIONS = [
        UISection.PROMPT,
        UISection.NEG_PROMPT,
        UISection.RESOLUTION,
        UISection.FRAMES,
        UISection.STEPS,
        UISection.GUIDANCE,
        UISection.SEED,
        UISection.LORA,
    ]
    PARAMS = ParamSpec(steps=8, guidance=1.0)
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

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs):
        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        notes = []
        custom_loras = pipe_obj.get("enabled_loras", []) if isinstance(pipe_obj, dict) else []
        applied_loras = _set_krea_lora_mutator(inputs, custom_loras)
        if applied_loras:
            notes.append(
                f"Krea 2 Turbo applied {applied_loras} selected LoRA(s) through local "
                "ComfyUI LoraLoaderModelOnly."
            )
        if inputs.neg_prompt:
            notes.append(
                "Krea 2 Turbo uses the official Comfy Turbo graph with "
                "ConditioningZeroOut; the negative prompt field is preserved in the UI "
                "but not consumed by this Turbo workflow."
            )
        if notes:
            _append_usage_note(inputs, "\n".join(notes))

        _prepare_krea_inputs(
            inputs,
            model_name="krea2_turbo_fp8_scaled.safetensors",
            steps_default=self.PARAMS.steps,
            guidance_default=self.PARAMS.guidance,
            turbo=True,
        )
        self.set_phase(inputs, "Generating with local ComfyUI Krea 2 Turbo")
        filename = clean_filename(f"{inputs.seed}_krea2_turbo") or "krea2_turbo"
        destination = solve_path(filename + ".png")
        try:
            return gateway.run_comfy_workflow(
                WORKFLOW_ID,
                inputs,
                scene,
                prefs,
                destination=destination,
                timeout=float(getattr(prefs, "comfyui_timeout", 3600.0) or 3600.0),
            )
        finally:
            _clear_krea_lora_mutator(inputs)
