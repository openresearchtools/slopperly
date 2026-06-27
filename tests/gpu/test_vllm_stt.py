from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError
from slopperly.validation.artifacts import ArtifactValidationError, validate_text


LOGICAL_NAME = "vllm_whisper_large_v3_turbo_stt"


def test_vllm_stt(gpu_cert, plugin_loader, base_models, repo_root, sequence_scene_factory):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "vllm")
    audio_path = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "Voices" / "Reading_Female_Girl_Emma.wav",
        "speech WAV fixture",
    )
    module = plugin_loader("text", "faster_whisper_transcribe")
    plugin = module.FasterWhisperTranscribePlugin()
    scene = sequence_scene_factory(
        whisper_model_size="large-v3-turbo",
        whisper_language="en",
    )
    inputs = base_models.ModelInputs(
        audio_ref=str(audio_path),
        insert_frame_start=100,
        insert_channel=2,
    )
    prefs = type("Prefs", (), {"vllm_url": runtime_url})()

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            plugin.generate(pipe_obj, inputs, scene, prefs)
        transcript = "\n".join(strip.text for strip in scene.sequence_editor.created)
        validation = validate_text(
            transcript,
            max_chars=20000,
            forbidden_fragments=["provider error", "connection refused"],
        )
    except RuntimeUnavailableError as exc:
        gpu_cert.block(LOGICAL_NAME, f"vLLM STT plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"vLLM STT transcript validation failed: {exc}")

    artifact = gpu_cert.artifact_path(LOGICAL_NAME, "transcript.txt")
    artifact.write_text(transcript, encoding="utf-8")
    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        artifact,
        validation,
        metadata={"runtime_url": runtime_url, "source_audio": str(audio_path)},
    )
