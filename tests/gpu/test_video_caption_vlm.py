from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError
from slopperly.validation.artifacts import ArtifactValidationError, validate_text


LOGICAL_NAME = "vllm_video_caption_vlm"


def test_video_caption_vlm(gpu_cert, plugin_loader, base_models, repo_root, sequence_scene_factory):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "vllm")
    video_path = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "video_caption_smoke.mp4",
        "video-caption MP4 fixture",
    )
    module = plugin_loader("text", "marlin_video_captions")
    plugin = module.MarlinVideoCaptionsPlugin()
    scene = sequence_scene_factory(
        marlin_mode="CAPTION",
        marlin_find_query="",
        marlin_last_query="",
        marlin_speed="FAST",
        frame_end=172,
    )
    inputs = base_models.ModelInputs(
        video_path=str(video_path),
        insert_frame_start=100,
        insert_channel=3,
    )
    prefs = SimpleNamespace(vllm_url=runtime_url, vllm_vlm_model="")

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            plugin.generate(pipe_obj, inputs, scene, prefs)
        captions = "\n".join(strip.text for strip in scene.sequence_editor.created)
        validation = validate_text(
            captions,
            max_chars=20000,
            forbidden_fragments=["provider error", "connection refused"],
        )
    except RuntimeUnavailableError as exc:
        gpu_cert.block(LOGICAL_NAME, f"vLLM VLM plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"vLLM VLM caption validation failed: {exc}")

    artifact = gpu_cert.artifact_path(LOGICAL_NAME, "video_captions.txt")
    artifact.write_text(captions, encoding="utf-8")
    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        artifact,
        validation,
        metadata={"runtime_url": runtime_url, "source_video": str(video_path)},
    )
