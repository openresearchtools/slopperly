"""Text-to-music via the local Slopperly ComfyUI Stable Audio 3 workflow."""

from ...models.base import ModelPlugin, InputSpec, UISection, ParamSpec, ModelInputs
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import solve_path, clean_filename


WORKFLOW_ID = "stable_audio_3_medium_base"


class StableAudio3Plugin(ModelPlugin):
    MODEL_ID = "cocktailpeanut/stable-audio-3-medium-base"
    DISPLAY_NAME = "Music: Stable Audio 3 (Local Comfy)"
    MODEL_TYPE = "audio"
    DESCRIPTION = "Text to music via the local ComfyUI Stable Audio 3 workflow"

    INPUTS = InputSpec.PROMPT | InputSpec.NEG_PROMPT
    UI_SECTIONS = [
        UISection.PROMPT,
        UISection.NEG_PROMPT,
        UISection.AUDIO_DURATION,
        UISection.STEPS,
        UISection.GUIDANCE,
        UISection.SEED,
    ]
    PARAMS = ParamSpec(steps=50, guidance=7.0, audio_length=30.0)
    REQUIRED_PACKAGES = []

    def load(self, prefs, scene, **kw):
        return {
            "gateway": SlopperlyRuntimeGateway(),
            "last_model_card": self.MODEL_ID,
        }

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs) -> str:
        gateway = (pipe_obj or {}).get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        self.set_phase(inputs, "Generating audio with local ComfyUI Stable Audio 3")
        filename = solve_path(
            clean_filename(f"{inputs.seed}_{inputs.prompt}_stable_audio_3") + ".flac"
        )
        return gateway.run_comfy_workflow(
            WORKFLOW_ID,
            inputs,
            scene,
            prefs,
            destination=filename,
        )
