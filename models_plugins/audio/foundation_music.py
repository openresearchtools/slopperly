"""Text-to-music via the local Slopperly ComfyUI Foundation-1 workflow."""

import shutil
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

from ...models.base import ModelPlugin, InputSpec, UISection, ParamSpec, ModelInputs
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import solve_path, clean_filename


WORKFLOW_ID = "foundation1_music_loop"
FOUNDATION_BPM_OPTIONS = (100, 110, 120, 128, 130, 140, 150)
FOUNDATION_BARS_OPTIONS = (4, 8)
FOUNDATION_KEYS = (
    "C major", "C# major", "D major", "Eb major", "E major", "F major",
    "F# major", "G major", "Ab major", "A major", "Bb major", "B major",
    "C minor", "C# minor", "D minor", "Eb minor", "E minor", "F minor",
    "F# minor", "G minor", "Ab minor", "A minor", "Bb minor", "B minor",
)


def _duration_for(bpm: int, bars: int) -> int:
    return round(bars * 4 / bpm * 60)


def _coerce_bpm(value, fallback: int) -> int:
    if isinstance(value, str):
        value = value.strip().split(" ", 1)[0]
    try:
        bpm = int(float(value))
    except (TypeError, ValueError):
        return fallback
    return min(FOUNDATION_BPM_OPTIONS, key=lambda option: abs(option - bpm))


def _coerce_bars(value, fallback: int) -> int:
    if isinstance(value, str):
        value = value.strip().split(" ", 1)[0]
    try:
        bars = int(float(value))
    except (TypeError, ValueError):
        return fallback
    return min(FOUNDATION_BARS_OPTIONS, key=lambda option: abs(option - bars))


def _choose_loop(audio_length: float) -> tuple[int, int]:
    target = max(float(audio_length or 10.0), 1.0)
    return min(
        ((bpm, bars) for bpm in FOUNDATION_BPM_OPTIONS for bars in FOUNDATION_BARS_OPTIONS),
        key=lambda pair: abs(_duration_for(pair[0], pair[1]) - target),
    )


def _foundation_tags(prompt: str, negative_prompt: str) -> str:
    prompt = (prompt or "").strip()
    negative_prompt = (negative_prompt or "").strip()
    if not negative_prompt:
        return prompt
    if not prompt:
        return f"avoid {negative_prompt}"
    return f"{prompt}, avoid {negative_prompt}"


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
                "44100",
                str(destination_path),
            ],
            check=True,
        )
        return str(destination_path)
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    try:
        import soundfile as sf

        audio, sample_rate = sf.read(str(source_path), always_2d=True)
        output_rate = 44100 if sample_rate != 44100 else sample_rate
        sf.write(str(destination_path), audio, output_rate)
    except Exception as exc:
        raise RuntimeError(
            f"Foundation-1 generated audio could not be converted to WAV: {source_path}"
        ) from exc
    return str(destination_path)


class FoundationMusicPlugin(ModelPlugin):
    MODEL_ID = "tintwotin/Foundation-1-Diffusers"
    DISPLAY_NAME = "Music: Foundation-1 (Local Comfy)"
    MODEL_TYPE = "audio"
    DESCRIPTION = "Structured loop generation through the local ComfyUI Foundation-1 workflow"

    INPUTS = InputSpec.PROMPT | InputSpec.NEG_PROMPT | InputSpec.MUSIC_PARAMS
    UI_SECTIONS = [
        UISection.PROMPT,
        UISection.NEG_PROMPT,
        UISection.AUDIO_DURATION,
        UISection.MUSIC_PARAMS,
        UISection.STEPS,
        UISection.SEED,
    ]
    PARAMS = ParamSpec(steps=100, audio_length=10.0)
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

        self.set_phase(inputs, "Generating audio with local ComfyUI Foundation-1")
        filename = solve_path(
            clean_filename(f"{inputs.seed}_{inputs.prompt[:30]}_foundation1") + ".wav"
        )
        comfy_destination = str(Path(filename).with_suffix(".flac"))

        chosen_bpm, chosen_bars = _choose_loop(inputs.audio_length)
        scene_bpm = getattr(scene, "foundation1_bpm", None)
        scene_bars = getattr(scene, "foundation1_bars", None)
        scene_key = getattr(scene, "foundation1_key", None)
        input_bpm = getattr(inputs, "bpm", 0) or None
        input_key = getattr(inputs, "key_scale", "") or None

        bpm = _coerce_bpm(scene_bpm if scene_bpm is not None else input_bpm, chosen_bpm)
        bars = _coerce_bars(scene_bars, chosen_bars)
        key = (scene_key or input_key or "C major").strip()
        if key not in FOUNDATION_KEYS:
            key = "C major"

        workflow_inputs = SimpleNamespace(**vars(inputs))
        workflow_inputs.prompt = _foundation_tags(inputs.prompt, inputs.neg_prompt)
        workflow_inputs.foundation1_bpm = f"{bpm} BPM"
        workflow_inputs.foundation1_bars = f"{bars} Bars"
        workflow_inputs.foundation1_key = key
        workflow_inputs.foundation1_filename_prefix = (
            f"slopperly_foundation1_{inputs.seed}_{time.time_ns()}"
        )

        comfy_output = gateway.run_comfy_workflow(
            WORKFLOW_ID,
            workflow_inputs,
            scene,
            prefs,
            destination=comfy_destination,
        )
        return _write_wav(comfy_output, filename)
