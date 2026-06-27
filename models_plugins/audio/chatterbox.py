"""TTS and voice cloning via local Slopperly ComfyUI Chatterbox workflows."""

from ...models.base import ModelPlugin, InputSpec, UISection, ParamSpec, ModelInputs
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import solve_path, clean_filename


WORKFLOW_ID = "chatterbox_tts_comfy"
WORKFLOW_REF_ID = "chatterbox_tts_vc_comfy"
WORKFLOW_VC_ID = "chatterbox_vc_comfy"


class ChatterboxPlugin(ModelPlugin):
    MODEL_ID = "Chatterbox"
    DISPLAY_NAME = "TTS/VC: Chatterbox"
    MODEL_TYPE = "audio"
    DESCRIPTION = "Text-to-speech and voice cloning via local ComfyUI Chatterbox"

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

        workflow_id = WORKFLOW_ID
        phase = "Generating speech with local ComfyUI Chatterbox"
        if inputs.audio_ref:
            workflow_id = WORKFLOW_REF_ID
            phase = "Generating reference speech with local ComfyUI Chatterbox"
        if inputs.is_voice_clone and inputs.audio_ref:
            workflow_id = WORKFLOW_VC_ID
            phase = "Converting voice with local ComfyUI Chatterbox"
            inputs.usage_note = (
                "Chatterbox VC used the legacy single audio picker for both source "
                "and target voice; cross-speaker VC needs a future second target selector."
            )

        self.set_phase(inputs, phase)
        label = inputs.prompt or "chatterbox_voice_clone"
        filename = solve_path(
            clean_filename(f"{inputs.seed}_{label[:48]}_chatterbox") + ".flac"
        )
        return gateway.run_comfy_workflow(
            workflow_id,
            inputs,
            scene,
            prefs,
            destination=filename,
        )
