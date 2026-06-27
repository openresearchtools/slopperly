from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_video


LOGICAL_NAME = "wan22_ti2v_5b_720p24_gguf"
WORKFLOW_ID = "wan22_ti2v_5b_720p24_gguf"


def test_wan22_ti2v_5b_t2v_720p24(gpu_cert, plugin_loader, base_models, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    workflow_pack = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "slopperly" / "workflows" / "comfy" / WORKFLOW_ID / "workflow.api.json",
        "Wan2.2 TI2V-5B Q5 GGUF Comfy workflow API graph",
    )

    module = plugin_loader("video", "wan_ti2v_5b")
    plugin = module.WanTI2V5BPlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, "wan22_ti2v_5b_t2v.mp4")
    module.solve_path = lambda filename: str(output_path)

    inputs = base_models.ModelInputs(
        prompt="a short local 24fps shot of a brass robot pouring tea in a workshop",
        neg_prompt="text, watermark, low quality",
        width=1280,
        height=704,
        frames=49,
        fps=24,
        steps=25,
        guidance=5.0,
        seed=220502,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, SimpleNamespace())
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, SimpleNamespace(), prefs)
        validation = validate_video(
            result_path,
            expected_width=1280,
            expected_height=704,
            expected_fps=24.0,
            expected_duration=49 / 24,
            duration_tolerance=0.25,
            require_audio=False,
        )
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"Wan2.2 TI2V-5B T2V Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"Wan2.2 TI2V-5B T2V MP4 validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        output_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "workflow_pack": str(workflow_pack),
            "mode": "t2v",
            "plugin": "video/wan_ti2v_5b.py",
        },
    )


def test_wan22_ti2v_5b_i2v_720p24(gpu_cert, plugin_loader, base_models, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    workflow_pack = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "slopperly" / "workflows" / "comfy" / WORKFLOW_ID / "workflow.api.json",
        "Wan2.2 TI2V-5B Q5 GGUF Comfy workflow API graph",
    )
    source = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "vsr_source.ppm",
        "Wan2.2 TI2V-5B source image fixture",
    )

    module = plugin_loader("video", "minimax")
    plugin = module.MiniMaxImg2VidPlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, "wan22_ti2v_5b_i2v_alias.mp4")
    module.solve_path = lambda filename: str(output_path)

    inputs = base_models.ModelInputs(
        prompt="turn the local image into gentle 24fps camera motion",
        image=str(source),
        width=1280,
        height=704,
        frames=49,
        fps=24,
        steps=25,
        guidance=5.0,
        seed=220503,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, SimpleNamespace())
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, SimpleNamespace(), prefs)
        validation = validate_video(
            result_path,
            expected_width=1280,
            expected_height=704,
            expected_fps=24.0,
            expected_duration=49 / 24,
            duration_tolerance=0.25,
            require_audio=False,
        )
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"Wan2.2 TI2V-5B I2V alias Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"Wan2.2 TI2V-5B I2V alias MP4 validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        output_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "workflow_pack": str(workflow_pack),
            "source": str(source),
            "mode": "i2v",
            "plugin": "video/minimax.py",
            "legacy_alias": "Hailuo/MiniMax/img2vid",
        },
    )
