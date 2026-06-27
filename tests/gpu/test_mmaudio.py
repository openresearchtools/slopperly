from pathlib import Path
from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_audio


LOGICAL_NAME = "mmaudio_video_to_audio"


def test_mmaudio(gpu_cert, plugin_loader, base_models, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    video_path = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "video_vsr_source.mp4",
        "MMAudio source MP4 fixture",
    )

    module = plugin_loader("audio", "mmaudio")
    plugin = module.MMAudioPlugin()
    output_dir = gpu_cert.artifact_path(LOGICAL_NAME, "mmaudio.flac").parent
    module.solve_path = lambda filename: str(output_dir / filename)

    scene = SimpleNamespace(
        mmaudio_force_offload=True,
        mmaudio_mask_away_clip=False,
    )
    inputs = base_models.ModelInputs(
        prompt="subtle cloth movement, quiet room tone, small mechanical hum",
        neg_prompt="speech, music, distortion, clipping",
        video_path=str(video_path),
        audio_length=1.0,
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
            expected_duration=1.0,
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
