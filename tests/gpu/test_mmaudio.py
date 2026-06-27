import subprocess
from pathlib import Path
from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_audio


LOGICAL_NAME = "mmaudio_video_to_audio"


def _write_source_video(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "testsrc2=size=160x96:rate=24:duration=3",
        "-an",
        "-c:v",
        "mpeg4",
        "-q:v",
        "5",
        str(path),
    ]
    subprocess.run(cmd, check=True)


def test_mmaudio(gpu_cert, plugin_loader, base_models):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    module = plugin_loader("audio", "mmaudio")
    plugin = module.MMAudioPlugin()
    output_dir = gpu_cert.artifact_path(LOGICAL_NAME, "mmaudio.wav").parent
    video_path = output_dir / "mmaudio_source_3s.mp4"
    try:
        _write_source_video(video_path)
    except (OSError, subprocess.CalledProcessError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"Could not generate MMAudio source MP4 with ffmpeg: {exc}")
    gpu_cert.require_file(LOGICAL_NAME, video_path, "MMAudio generated source MP4")
    module.solve_path = lambda filename: str(output_dir / filename)

    scene = SimpleNamespace(
        mmaudio_force_offload=True,
        mmaudio_mask_away_clip=False,
    )
    inputs = base_models.ModelInputs(
        prompt="subtle cloth movement, quiet room tone, small mechanical hum",
        neg_prompt="speech, music, distortion, clipping",
        video_path=str(video_path),
        audio_length=1.5,
        steps=8,
        guidance=4.0,
        seed=2468,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            output = plugin.generate(pipe_obj, inputs, scene, prefs)
        validation = validate_audio(
            output,
            expected_duration=1.5,
            duration_tolerance=0.35,
            expected_sample_rate=44100,
            require_non_silent=True,
        )
    except (RuntimeUnavailableError, WorkflowValidationError, ValueError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"MMAudio Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"MMAudio audio validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        Path(output),
        validation,
        metadata={"runtime_url": runtime_url, "source_video": str(video_path), "output": output},
    )
