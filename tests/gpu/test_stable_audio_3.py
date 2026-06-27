from pathlib import Path
from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_audio


LOGICAL_NAME = "stable_audio_3_medium_base"


def test_stable_audio_3(gpu_cert, plugin_loader, base_models):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))

    module = plugin_loader("audio", "_stable_audio_3")
    plugin = module.StableAudio3Plugin()
    output_dir = gpu_cert.artifact_path(LOGICAL_NAME, "stable_audio_3.flac").parent
    module.solve_path = lambda filename: str(output_dir / filename)

    scene = SimpleNamespace(
        stable_audio_3_sampler="lcm",
        stable_audio_3_scheduler="simple",
        stable_audio_3_denoise=1.0,
    )
    inputs = base_models.ModelInputs(
        prompt="warm lo-fi electric piano chords, soft brushed drums, rounded bass",
        neg_prompt="speech, vocals, clipping, harsh distortion",
        audio_length=2.0,
        steps=8,
        guidance=5.0,
        seed=31415,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            output = plugin.generate(pipe_obj, inputs, scene, prefs)
        validation = validate_audio(
            output,
            expected_duration=2.0,
            duration_tolerance=0.35,
            expected_sample_rate=44100,
            require_non_silent=True,
        )
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"Stable Audio 3 Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"Stable Audio 3 audio validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        Path(output),
        validation,
        metadata={"runtime_url": runtime_url, "output": output},
    )
