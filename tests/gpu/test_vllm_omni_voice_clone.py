from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError
from slopperly.validation.artifacts import ArtifactValidationError, validate_audio


LOGICAL_NAME = "moss_tts_nano_vllm_omni"


def test_vllm_omni_voice_clone(gpu_cert, plugin_loader, base_models, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "vllm_omni")
    ref_audio = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "Voices" / "Reading_Female_Girl_Emma.wav",
        "voice-clone reference WAV",
    )
    module = plugin_loader("audio", "moss_tts")
    plugin = module.MossTTSPlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, "moss_tts_nano.wav")
    module.solve_path = lambda filename: str(output_path)
    scene = SimpleNamespace(
        moss_model_variant="nano",
        moss_ref_audio_path=str(ref_audio),
        moss_language="EN",
        moss_duration_tokens=128,
        moss_max_new_tokens=1024,
        moss_temperature=1.1,
        moss_top_p=0.8,
        moss_top_k=25,
    )
    inputs = base_models.ModelInputs(
        prompt="This local voice clone test should produce a short spoken sentence.",
        seed=27182,
    )
    prefs = SimpleNamespace(vllm_omni_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, scene, prefs)
        validation = validate_audio(result_path, require_non_silent=True)
    except RuntimeUnavailableError as exc:
        gpu_cert.block(LOGICAL_NAME, f"vLLM-Omni voice-clone plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"vLLM-Omni voice-clone artifact validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        output_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "model": "OpenMOSS-Team/MOSS-TTS-Nano",
            "reference_audio": str(ref_audio),
        },
    )
