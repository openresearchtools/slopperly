from pathlib import Path
from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_audio


LOGICAL_NAME = "chatterbox_turbo_tts_comfy"


def test_chatterbox_turbo(gpu_cert, plugin_loader, base_models):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))

    module = plugin_loader("audio", "chatterbox_turbo")
    plugin = module.ChatterboxTurboPlugin()
    output_dir = gpu_cert.artifact_path(LOGICAL_NAME, "chatterbox_turbo.flac").parent
    module.solve_path = lambda filename: str(output_dir / filename)

    scene = SimpleNamespace(
        chatterbox_turbo_top_k=1000,
        chatterbox_turbo_top_p=0.95,
        chatterbox_turbo_repetition_penalty=1.2,
    )
    inputs = base_models.ModelInputs(
        prompt="A quick local Chatterbox Turbo voice confirms the Slopperly workflow is running.",
        audio_length=2.0,
        temperature=0.8,
        seed=9191,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            output = plugin.generate(pipe_obj, inputs, scene, prefs)
        validation = validate_audio(
            output,
            expected_sample_rate=24000,
            require_non_silent=True,
        )
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"Chatterbox Turbo Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"Chatterbox Turbo audio validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        Path(output),
        validation,
        metadata={"runtime_url": runtime_url, "output": output},
    )
