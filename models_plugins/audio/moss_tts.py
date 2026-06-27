"""MOSS-TTS through local vLLM-Omni."""

from ...models.base import InputSpec, ModelInputs, ModelPlugin, ParamSpec, UISection
from ...slopperly.runtime.errors import RuntimeUnavailableError
from ...slopperly.runtime.vllm_omni.tts_client import VllmOmniTtsClient
from ...utils.helpers import clean_filename, solve_path

_VARIANT_REPOS = {
    "nano": "OpenMOSS-Team/MOSS-TTS-Nano",
}
_DEFAULT_VARIANT = "nano"
_LANGUAGE_NAMES = {
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
    return _LANGUAGE_NAMES.get(raw.upper(), raw or None)


def _positive_int(value, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _served_model_id(client: VllmOmniTtsClient, requested_model: str) -> str:
    try:
        models = client.health().get("data", [])
    except RuntimeUnavailableError:
        return requested_model
    served_ids = [str(item.get("id")) for item in models if item.get("id")]
    if requested_model in served_ids:
        return requested_model
    if len(served_ids) == 1:
        return served_ids[0]
    return requested_model


class MossTTSPlugin(ModelPlugin):
    MODEL_ID = "MOSS-TTS"
    DISPLAY_NAME = "TTS: MOSS-TTS"
    MODEL_TYPE = "audio"
    DESCRIPTION = "MOSS-TTS through local vLLM-Omni"

    INPUTS = InputSpec.PROMPT | InputSpec.AUDIO_REF
    UI_SECTIONS = [
        UISection.PROMPT,
        UISection.SEED,
    ]
    PARAMS = ParamSpec()
    REQUIRED_PACKAGES = []
    runtime_profile = "moss_tts_nano_vllm_omni"

    @staticmethod
    def _variant_of(scene) -> str:
        variant = getattr(scene, "moss_model_variant", _DEFAULT_VARIANT)
        return variant if variant in _VARIANT_REPOS else _DEFAULT_VARIANT

    def load(self, prefs, scene, **kw):
        return {"pipe": None, "last_model_card": self.MODEL_ID}

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs) -> str:
        variant = self._variant_of(scene)
        model = _VARIANT_REPOS[variant]
        scene_ref_audio = (getattr(scene, "moss_ref_audio_path", "") or "").strip() or None
        ref_audio = inputs.audio_ref or scene_ref_audio
        if not ref_audio:
            raise RuntimeUnavailableError(
                "MOSS-TTS-Nano requires a local speaker reference audio file for voice cloning."
            )

        language = _language_name(getattr(scene, "moss_language", "AUTO"))
        duration_tokens = _positive_int(getattr(scene, "moss_duration_tokens", 0), 0)
        max_new_tokens = _positive_int(getattr(scene, "moss_max_new_tokens", 4096), 4096)
        effective_max_new_tokens = duration_tokens or max_new_tokens
        temperature = float(getattr(scene, "moss_temperature", 1.7))
        top_p = float(getattr(scene, "moss_top_p", 0.8))
        top_k = int(getattr(scene, "moss_top_k", 25))
        extra_params = {
            "max_new_frames": int(effective_max_new_tokens),
            "text_temperature": temperature,
            "text_top_p": top_p,
            "text_top_k": top_k,
            "audio_temperature": temperature,
            "audio_top_p": top_p,
            "audio_top_k": top_k,
        }

        output_path = solve_path(clean_filename(str(inputs.seed) + "_" + inputs.prompt) + ".wav")
        self.set_phase(inputs, "Generating with vLLM-Omni")
        client = VllmOmniTtsClient.from_preferences(prefs)
        return client.speech(
            text=inputs.prompt,
            output_path=output_path,
            model=_served_model_id(client, model),
            ref_audio=ref_audio,
            language=language,
            seed=inputs.seed,
            max_new_tokens=int(effective_max_new_tokens),
            extra_params=extra_params,
        )

    def draw_custom_ui(self, col, context) -> bool:
        scene = context.scene
        col.prop(scene, "moss_model_variant")
        col.prop(scene, "moss_language")
        col.separator()
        if self._variant_of(scene) != "voicegen":
            row = col.row(align=True)
            row.prop(scene, "moss_ref_audio_path", text="Speaker Ref.")
            row.operator(
                "sequencer.open_audio_filebrowser", text="", icon="FILEBROWSER",
            ).target_prop = "moss_ref_audio_path"
            col.separator()
        col.prop(scene, "moss_duration_tokens")
        col.prop(scene, "moss_max_new_tokens")
        col.separator()
        col.prop(scene, "moss_temperature")
        col.prop(scene, "moss_top_p")
        col.prop(scene, "moss_top_k")
        return False
