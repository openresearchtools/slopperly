"""Video-to-audio via the local Slopperly ComfyUI MMAudio workflow."""

import shutil
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

from ...models.base import ModelPlugin, InputSpec, UISection, ParamSpec, ModelInputs
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import solve_path, clean_filename


WORKFLOW_ID = "mmaudio_video_to_audio"


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
        sf.write(str(destination_path), audio, sample_rate)
    except Exception as exc:
        raise RuntimeError(
            f"MMAudio generated audio could not be converted to WAV: {source_path}"
        ) from exc
    return str(destination_path)


class MMAudioPlugin(ModelPlugin):
    MODEL_ID = "MMAudio"
    DISPLAY_NAME = "Video to Audio: MMAudio (Local Comfy)"
    MODEL_TYPE = "audio"
    DESCRIPTION = "Generate audio for video clips through the local ComfyUI MMAudio workflow"

    INPUTS = InputSpec.PROMPT | InputSpec.NEG_PROMPT | InputSpec.VIDEO
    UI_SECTIONS = [
        UISection.PROMPT,
        UISection.NEG_PROMPT,
        UISection.VIDEO_STRIP,
        UISection.AUDIO_DURATION,
        UISection.STEPS,
        UISection.GUIDANCE,
        UISection.SEED,
    ]
    PARAMS = ParamSpec(steps=25, guidance=4.5, audio_length=8.0)
    REQUIRED_PACKAGES = []

    def load(self, prefs, scene, **kw):
        return {
            "gateway": SlopperlyRuntimeGateway(),
            "last_model_card": self.MODEL_ID,
        }

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs) -> str:
        if not inputs.video_path or not Path(inputs.video_path).is_file():
            raise ValueError(
                "MMAudio local Comfy workflow requires a selected video strip. "
                "The former image-only and text-only branches remain hidden until "
                "committed local workflow packs pass artifact tests."
            )

        gateway = (pipe_obj or {}).get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        self.set_phase(inputs, "Generating audio with local ComfyUI MMAudio")
        filename = solve_path(
            clean_filename(f"{inputs.seed}_{inputs.prompt}_mmaudio") + ".wav"
        )
        comfy_destination = str(Path(filename).with_suffix(".flac"))
        workflow_inputs = SimpleNamespace(**vars(inputs))
        workflow_inputs.mmaudio_filename_prefix = (
            f"slopperly_mmaudio_{inputs.seed}_{time.time_ns()}"
        )
        comfy_output = gateway.run_comfy_workflow(
            WORKFLOW_ID,
            workflow_inputs,
            scene,
            prefs,
            destination=comfy_destination,
        )
        return _write_wav(comfy_output, filename)
