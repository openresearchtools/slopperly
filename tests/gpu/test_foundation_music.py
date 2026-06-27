from pathlib import Path
from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_audio


LOGICAL_NAME = "foundation1_music_loop"


def test_foundation_music(gpu_cert, plugin_loader, base_models):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))

    module = plugin_loader("audio", "foundation_music")
    plugin = module.FoundationMusicPlugin()
    output_dir = gpu_cert.artifact_path(LOGICAL_NAME, "foundation1.flac").parent
    module.solve_path = lambda filename: str(output_dir / filename)

    scene = SimpleNamespace(
        foundation1_bpm="100 BPM",
        foundation1_bars="4 Bars",
        foundation1_key="C minor",
        foundation1_cfg_scale=7.0,
        foundation1_sampler_type="dpmpp-3m-sde",
    )
    inputs = base_models.ModelInputs(
        prompt="warm analog bass, clipped house drums, bright plucked synth, clean loop",
        neg_prompt="speech, vocals, clipping",
        audio_length=10.0,
        steps=20,
        seed=424242,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            output = plugin.generate(pipe_obj, inputs, scene, prefs)
        validation = validate_audio(
            output,
            expected_duration=10.0,
            duration_tolerance=0.5,
            expected_sample_rate=44100,
            require_non_silent=True,
        )
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"Foundation-1 Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"Foundation-1 audio validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        Path(output),
        validation,
        metadata={"runtime_url": runtime_url, "output": output},
    )
