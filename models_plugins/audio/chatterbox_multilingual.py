"""Multilingual TTS via local Slopperly ComfyUI Chatterbox workflows."""

from types import SimpleNamespace

from ...models.base import ModelPlugin, InputSpec, UISection, ParamSpec, ModelInputs
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import solve_path, clean_filename


WORKFLOW_ID = "chatterbox_multilingual_tts_comfy"
WORKFLOW_REF_ID = "chatterbox_multilingual_ref_tts_comfy"

LANGUAGE_NAMES = {
    "ar": "Arabic",
    "da": "Danish",
    "de": "German",
    "el": "Greek",
    "en": "English",
    "es": "Spanish",
    "fi": "Finnish",
    "fr": "French",
    "he": "Hebrew",
    "hi": "Hindi",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "ms": "Malay",
    "nl": "Dutch",
    "no": "Norwegian",
    "pl": "Polish",
    "pt": "Portuguese",
    "ru": "Russian",
    "sv": "Swedish",
    "sw": "Swahili",
    "tr": "Turkish",
    "zh": "Chinese",
}


def _comfy_language(value: str) -> str:
    text = (value or "en").strip()
    if "(" in text and text.endswith(")"):
        return text
    code = text.lower()
    name = LANGUAGE_NAMES.get(code, "English")
    code = code if code in LANGUAGE_NAMES else "en"
    return f"{name} ({code})"


class ChatterboxMultilingualPlugin(ModelPlugin):
    MODEL_ID = "ChatterboxMultilingual"
    DISPLAY_NAME = "TTS/VC: Chatterbox Multilingual"
    MODEL_TYPE = "audio"
    DESCRIPTION = "Multilingual text-to-speech via local ComfyUI Chatterbox"

    INPUTS = InputSpec.PROMPT | InputSpec.AUDIO_REF
    UI_SECTIONS = [
        UISection.PROMPT,
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

        language = _comfy_language(getattr(scene, "chatterbox_mtl_language", "en"))
        workflow_inputs = SimpleNamespace(**vars(inputs))
        workflow_inputs.chatterbox_mtl_language = language

        workflow_id = WORKFLOW_REF_ID if inputs.audio_ref else WORKFLOW_ID
        phase = "Generating multilingual speech with local ComfyUI Chatterbox"
        if inputs.audio_ref:
            phase = "Generating multilingual reference speech with local ComfyUI Chatterbox"
        if inputs.is_voice_clone and inputs.audio_ref:
            inputs.usage_note = (
                "Chatterbox Multilingual uses reference-audio TTS in the pinned Comfy node; "
                "speech-to-speech VC is handled by the standard Chatterbox VC profile."
            )
            workflow_inputs.usage_note = inputs.usage_note

        self.set_phase(inputs, phase)
        filename = solve_path(
            clean_filename(f"{inputs.seed}_{language}_{inputs.prompt[:40]}_chatterbox_mtl") + ".flac"
        )
        return gateway.run_comfy_workflow(
            workflow_id,
            workflow_inputs,
            scene,
            prefs,
            destination=filename,
        )

    def draw_custom_ui(self, col, context) -> bool:
        scene = context.scene
        col.prop(scene, "chatterbox_mtl_language")
        return False
