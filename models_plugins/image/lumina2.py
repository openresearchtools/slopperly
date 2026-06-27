"""Text-to-image via the local ComfyUI Lumina-Image 2.0 workflow."""

from ...models.base import InputSpec, ModelInputs, ModelPlugin, ParamSpec, UISection
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import clean_filename, solve_path


WORKFLOW_ID = "lumina2_t2i"


class Lumina2Plugin(ModelPlugin):
    MODEL_ID = "Alpha-VLLM/Lumina-Image-2.0"
    DISPLAY_NAME = "Image: Lumina-Image 2.0"
    MODEL_TYPE = "image"
    DESCRIPTION = "High-quality text-to-image via the local ComfyUI Lumina-Image 2.0 workflow"

    INPUTS = InputSpec.PROMPT | InputSpec.NEG_PROMPT
    UI_SECTIONS = [
        UISection.PROMPT,
        UISection.NEG_PROMPT,
        UISection.RESOLUTION,
        UISection.FRAMES,
        UISection.STEPS,
        UISection.GUIDANCE,
        UISection.SEED,
    ]
    PARAMS = ParamSpec(steps=30, guidance=4.0)
    REQUIRED_PACKAGES = []
    supports_inpaint = False
    supports_img2img = False
    uses_standard_input_strip = False

    def load(self, prefs, scene, **kw):
        return {
            "gateway": SlopperlyRuntimeGateway(),
            "last_model_card": self.MODEL_ID,
        }

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs):
        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        _prepare_lumina_inputs(inputs)
        self.set_phase(inputs, "Generating with local ComfyUI Lumina-Image 2.0")
        filename = clean_filename(f"{inputs.seed}_lumina2") or "lumina2"
        destination = solve_path(filename + ".png")
        return gateway.run_comfy_workflow(
            WORKFLOW_ID,
            inputs,
            scene,
            prefs,
            destination=destination,
            timeout=float(getattr(prefs, "comfyui_timeout", 3600.0) or 3600.0),
        )


def _prepare_lumina_inputs(inputs: ModelInputs) -> None:
    inputs.lumina_checkpoint = "lumina_2.safetensors"
    inputs.lumina_system_prompt = "superior"
    inputs.lumina_shift = 6.0
    inputs.lumina_sampler = "res_multistep"
    inputs.lumina_scheduler = "simple"
    inputs.lumina_denoise = 1.0
