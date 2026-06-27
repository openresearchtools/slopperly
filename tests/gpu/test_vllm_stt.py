from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError
from slopperly.validation.artifacts import ArtifactValidationError, validate_audio, validate_text


LOGICAL_NAME = "vllm_whisper_large_v3_turbo_stt"


def test_vllm_stt(gpu_cert, plugin_loader, base_models, repo_root, sequence_scene_factory):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "vllm")
    audio_path = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "vllm_stt_hello_local_world.wav",
        "known speech WAV fixture",
    )
    audio_validation = validate_audio(
        str(audio_path),
        expected_sample_rate=16000,
        require_non_silent=True,
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
        transcript_lower = transcript.lower()
        expected_words = ["hello", "local", "world", "whisper", "test"]
        missing = [word for word in expected_words if word not in transcript_lower]
        if missing:
            raise ArtifactValidationError(
                f"transcript missing expected words {missing}: {transcript!r}"
            )
        validation["expected_words"] = expected_words
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
        metadata={
            "runtime_url": runtime_url,
            "source_audio": str(audio_path),
            "source_audio_validation": audio_validation,
        },
    )
