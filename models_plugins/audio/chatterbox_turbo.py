"""Fast TTS via local Slopperly ComfyUI Chatterbox Turbo workflows."""

from ...models.base import ModelPlugin, InputSpec, UISection, ParamSpec, ModelInputs
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import solve_path, clean_filename


WORKFLOW_ID = "chatterbox_turbo_tts_comfy"
WORKFLOW_REF_ID = "chatterbox_turbo_ref_tts_comfy"


class ChatterboxTurboPlugin(ModelPlugin):
    MODEL_ID = "ChatterboxTurbo"
    DISPLAY_NAME = "TTS/VC: Chatterbox Turbo"
    MODEL_TYPE = "audio"
    DESCRIPTION = "Fast text-to-speech via local ComfyUI Chatterbox Turbo"

    INPUTS = InputSpec.PROMPT | InputSpec.AUDIO_REF
    UI_SECTIONS = [
        UISection.PROMPT,
        UISection.AUDIO_DURATION,
        UISection.AUDIO_REF,
        UISection.CHAT_PARAMS,
        UISection.SEED,
    ]
    PARAMS = ParamSpec()
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

        workflow_id = WORKFLOW_REF_ID if inputs.audio_ref else WORKFLOW_ID
        phase = "Generating speech with local ComfyUI Chatterbox Turbo"
        if inputs.audio_ref:
            phase = "Generating reference speech with local ComfyUI Chatterbox Turbo"
        if inputs.is_voice_clone and inputs.audio_ref:
            inputs.usage_note = (
                "Chatterbox Turbo uses reference-audio TTS in the pinned Comfy node; "
                "speech-to-speech VC is handled by the standard Chatterbox VC profile."
            )

        self.set_phase(inputs, phase)
        label = inputs.prompt or "chatterbox_turbo"
        filename = solve_path(
            clean_filename(f"{inputs.seed}_{label[:48]}_chatterbox_turbo") + ".flac"
        )
        return gateway.run_comfy_workflow(
            workflow_id,
            inputs,
            scene,
            prefs,
            destination=filename,
        )
