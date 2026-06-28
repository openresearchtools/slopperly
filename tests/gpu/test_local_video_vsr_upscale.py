from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_video


LOGICAL_NAME = "local_video_vsr_upscale"


def test_local_video_vsr_upscale(gpu_cert, plugin_loader, base_models, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    video_path = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "video_vsr_source.mp4",
        "local video VSR MP4 fixture with audio",
    )

    module = plugin_loader("video", "maxine_vsr_video")
    plugin = module.MaxineVSRVideoPlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, "local_video_vsr.mp4")
    module.solve_path = lambda filename: str(output_path)

    scene = SimpleNamespace()
    inputs = base_models.ModelInputs(
        video_path=str(video_path),
        width=32,
        height=24,
        fps=12.0,
        seed=123,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, scene, prefs)
        validation = validate_video(
            result_path,
            expected_width=32,
            expected_height=24,
            expected_fps=12.0,
            expected_duration=1.0,
            duration_tolerance=0.12,
            require_audio=True,
        )
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"Local video VSR Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"Local video VSR MP4 validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        output_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "source_video": str(video_path),
            "workflow_pack": "local_video_vsr_upscale",
            "model_files": {"upscale_model": "RealESRGAN_x4.pth"},
            "video_format": "video/h264-mp4",
            "pix_fmt": "yuv420p",
            "crf": 19,
            "audio_passthrough": True,
        },
    )
