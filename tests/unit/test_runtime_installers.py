import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from slopperly.runtime.comfy.install import install_comfy
from slopperly.runtime.llamacpp.install import (
    install_llamacpp,
    select_release_asset,
)
from slopperly.runtime.vllm.install import install_vllm
from slopperly.runtime.vllm_omni.install import install_vllm_omni


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
        self.assertIn("install-manifest.json", details)

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
        self.assertIn("vllm-omni", details)
        self.assertIn("vllm-omni-install-manifest.json", details)

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
            ]
        }
        asset = select_release_asset(release_data, "ubuntu-x64-cuda13")
        self.assertIsNotNone(asset)
        self.assertEqual(asset["browser_download_url"], "https://example.invalid/cuda.tar.gz")

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
