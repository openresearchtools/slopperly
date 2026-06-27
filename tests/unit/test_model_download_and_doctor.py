import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from slopperly.doctor import run_checks, selected_runtimes
from slopperly.audit.model_registry import validate_model_registry
from slopperly.models.download import (
    download_models,
    huggingface_repo_id,
    is_exact_file,
    is_safe_relative_file,
)


class ModelDownloadAndDoctorTests(unittest.TestCase):
    def test_huggingface_repo_id_parses_artifact_urls(self):
        self.assertEqual(
            huggingface_repo_id("https://huggingface.co/unsloth/Qwen-Image-Edit-2511-GGUF"),
            "unsloth/Qwen-Image-Edit-2511-GGUF",
        )
        self.assertEqual(
            huggingface_repo_id("https://huggingface.co/org/model/blob/main/file.gguf"),
            "org/model",
        )
        self.assertIsNone(huggingface_repo_id("local GGUF configured by model manager"))

    def test_exact_file_detection_blocks_generic_registry_text(self):
        self.assertTrue(is_exact_file("model-Q5_K_M.gguf"))
        self.assertFalse(is_exact_file("model artifacts downloaded by vLLM"))
        self.assertFalse(is_exact_file("nested/path/model.gguf"))
        self.assertTrue(is_safe_relative_file("config.json"))
        self.assertTrue(is_safe_relative_file("subdir/config.json"))
        self.assertFalse(is_safe_relative_file("../config.json"))

    def test_download_dry_run_plans_files_and_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = download_models(
                root=ROOT,
                profile="smoke_16gb",
                cache_root=Path(tmp),
                dry_run=True,
            )
        statuses = {(result.model, result.status) for result in results}
        self.assertIn(("qwen_image_edit_2511_multi_gguf", "PLAN"), statuses)
        self.assertIn(("wan22_ti2v_5b_720p24_gguf", "PLAN"), statuses)
        self.assertIn(("vllm_whisper_large_v3_turbo_stt", "PLAN"), statuses)
        self.assertIn(("vllm_video_caption_vlm", "PLAN"), statuses)
        self.assertIn(("florence2_caption_ocr", "PLAN"), statuses)
        self.assertIn(("birefnet_rmbg", "PLAN"), statuses)
        self.assertIn(("local_image_vsr_upscale", "PLAN"), statuses)
        self.assertIn(("local_video_vsr_upscale", "PLAN"), statuses)
        self.assertIn(("audio_stem_split_demucs", "PLAN"), statuses)
        self.assertIn(("mmaudio_video_to_audio", "PLAN"), statuses)
        self.assertIn(("mmaudio_video_to_audio:bigvgan_44k", "PLAN"), statuses)
        self.assertIn(("stable_audio_3_medium_base", "PLAN"), statuses)
        self.assertIn(("ace_step_15_music", "PLAN"), statuses)
        self.assertIn(("foundation1_music_loop", "PLAN"), statuses)
        self.assertIn(("chatterbox_tts_vc_comfy", "PLAN"), statuses)
        self.assertIn(("chatterbox_tts_vc_comfy:chatterbox_vc", "PLAN"), statuses)
        self.assertIn(("llamacpp_prompt_rewriter", "PLAN"), statuses)
        self.assertIn(("omnivoice_vllm_omni", "PLAN"), statuses)
        self.assertIn(("moss_tts_nano_vllm_omni", "PLAN"), statuses)
        self.assertFalse([result for result in results if result.status == "BLOCKED"])

    def test_doctor_local_only_checks_pass_without_runtime_probe(self):
        checks = run_checks(root=ROOT, local_only=True, cuda=False, runtimes="none")
        by_name = {check.name: check.status for check in checks}
        self.assertEqual(by_name["local_only_surface"], "PASS")
        self.assertEqual(by_name["no_cloud"], "PASS")
        self.assertEqual(by_name["model_registry"], "PASS")
        self.assertEqual(by_name["workflow_packs"], "PASS")

    def test_model_registry_audit_passes_current_registry(self):
        self.assertEqual(validate_model_registry(ROOT), [])

    def test_selected_runtimes(self):
        self.assertEqual(selected_runtimes("none"), [])
        self.assertEqual(
            selected_runtimes("all"),
            ["comfyui", "vllm", "vllm_omni", "llamacpp"],
        )
        self.assertEqual(selected_runtimes("comfyui,vllm"), ["comfyui", "vllm"])


if __name__ == "__main__":
    unittest.main()
