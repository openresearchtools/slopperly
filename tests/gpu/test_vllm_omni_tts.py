from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError
from slopperly.validation.artifacts import ArtifactValidationError, validate_audio


LOGICAL_NAME = "omnivoice_vllm_omni"


def test_vllm_omni_tts(gpu_cert, plugin_loader, base_models):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "vllm_omni")
    module = plugin_loader("audio", "omnivoice")
    plugin = module.OmniVoicePlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, "omnivoice.wav")
    module.solve_path = lambda filename: str(output_path)
    scene = SimpleNamespace(omnivoice_instruct="clear warm narrator", omnivoice_language="EN")
    inputs = base_models.ModelInputs(
        prompt="This is a local Slopperly voice generation test.",
        speed=1.0,
        seed=31415,
    )
    prefs = SimpleNamespace(vllm_omni_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, scene, prefs)
        validation = validate_audio(result_path, require_non_silent=True)
    except RuntimeUnavailableError as exc:
        gpu_cert.block(LOGICAL_NAME, f"vLLM-Omni TTS plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"vLLM-Omni TTS artifact validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        output_path,
        validation,
        metadata={"runtime_url": runtime_url, "model": "k2-fsa/OmniVoice"},
    )
