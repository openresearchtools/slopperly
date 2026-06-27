"""Multilingual TTS via local Slopperly ComfyUI Chatterbox workflows."""

import shutil
import subprocess
import time
from pathlib import Path
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


def _is_wav(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(4) == b"RIFF"
    except OSError:
        return False


def _write_wav(source: str, destination: str) -> str:
    source_path = Path(source)
    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)

    if source_path.resolve() == destination_path.resolve():
        return str(destination_path)

    if _is_wav(source_path):
        shutil.copyfile(source_path, destination_path)
        return str(destination_path)

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(source_path),
                "-ar",
                "24000",
                str(destination_path),
            ],
            check=True,
        )
        return str(destination_path)
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    try:
        import soundfile as sf

        audio, _sample_rate = sf.read(str(source_path), always_2d=True)
        sf.write(str(destination_path), audio, 24000)
    except Exception as exc:
        raise RuntimeError(
            f"Chatterbox Multilingual generated audio could not be converted to WAV: {source_path}"
        ) from exc
    return str(destination_path)


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
        workflow_id = WORKFLOW_REF_ID if inputs.audio_ref else WORKFLOW_ID
        phase = "Generating multilingual speech with local ComfyUI Chatterbox"
        if inputs.audio_ref:
            phase = "Generating multilingual reference speech with local ComfyUI Chatterbox"
        if inputs.is_voice_clone and inputs.audio_ref:
            inputs.usage_note = (
                "Chatterbox Multilingual uses reference-audio TTS in the pinned Comfy node; "
                "speech-to-speech VC is handled by the standard Chatterbox VC profile."
            )

        self.set_phase(inputs, phase)
        label = inputs.prompt or "chatterbox_multilingual"
        filename = solve_path(
            clean_filename(f"{inputs.seed}_{language}_{label[:48]}_chatterbox_mtl") + ".wav"
        )
        comfy_destination = str(Path(filename).with_suffix(".flac"))
        workflow_inputs = SimpleNamespace(**vars(inputs))
        workflow_inputs.chatterbox_mtl_language = language
        workflow_inputs.chatterbox_multilingual_filename_prefix = (
            f"slopperly_chatterbox_multilingual_{inputs.seed}_{time.time_ns()}"
        )
        comfy_output = gateway.run_comfy_workflow(
            workflow_id,
            workflow_inputs,
            scene,
            prefs,
            destination=comfy_destination,
        )
        return _write_wav(comfy_output, filename)

    def draw_custom_ui(self, col, context) -> bool:
        scene = context.scene
        col.prop(scene, "chatterbox_mtl_language")
        return False
