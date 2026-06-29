import math
from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_audio, validate_video


LOGICAL_NAME = "ltx23_lipsync_dialogue_q5_gguf"
WORKFLOW_ID = "ltx23_lipsync_dialogue"
REQUESTED_WIDTH = 1280
REQUESTED_HEIGHT = 720
MAPPED_WIDTH = 1280
MAPPED_HEIGHT = 704
FPS = 24.0


def _ltx_8n_plus_1(frames: int) -> int:
    requested = max(9, int(frames or 17))
    return ((requested - 1 + 7) // 8) * 8 + 1


def test_ltx23_lipsync_audio_duration(gpu_cert, plugin_loader, base_models, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    workflow_pack = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "slopperly" / "workflows" / "comfy" / WORKFLOW_ID / "workflow.api.json",
        "LTX 2.3 Q5 GGUF Comfy lipsync/dialogue workflow API graph",
    )
    source = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "vsr_source.ppm",
        "LTX lipsync source image fixture",
    )
    audio = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "stem_split_source.wav",
        "LTX lipsync reference audio fixture",
    )

    module = plugin_loader("video", "ltx23_lipsync")
    plugin = module.LTX2_3LipSyncPlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, "ltx23_lipsync_q5.mp4")
    module.solve_path = lambda filename: str(output_path)

    inputs = base_models.ModelInputs(
        prompt="a verified local LTX Q5 close-up speaker matching the reference audio rhythm",
        neg_prompt="static mouth, frozen face, low quality, flicker, watermark, desynced speech",
        image=str(source),
        audio_ref=str(audio),
        width=REQUESTED_WIDTH,
        height=REQUESTED_HEIGHT,
        frames=0,
        fps=FPS,
        steps=8,
        guidance=1.0,
        strength=0.7,
        seed=230522,
    )
    scene = SimpleNamespace(
        sequence_editor=None,
        ref_audio_path="",
        ltx23_lipsync_identity_guidance=1.5,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url, comfyui_timeout=7200.0)

    validation = {}
    audio_validation = {}
    try:
        audio_validation = validate_audio(str(audio), require_non_silent=True)
        target_frames = max(1, math.ceil(audio_validation["duration"] * FPS))
        workflow_frames = _ltx_8n_plus_1(target_frames)
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, scene, prefs)
        validation = validate_video(
            result_path,
            expected_width=MAPPED_WIDTH,
            expected_height=MAPPED_HEIGHT,
            expected_fps=FPS,
            expected_duration=audio_validation["duration"],
            duration_tolerance=0.25,
            require_audio=True,
        )
    except (RuntimeUnavailableError, WorkflowValidationError, RuntimeError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"LTX 2.3 Q5 lipsync Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"LTX 2.3 Q5 lipsync MP4 validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        output_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "workflow_pack": str(workflow_pack),
            "source": str(source),
            "audio": str(audio),
            "audio_validation": audio_validation,
            "plugin": "video/ltx23_lipsync.py",
            "workflow_id": WORKFLOW_ID,
            "requested_width": REQUESTED_WIDTH,
            "requested_height": REQUESTED_HEIGHT,
            "mapped_width": MAPPED_WIDTH,
            "mapped_height": MAPPED_HEIGHT,
            "target_fps": FPS,
            "target_frames": target_frames,
            "workflow_frames": workflow_frames,
            "identity_guidance": 1.5,
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
