import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from slopperly.runtime.comfy.install import (
    disable_foundation1_object_info_autodownload,
    install_comfy,
)
from slopperly.runtime.llamacpp.install import (
    install_llamacpp,
    select_release_asset,
)
from slopperly.runtime.vllm.install import install_vllm
from slopperly.runtime.vllm_omni.install import install_vllm_omni
from slopperly.runtime.vllm_omni.install import patch_moss_tts_nano_controls
from slopperly.runtime.vllm_omni.install import patch_omnivoice_sampling_controls


class RuntimeInstallerTests(unittest.TestCase):
    def test_comfy_install_dry_run_plans_owned_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            steps = install_comfy(
                runtime_root=Path(tmp),
                pin=ROOT / "slopperly/runtime/comfy/nodes.lock.yaml",
                profile="cuda13",
                dry_run=True,
            )
        self.assertFalse([step for step in steps if step.status == "BLOCKED"])
        details = "\n".join(step.detail for step in steps)
        self.assertIn("ComfyUI", details)
        self.assertIn("custom_nodes", details)
        self.assertIn("slopperly_nodes", details)
        self.assertIn("object_info local-only", details)
        self.assertIn("install-manifest.json", details)

    def test_foundation1_patch_disables_object_info_autodownload(self):
        source = '''def _scan_checkpoints() -> list:
    """Return available checkpoints, auto-downloading if none are found."""
    results = _do_scan()

    if not results:
        if _check_foundation1_exists():
            pass
        else:
            logger.info(
                "No Foundation-1 models found in models/stable_audio/. "
                "Attempting auto-download from HuggingFace..."
            )
            _download_foundation1()
            results = _do_scan()

    return results
'''
        with tempfile.TemporaryDirectory() as tmp:
            loader = Path(tmp) / "loader_node.py"
            loader.write_text(source, encoding="utf-8")
            step = disable_foundation1_object_info_autodownload(loader, dry_run=False)
            patched = loader.read_text(encoding="utf-8")
        self.assertEqual(step.status, "PASS")
        self.assertIn("Slopperly disables upstream auto-download", patched)
        self.assertNotIn("_download_foundation1()", patched)

    def test_vllm_install_dry_run_records_audio_extra(self):
        with tempfile.TemporaryDirectory() as tmp:
            steps = install_vllm(
                venv_dir=Path(tmp) / "vllm-venv",
                extras="audio",
                dry_run=True,
            )
        details = "\n".join(step.detail for step in steps)
        self.assertIn("vllm[audio]", details)
        self.assertIn("vllm-install-manifest.json", details)

    def test_vllm_omni_install_dry_run_records_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            steps = install_vllm_omni(
                venv_dir=Path(tmp) / "vllm-omni-venv",
                dry_run=True,
            )
        details = "\n".join(step.detail for step in steps)
        names = {step.name for step in steps}
        self.assertIn("vllm-omni==0.22.0", details)
        self.assertIn("vllm==0.22.0", details)
        self.assertIn("omnivoice-patch", names)
        self.assertIn("moss-tts-nano-patch", names)
        self.assertIn("vllm-omni-install-manifest.json", details)

    def test_vllm_omni_omnivoice_patch_maps_sampling_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = (
                Path(tmp)
                / "vllm-omni-venv/lib/python3.12/site-packages/vllm_omni/diffusion/models/omnivoice/pipeline_omnivoice.py"
            )
            pipeline.parent.mkdir(parents=True)
            pipeline.write_text(
                '''        extra = req.sampling_params.extra_args or {}
        seed = extra.get("seed", None)
        tokens = self.generator(
            input_ids=batch_input_ids,
            num_step=self.num_step,
            guidance_scale=self.guidance_scale,
            seed=seed,
        )
''',
                encoding="utf-8",
            )
            step = patch_omnivoice_sampling_controls(Path(tmp) / "vllm-omni-venv")
            patched = pipeline.read_text(encoding="utf-8")
        self.assertEqual(step.status, "PASS")
        self.assertIn("num_step = int(extra.get(\"num_step\", self.num_step))", patched)
        self.assertIn("guidance_scale = float(extra.get(\"guidance_scale\", self.guidance_scale))", patched)
        self.assertIn("num_step=num_step", patched)
        self.assertIn("guidance_scale=guidance_scale", patched)

    def test_vllm_omni_moss_patch_maps_request_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            serving = (
                Path(tmp)
                / "vllm-omni-venv/lib/python3.12/site-packages/vllm_omni/entrypoints/openai/serving_speech.py"
            )
            serving.parent.mkdir(parents=True)
            serving.write_text(
                '''            if request.max_new_tokens is not None:
                params["max_new_frames"] = [request.max_new_tokens]
            wav_list, sr = await self._resolve_ref_audio(request.ref_audio)
            params["prompt_audio_array"] = [[wav_list, sr]]
            return params
''',
                encoding="utf-8",
            )
            step = patch_moss_tts_nano_controls(Path(tmp) / "vllm-omni-venv")
            patched = serving.read_text(encoding="utf-8")
        self.assertEqual(step.status, "PASS")
        self.assertIn("request-time MOSS-TTS-Nano controls", patched)
        self.assertIn("max_new_frames = extra.get(\"max_new_frames\", request.max_new_tokens)", patched)
        self.assertIn("params[\"seed\"] = [int(request.seed)]", patched)
        self.assertIn("(\"text_temperature\", \"text_temperature\", float)", patched)
        self.assertIn("(\"audio_top_k\", \"audio_top_k\", int)", patched)

    def test_llamacpp_selects_matching_archive_asset(self):
        release_data = {
            "assets": [
                {
                    "name": "llama.cpp-b9803-macos.zip",
                    "browser_download_url": "https://example.invalid/macos.zip",
                },
                {
                    "name": "llama.cpp-b9803-ubuntu-x64-cuda13.tar.gz",
                    "browser_download_url": "https://example.invalid/cuda.tar.gz",
                },
                {
                    "name": "llama-b9803-bin-ubuntu-cuda13-x64.tar.gz",
                    "browser_download_url": "https://example.invalid/cuda-real.tar.gz",
                },
            ]
        }
        asset = select_release_asset(release_data, "ubuntu-x64-cuda13")
        self.assertIsNotNone(asset)
        self.assertEqual(asset["browser_download_url"], "https://example.invalid/cuda.tar.gz")

    def test_llamacpp_selects_reordered_cuda_archive_asset(self):
        release_data = {
            "assets": [
                {
                    "name": "llama-b9803-bin-ubuntu-cuda13-x64.tar.gz",
                    "browser_download_url": "https://example.invalid/cuda-real.tar.gz",
                }
            ]
        }
        asset = select_release_asset(release_data, "ubuntu-x64-cuda13")
        self.assertIsNotNone(asset)
        self.assertEqual(asset["browser_download_url"], "https://example.invalid/cuda-real.tar.gz")

    def test_llamacpp_dry_run_does_not_query_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            steps = install_llamacpp(
                runtime_root=Path(tmp),
                release="b9803",
                artifact="ubuntu-x64-cuda13",
                dry_run=True,
            )
        statuses = {step.name: step.status for step in steps}
        self.assertEqual(statuses["cuda"], "PLAN")
        self.assertEqual(statuses["release"], "PLAN")
        self.assertEqual(statuses["launch"], "PLAN")
        self.assertFalse([step for step in steps if step.status == "BLOCKED"])


if __name__ == "__main__":
    unittest.main()
