from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_video


LOGICAL_NAME = "wan22_i2v_a14b_720p16_to24_gguf"
WORKFLOW_ID = LOGICAL_NAME
TARGET_FRAMES = 25
NATIVE_FRAMES = 17
TARGET_FPS = 24.0
NATIVE_FPS = 16.0


def test_wan22_i2v_a14b_q5_gguf_plugin_path(gpu_cert, plugin_loader, base_models, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    workflow_pack = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "slopperly" / "workflows" / "comfy" / WORKFLOW_ID / "workflow.api.json",
        "Wan2.2 A14B I2V Q5 GGUF Comfy workflow API graph",
    )
    source = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "vsr_source.ppm",
        "Wan2.2 A14B source image fixture",
    )
    model_files = {
        "high_noise_gguf": repo_root
        / ".slopperly/runtimes/ComfyUI/models/unet/HighNoise/Wan2.2-I2V-A14B-HighNoise-Q5_K_M.gguf",
        "low_noise_gguf": repo_root
        / ".slopperly/runtimes/ComfyUI/models/unet/LowNoise/Wan2.2-I2V-A14B-LowNoise-Q5_K_M.gguf",
        "text_encoder": repo_root
        / ".slopperly/runtimes/ComfyUI/models/text_encoders/umt5_xxl_wan_text_encoder.safetensors",
        "vae": repo_root / ".slopperly/runtimes/ComfyUI/models/vae/wan_2.1_vae.safetensors",
        "high_lora": repo_root
        / ".slopperly/runtimes/ComfyUI/models/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors",
        "low_lora": repo_root
        / ".slopperly/runtimes/ComfyUI/models/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors",
    }
    for label, path in model_files.items():
        gpu_cert.require_file(LOGICAL_NAME, path, f"Wan2.2 A14B {label} artifact")

    module = plugin_loader("video", "wan_i2v")
    plugin = module.WanI2VPlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, "wan22_i2v_a14b_24fps.mp4")
    native_path = output_path.with_name(output_path.stem + "_native16.mp4")
    module.solve_path = lambda filename: str(output_path)

    inputs = base_models.ModelInputs(
        prompt="a local Wan A14B image-to-video smoke test with gentle camera drift",
        neg_prompt="text, watermark, low quality, jitter",
        image=str(source),
        width=1280,
        height=720,
        frames=TARGET_FRAMES,
        fps=TARGET_FPS,
        steps=4,
        guidance=1.0,
        seed=220514,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url, comfyui_timeout=7200.0)

    try:
        pipe_obj = plugin.load(prefs, SimpleNamespace())
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, SimpleNamespace(), prefs)
        native_validation = validate_video(
            str(native_path),
            expected_width=1280,
            expected_height=720,
            expected_fps=NATIVE_FPS,
            expected_duration=NATIVE_FRAMES / NATIVE_FPS,
            duration_tolerance=0.25,
            require_audio=False,
        )
        validation = validate_video(
            result_path,
            expected_width=1280,
            expected_height=720,
            expected_fps=TARGET_FPS,
            expected_duration=TARGET_FRAMES / TARGET_FPS,
            duration_tolerance=0.35,
            require_audio=False,
        )
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"Wan2.2 A14B I2V Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"Wan2.2 A14B I2V MP4 validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        output_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "workflow_pack": str(workflow_pack),
            "source": str(source),
            "plugin": "video/wan_i2v.py",
            "mode": "i2v",
            "target_fps": TARGET_FPS,
            "workflow_native_fps": NATIVE_FPS,
            "requested_target_frames": TARGET_FRAMES,
            "generated_native_frames": NATIVE_FRAMES,
            "native_artifact": str(native_path),
            "native_validation": native_validation,
            "model_files": {
                key: path.name for key, path in model_files.items()
            },
            "gguf_backbones": [
                "Wan2.2-I2V-A14B-HighNoise-Q5_K_M.gguf",
                "Wan2.2-I2V-A14B-LowNoise-Q5_K_M.gguf",
            ],
        },
    )
