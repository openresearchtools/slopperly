"""Zero-shot multilingual TTS via local vLLM-Omni OmniVoice."""

from ...models.base import InputSpec, ModelInputs, ModelPlugin, ParamSpec, UISection
from ...utils.helpers import clean_filename, solve_path
from ...slopperly.runtime.vllm_omni.tts_client import VllmOmniTtsClient


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
        language = getattr(scene, "omnivoice_language", "AUTO")
        ref_audio = inputs.audio_ref or None
        ref_text = (inputs.text_ref or "").strip() or None
        speed = inputs.speed if inputs.speed != 1.0 else None
        lang_note = "" if language == "AUTO" else f"Language: {language}."
        instructions = " ".join(x for x in (lang_note, instruct or "") if x).strip() or None

        output_path = solve_path(clean_filename(str(inputs.seed) + "_" + inputs.prompt) + ".wav")
        self.set_phase(inputs, "Generating with vLLM-Omni")
        return VllmOmniTtsClient.from_preferences(prefs).speech(
            text=inputs.prompt,
            output_path=output_path,
            model="k2-fsa/OmniVoice",
            voice="default",
            ref_audio=ref_audio,
            ref_text=ref_text,
            speed=speed,
            instructions=instructions,
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
