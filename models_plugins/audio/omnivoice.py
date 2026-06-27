"""Zero-shot multilingual TTS via local vLLM-Omni OmniVoice."""

from ...models.base import InputSpec, ModelInputs, ModelPlugin, ParamSpec, UISection
from ...utils.helpers import clean_filename, solve_path
from ...slopperly.runtime.vllm_omni.tts_client import VllmOmniTtsClient

_LANGUAGE_FALLBACKS = {
    "AUTO": None,
    "": None,
    "EN": "English",
    "ZH": "Chinese",
    "JA": "Japanese",
    "KO": "Korean",
    "ES": "Spanish",
    "FR": "French",
    "DE": "German",
    "IT": "Italian",
    "PT": "Portuguese",
    "RU": "Russian",
}


def _language_name(value: str | None) -> str | None:
    raw = (value or "AUTO").strip()
    upper = raw.upper()
    if upper in _LANGUAGE_FALLBACKS:
        return _LANGUAGE_FALLBACKS[upper]
    try:
        from ...utils.omnivoice_langs import OMNIVOICE_LANG_ITEMS

        for item in OMNIVOICE_LANG_ITEMS:
            if item and item[0] == raw:
                return item[1]
    except Exception:
        pass
    return raw or None


class OmniVoicePlugin(ModelPlugin):
    MODEL_ID = "OmniVoice"
    DISPLAY_NAME = "TTS: OmniVoice"
    MODEL_TYPE = "audio"
    DESCRIPTION = "Zero-shot TTS through local vLLM-Omni using k2-fsa/OmniVoice"

    INPUTS = InputSpec.PROMPT | InputSpec.AUDIO_REF | InputSpec.TEXT_REF
    UI_SECTIONS = [
        UISection.PROMPT,
        UISection.SPEED,
        UISection.STEPS,
        UISection.GUIDANCE,
        UISection.SEED,
    ]
    PARAMS = ParamSpec(steps=32, guidance=2.0)
    REQUIRED_PACKAGES = []
    runtime_profile = "omnivoice_vllm_omni"

    def load(self, prefs, scene, **kw):
        return {"pipe": None, "last_model_card": self.MODEL_ID}

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs) -> str:
        instruct = getattr(scene, "omnivoice_instruct", "").strip() or None
        language = _language_name(getattr(scene, "omnivoice_language", "AUTO"))
        ref_audio = inputs.audio_ref or getattr(scene, "ref_audio_path", "") or None
        ref_text = (inputs.text_ref or getattr(scene, "ref_text", "") or "").strip() or None
        speed = inputs.speed if inputs.speed != 1.0 else None
        instructions = instruct
        extra_params = {
            "num_step": int(inputs.steps),
            "guidance_scale": float(inputs.guidance),
        }

        output_path = solve_path(clean_filename(str(inputs.seed) + "_" + inputs.prompt) + ".wav")
        self.set_phase(inputs, "Generating with vLLM-Omni")
        return VllmOmniTtsClient.from_preferences(prefs).speech(
            text=inputs.prompt,
            output_path=output_path,
            model="k2-fsa/OmniVoice",
            ref_audio=ref_audio,
            ref_text=ref_text,
            speed=speed,
            instructions=instructions,
            language=language,
            seed=inputs.seed,
            extra_params=extra_params,
        )

    def draw_custom_ui(self, col, context) -> bool:
        scene = context.scene
        col.prop(scene, "omnivoice_language")
        col.separator()
        row = col.row(align=True)
        row.prop(scene, "ref_audio_path", text="Speaker Ref.")
        row.operator("sequencer.open_audio_filebrowser", text="", icon="FILEBROWSER")
        col.prop(scene, "ref_text", text="Ref. Text")
        col.prop(scene, "omnivoice_preprocess")
        col.separator()
        col.prop(scene, "omnivoice_instruct")
        col.separator()
        col.prop(scene, "omnivoice_denoise")
        col.prop(scene, "omnivoice_postprocess")
        return False
