"""MOSS-TTS through local vLLM-Omni."""

from ...models.base import InputSpec, ModelInputs, ModelPlugin, ParamSpec, UISection
from ...utils.helpers import clean_filename, solve_path
from ...slopperly.runtime.vllm_omni.tts_client import VllmOmniTtsClient

_VARIANT_REPOS = {
    "nano": "OpenMOSS-Team/MOSS-TTS-Nano",
}
_DEFAULT_VARIANT = "nano"


class MossTTSPlugin(ModelPlugin):
    MODEL_ID = "MOSS-TTS"
    DISPLAY_NAME = "TTS: MOSS-TTS"
    MODEL_TYPE = "audio"
    DESCRIPTION = "MOSS-TTS through local vLLM-Omni"

    INPUTS = InputSpec.PROMPT
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
        ref_audio = (getattr(scene, "moss_ref_audio_path", "") or "").strip() or None
        language = getattr(scene, "moss_language", "AUTO")
        duration_tokens = int(getattr(scene, "moss_duration_tokens", 0))
        max_new_tokens = int(getattr(scene, "moss_max_new_tokens", 4096))
        temperature = float(getattr(scene, "moss_temperature", 1.7))
        top_p = float(getattr(scene, "moss_top_p", 0.8))
        top_k = int(getattr(scene, "moss_top_k", 25))
        instructions = (
            f"language={language}; duration_tokens={duration_tokens}; "
            f"max_new_tokens={max_new_tokens}; temperature={temperature}; "
            f"top_p={top_p}; top_k={top_k}"
        )

        output_path = solve_path(clean_filename(str(inputs.seed) + "_" + inputs.prompt) + ".wav")
        self.set_phase(inputs, "Generating with vLLM-Omni")
        return VllmOmniTtsClient.from_preferences(prefs).speech(
            text=inputs.prompt,
            output_path=output_path,
            model=model,
            voice="default",
            ref_audio=ref_audio,
            instructions=instructions,
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
