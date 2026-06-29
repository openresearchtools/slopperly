from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_video


LOGICAL_NAME = "ltx23_multi_staged_q5_gguf"
WORKFLOW_ID = "ltx23_multi_staged"
REQUESTED_WIDTH = 1280
REQUESTED_HEIGHT = 720
MAPPED_WIDTH = 1280
MAPPED_HEIGHT = 704
FRAMES = 17
FPS = 24.0


def test_ltx23_multi_staged_q5_workflow(gpu_cert, plugin_loader, base_models, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    workflow_pack = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "slopperly" / "workflows" / "comfy" / WORKFLOW_ID / "workflow.api.json",
        "LTX 2.3 Q5 GGUF Comfy multi-anchor workflow API graph",
    )
    start = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "vsr_source.ppm",
        "LTX multi start image fixture",
    )
    middle = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "florence2_caption.png",
        "LTX multi middle anchor image fixture",
    )
    last = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "birefnet_source.ppm",
        "LTX multi final anchor image fixture",
    )

    module = plugin_loader("video", "ltx23_multi")
    plugin = module.LTX2_3MultiStagedPlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, "ltx23_multi_staged_q5.mp4")
    module.solve_path = lambda filename: str(output_path)

    inputs = base_models.ModelInputs(
        prompt="a verified local LTX Q5 multi-anchor shot with a start pose, a middle caption card, and a final graphic pose",
        neg_prompt="static pose, frozen frame, low quality, flicker, watermark",
        image=str(start),
        middle_images_paths=[(str(middle), 0.5)],
        last_image=str(last),
        width=REQUESTED_WIDTH,
        height=REQUESTED_HEIGHT,
        frames=FRAMES,
        fps=FPS,
        steps=8,
        guidance=1.0,
        strength=0.7,
        seed=230523,
    )
    scene = SimpleNamespace(ltx23_stage_mode="FULL")
    prefs = SimpleNamespace(comfyui_url=runtime_url, comfyui_timeout=7200.0)

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, scene, prefs)
        validation = validate_video(
            result_path,
            expected_width=MAPPED_WIDTH,
            expected_height=MAPPED_HEIGHT,
            expected_fps=FPS,
            expected_duration=FRAMES / FPS,
            duration_tolerance=0.35,
            require_audio=True,
        )
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"LTX 2.3 Q5 Multi Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"LTX 2.3 Q5 Multi MP4 validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        output_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "workflow_pack": str(workflow_pack),
            "start": str(start),
            "middle": str(middle),
            "last": str(last),
            "plugin": "video/ltx23_multi.py",
            "workflow_id": WORKFLOW_ID,
            "requested_width": REQUESTED_WIDTH,
            "requested_height": REQUESTED_HEIGHT,
            "mapped_width": MAPPED_WIDTH,
            "mapped_height": MAPPED_HEIGHT,
            "frames": FRAMES,
            "fps": FPS,
            "anchor_frames": {
                "start": 0,
                "middle": [8],
                "last": FRAMES - 1,
            },
            "model_files": {
                "gguf": "ltx-2.3-22b-distilled-1.1-Q5_K_M.gguf",
                "text_encoder": "gemma_3_12B_it_fp4_mixed.safetensors",
                "connector": "ltx-2.3-22b-distilled_embeddings_connectors.safetensors",
                "video_vae": "ltx-2.3-22b-distilled_video_vae.safetensors",
                "audio_vae": "ltx-2.3-22b-distilled_audio_vae.safetensors",
                "lora": "ltx-2.3-22b-distilled-lora-384.safetensors",
            },
        },
    )
