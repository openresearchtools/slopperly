import tempfile
import unittest
from pathlib import Path
import sys
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from slopperly.doctor import run_checks, selected_runtimes
from slopperly.audit.model_registry import validate_model_registry
from slopperly.models.download import (
    download_models,
    hf_file_source_and_target,
    huggingface_repo_id,
    is_exact_file,
    is_safe_relative_file,
    mirror_torchaudio_asset,
    rewrite_moss_tts_nano_config,
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
        self.assertEqual(
            hf_file_source_and_target({
                "path": "split_files/text_encoders/qwen.safetensors",
                "target": "qwen.safetensors",
            }),
            ("split_files/text_encoders/qwen.safetensors", "qwen.safetensors"),
        )

    def test_download_dry_run_plans_files_and_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = download_models(
                root=ROOT,
                profile="smoke_16gb",
                cache_root=Path(tmp),
                dry_run=True,
            )
        statuses = {(result.model, result.status) for result in results}
        self.assertIn(("qwen_image_2512_t2i_gguf", "PLAN"), statuses)
        self.assertIn(("qwen_image_2512_t2i_gguf:qwen_image_2512_text_encoder", "PLAN"), statuses)
        self.assertIn(("qwen_image_edit_2511_multi_gguf", "PLAN"), statuses)
        self.assertIn(("zimage_t2i_i2i", "PLAN"), statuses)
        self.assertIn(("zimage_t2i_i2i:zimage_text_encoder", "PLAN"), statuses)
        self.assertIn(("zimage_turbo_t2i_i2i", "PLAN"), statuses)
        self.assertIn(("zimage_turbo_t2i_i2i:zimage_turbo_vae", "PLAN"), statuses)
        self.assertIn(("anima_t2i_i2i", "PLAN"), statuses)
        self.assertIn(("anima_t2i_i2i:anima_text_encoder", "PLAN"), statuses)
        self.assertIn(("anima_t2i_i2i:anima_vae", "PLAN"), statuses)
        self.assertIn(("ernie_image_t2i", "PLAN"), statuses)
        self.assertIn(("ernie_image_t2i:ernie_text_encoder", "PLAN"), statuses)
        self.assertIn(("ernie_image_t2i:ernie_prompt_enhancer", "PLAN"), statuses)
        self.assertIn(("ernie_image_t2i:ernie_vae", "PLAN"), statuses)
        self.assertIn(("ernie_image_turbo_t2i", "PLAN"), statuses)
        self.assertIn(("ernie_image_turbo_t2i:ernie_turbo_text_encoder", "PLAN"), statuses)
        self.assertIn(("ernie_image_turbo_t2i:ernie_turbo_prompt_enhancer", "PLAN"), statuses)
        self.assertIn(("ernie_image_turbo_t2i:ernie_turbo_vae", "PLAN"), statuses)
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
        self.assertIn(("chatterbox_turbo_tts_comfy", "PLAN"), statuses)
        self.assertIn(("chatterbox_multilingual_tts_comfy", "PLAN"), statuses)
        self.assertIn(("llamacpp_prompt_rewriter", "PLAN"), statuses)
        self.assertIn(("omnivoice_vllm_omni", "PLAN"), statuses)
        self.assertIn(("moss_tts_nano_vllm_omni", "PLAN"), statuses)
        self.assertIn(("moss_tts_nano_vllm_omni:moss_audio_tokenizer_nano", "PLAN"), statuses)
        self.assertIn(("moss_tts_nano_vllm_omni:moss_local_tokenizer_config", "PLAN"), statuses)
        self.assertFalse([result for result in results if result.status == "BLOCKED"])

    def test_moss_download_postprocess_points_config_to_local_tokenizer(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_root = Path(tmp)
            entry = {
                "logical_name": "moss_tts_nano_vllm_omni",
                "local_cache_path": "models/vllm_omni/OpenMOSS-Team/MOSS-TTS-Nano",
                "auxiliary_sources": [
                    {
                        "id": "moss_audio_tokenizer_nano",
                        "local_cache_path": "models/vllm_omni/OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano",
                    }
                ],
            }
            model_dir = cache_root / entry["local_cache_path"]
            tokenizer_dir = cache_root / entry["auxiliary_sources"][0]["local_cache_path"]
            model_dir.mkdir(parents=True)
            tokenizer_dir.mkdir(parents=True)
            (tokenizer_dir / "config.json").write_text("{}", encoding="utf-8")
            config_path = model_dir / "config.json"
            config_path.write_text(
                '{"audio_tokenizer_pretrained_name_or_path": "OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano"}',
                encoding="utf-8",
            )

            result = rewrite_moss_tts_nano_config(
                entry=entry,
                name="moss_tts_nano_vllm_omni",
                cache_root=cache_root,
                dry_run=False,
            )

            self.assertEqual(result.status, "PASS")
            self.assertIn(str(tokenizer_dir.resolve()), config_path.read_text(encoding="utf-8"))

    def test_torchaudio_asset_mirror_copies_to_hub_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "owned" / "hdemucs_high_trained.pt"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"local demucs checkpoint")
            entry = {
                "default_parameters": {
                    "torchaudio_asset_key": "models/hdemucs_high_trained.pt",
                }
            }
            with mock.patch("slopperly.models.download.torch_hub_dir", return_value=root / "hub"):
                result = mirror_torchaudio_asset(
                    entry=entry,
                    name="audio_stem_split_demucs",
                    source_path=source,
                    dry_run=False,
                )

            self.assertEqual(result.status, "PASS")
            mirrored = root / "hub" / "torchaudio" / "models" / "hdemucs_high_trained.pt"
            self.assertEqual(mirrored.read_bytes(), b"local demucs checkpoint")

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
