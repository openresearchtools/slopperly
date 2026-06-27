from types import SimpleNamespace
import json

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError
from slopperly.validation.artifacts import ArtifactValidationError, validate_audio


LOGICAL_NAME = "omnivoice_vllm_omni"


def test_vllm_omni_tts(gpu_cert, plugin_loader, base_models):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "vllm_omni")
    module = plugin_loader("audio", "omnivoice")
    plugin = module.OmniVoicePlugin()
    plain_output = gpu_cert.artifact_path(LOGICAL_NAME, "omnivoice_plain.wav")
    clone_output = gpu_cert.artifact_path(LOGICAL_NAME, "omnivoice_clone.wav")
    generated_outputs = [plain_output, clone_output]

    def _solve_path(_filename: str) -> str:
        return str(generated_outputs.pop(0))

    module.solve_path = _solve_path
    scene = SimpleNamespace(omnivoice_instruct="clear warm narrator", omnivoice_language="EN")
    plain_inputs = base_models.ModelInputs(
        prompt="This is a local Slopperly voice generation test.",
        speed=1.0,
        seed=31415,
    )
    prefs = SimpleNamespace(vllm_omni_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            plain_result = plugin.generate(pipe_obj, plain_inputs, scene, prefs)
        plain_validation = validate_audio(plain_result, require_non_silent=True)

        clone_inputs = base_models.ModelInputs(
            prompt="This second sentence uses the first local OmniVoice sample as a reference voice.",
            audio_ref=plain_result,
            text_ref=plain_inputs.prompt,
            speed=1.0,
            seed=31416,
        )
        with local_only_network():
            clone_result = plugin.generate(pipe_obj, clone_inputs, scene, prefs)
        clone_validation = validate_audio(clone_result, require_non_silent=True)
    except RuntimeUnavailableError as exc:
        gpu_cert.block(LOGICAL_NAME, f"vLLM-Omni TTS plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"vLLM-Omni TTS artifact validation failed: {exc}")

    manifest_path = gpu_cert.artifact_path(LOGICAL_NAME, "omnivoice_manifest.json")
    manifest_path.write_text(
        json.dumps(
            {
                "runtime_url": runtime_url,
                "model": "k2-fsa/OmniVoice",
                "plain": {"path": plain_result, "validation": plain_validation},
                "clone": {
                    "path": clone_result,
                    "reference": plain_result,
                    "ref_text": plain_inputs.prompt,
                    "validation": clone_validation,
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        manifest_path,
        {"plain": plain_validation, "clone": clone_validation},
        metadata={"runtime_url": runtime_url, "model": "k2-fsa/OmniVoice"},
    )
