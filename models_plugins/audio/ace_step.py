"""Text-to-music via the local Slopperly ComfyUI ACE-Step 1.5 workflow."""

from dataclasses import replace

from ...models.base import ModelPlugin, InputSpec, UISection, ParamSpec, ModelInputs
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import solve_path, clean_filename


WORKFLOW_ID = "ace_step_15_music"


class AceStepPlugin(ModelPlugin):
    MODEL_ID = "ACE-Step/acestep-v15-xl-turbo-diffusers"
    DISPLAY_NAME = "Music: ACE-Step"
    MODEL_TYPE = "audio"
    DESCRIPTION = "High-quality text-to-music through the local ComfyUI ACE-Step 1.5 workflow"

    INPUTS = InputSpec.PROMPT | InputSpec.MUSIC_PARAMS
    UI_SECTIONS = [
        UISection.PROMPT,
        UISection.AUDIO_DURATION,
        UISection.STEPS, UISection.GUIDANCE,
        UISection.MUSIC_PARAMS,
        UISection.SEED,
    ]
    PARAMS = ParamSpec(steps=60, guidance=3.5, audio_length=30.0)
    REQUIRED_PACKAGES = []
    supports_inpaint = False
    supports_img2img = False

    def load(self, prefs, scene, **kw):
        return {
            "gateway": SlopperlyRuntimeGateway(),
            "last_model_card": self.MODEL_ID,
        }

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs) -> str:
        gateway = (pipe_obj or {}).get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        self.set_phase(inputs, "Generating audio with local ComfyUI ACE-Step 1.5")
        filename = solve_path(
            clean_filename(f"{inputs.seed}_{inputs.prompt[:30]}_ace_step_15") + ".flac"
        )
        workflow_inputs = replace(
            inputs,
            bpm=inputs.bpm or 120,
            key_scale=inputs.key_scale or "C major",
            time_signature=inputs.time_signature or "4",
        )
        return gateway.run_comfy_workflow(
            WORKFLOW_ID,
            workflow_inputs,
            scene,
            prefs,
            destination=filename,
        )
