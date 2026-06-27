from pathlib import Path
from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_audio


LOGICAL_NAME = "ace_step_15_music"


def test_ace_step(gpu_cert, plugin_loader, base_models):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))

    module = plugin_loader("audio", "ace_step")
    plugin = module.AceStepPlugin()
    output_dir = gpu_cert.artifact_path(LOGICAL_NAME, "ace_step.flac").parent
    module.solve_path = lambda filename: str(output_dir / filename)

    scene = SimpleNamespace(
        ace_step_language="en",
        ace_step_sampler="euler",
        ace_step_scheduler="simple",
        ace_step_denoise=1.0,
        ace_step_aura_shift=3.0,
    )
    inputs = base_models.ModelInputs(
        prompt="bright indie pop loop, clean guitar, warm bass, soft drums",
        lyrics="[verse]\nMorning light on the window\n[chorus]\nWe keep moving with the sunrise",
        audio_length=2.0,
        steps=8,
        guidance=3.5,
        seed=24680,
        bpm=96,
        key_scale="C major",
        time_signature="4",
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            output = plugin.generate(pipe_obj, inputs, scene, prefs)
        validation = validate_audio(
            output,
            expected_duration=2.0,
            duration_tolerance=0.5,
            expected_sample_rate=48000,
            require_non_silent=True,
        )
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"ACE-Step Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"ACE-Step audio validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        Path(output),
        validation,
        metadata={"runtime_url": runtime_url, "output": output},
    )
