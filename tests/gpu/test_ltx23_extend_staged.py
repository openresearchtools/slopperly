from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_video


LOGICAL_NAME = "ltx23_extend_staged_q5_gguf"
WORKFLOW_ID = "ltx23_extend_staged"
REQUESTED_WIDTH = 1280
REQUESTED_HEIGHT = 720
MAPPED_WIDTH = 1280
MAPPED_HEIGHT = 704
EXTEND_FRAMES = 17
FPS = 24.0


def test_ltx23_extend_staged_q5_workflow(gpu_cert, plugin_loader, base_models, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    workflow_pack = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "slopperly" / "workflows" / "comfy" / WORKFLOW_ID / "workflow.api.json",
        "LTX 2.3 Q5 GGUF Comfy extension-tail workflow API graph",
    )
    source = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "video_vsr_source.mp4",
        "LTX Extend source video fixture",
    )

    module = plugin_loader("video", "ltx23_extend")
    plugin = module.LTX2_3ExtendStagedPlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, "ltx23_extend_q5.mp4")
    module.solve_path = lambda filename: str(output_path)

    inputs = base_models.ModelInputs(
        prompt="a verified local LTX Q5 extension tail continuing the tiny source clip with gentle motion",
        neg_prompt="static pose, frozen frame, low quality, flicker, watermark",
        video_path=str(source),
        width=REQUESTED_WIDTH,
        height=REQUESTED_HEIGHT,
        frames=EXTEND_FRAMES,
        fps=FPS,
        steps=8,
        guidance=1.0,
        strength=0.7,
        seed=230521,
    )
    scene = SimpleNamespace(
        sequence_editor=None,
        ltx23ext_extend_frames=EXTEND_FRAMES,
        ltx23ext_video_strength=0.7,
        ltx23_stage_mode="FULL",
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url, comfyui_timeout=7200.0)

    try:
        source_validation = validate_video(str(source), require_audio=True)
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, scene, prefs)
        expected_duration = source_validation["duration"] + EXTEND_FRAMES / FPS
        validation = validate_video(
            result_path,
            expected_width=MAPPED_WIDTH,
            expected_height=MAPPED_HEIGHT,
            expected_fps=FPS,
            expected_duration=expected_duration,
            duration_tolerance=0.55,
            require_audio=True,
        )
        if validation["duration"] <= source_validation["duration"]:
            raise ArtifactValidationError(
                f"extended video duration {validation['duration']:.3f}s is not greater than "
                f"source duration {source_validation['duration']:.3f}s"
            )
    except (RuntimeUnavailableError, WorkflowValidationError, RuntimeError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"LTX 2.3 Q5 Extend Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"LTX 2.3 Q5 Extend MP4 validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        output_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "workflow_pack": str(workflow_pack),
            "source": str(source),
            "source_validation": source_validation,
            "plugin": "video/ltx23_extend.py",
            "workflow_id": WORKFLOW_ID,
            "requested_width": REQUESTED_WIDTH,
            "requested_height": REQUESTED_HEIGHT,
            "mapped_width": MAPPED_WIDTH,
            "mapped_height": MAPPED_HEIGHT,
            "extension_frames": EXTEND_FRAMES,
            "fps": FPS,
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
