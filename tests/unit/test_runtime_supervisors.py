import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from slopperly.runtime.comfy.supervisor import ComfySupervisor
from slopperly.runtime.llamacpp.supervisor import LlamaCppSupervisor
from slopperly.runtime.vllm.supervisor import VllmSupervisor
from slopperly.runtime.vllm_omni.supervisor import VllmOmniSupervisor


def make_executable(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o111)


class RuntimeSupervisorTests(unittest.TestCase):
    def test_comfy_launch_uses_owned_runtime_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ComfyUI").mkdir()
            (root / "ComfyUI/main.py").write_text("print('comfy')\n", encoding="utf-8")
            make_executable(root / "comfy-venv/bin/python")
            supervisor = ComfySupervisor(root, url="http://127.0.0.1:8188")
            self.assertFalse([step for step in supervisor.preflight() if step.status == "BLOCKED"])
            command = supervisor.launch_command()
        self.assertIn("main.py", command)
        self.assertIn("--listen", command)
        self.assertIn("127.0.0.1", command)
        self.assertIn("--port", command)
        self.assertIn("8188", command)
        self.assertTrue(command[0].endswith("comfy-venv/bin/python"))

    def test_vllm_launch_uses_local_openai_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            venv = Path(tmp) / "vllm-venv"
            make_executable(venv / "bin/python")
            supervisor = VllmSupervisor(venv=venv, url="http://localhost:8090")
            self.assertFalse([step for step in supervisor.preflight() if step.status == "BLOCKED"])
            command = supervisor.launch_command("openai/whisper-large-v3-turbo")
        self.assertEqual(command[1:3], ["-m", "vllm.entrypoints.openai.api_server"])
        self.assertIn("openai/whisper-large-v3-turbo", command)
        self.assertIn("8090", command)
        self.assertIn("--allowed-local-media-path", command)
        allowed_idx = command.index("--allowed-local-media-path") + 1
        self.assertEqual(command[allowed_idx], str(Path(".").resolve()))

    def test_vllm_omni_launch_uses_local_openai_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            venv = Path(tmp) / "vllm-omni-venv"
            make_executable(venv / "bin/python")
            supervisor = VllmOmniSupervisor(venv=venv, url="http://127.0.0.1:8091")
            self.assertFalse([step for step in supervisor.preflight() if step.status == "BLOCKED"])
            command = supervisor.launch_command("k2-fsa/OmniVoice")
        self.assertEqual(command[1:3], ["-m", "vllm_omni.entrypoints.openai.api_server"])
        self.assertIn("k2-fsa/OmniVoice", command)
        self.assertIn("8091", command)

    def test_llamacpp_launch_uses_context_and_token_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_executable(root / "llama.cpp/bin/llama-server")
            model = root / "models/qwen.gguf"
            model.parent.mkdir(parents=True, exist_ok=True)
            model.write_bytes(b"gguf")
            supervisor = LlamaCppSupervisor(root, url="http://127.0.0.1:8092")
            self.assertFalse(
                [step for step in supervisor.preflight(str(model)) if step.status == "BLOCKED"]
            )
            command = supervisor.launch_command(str(model))
        self.assertEqual(Path(command[0]).name, "llama-server")
        self.assertIn("--ctx-size", command)
        self.assertIn("60000", command)
        self.assertIn("--n-predict", command)
        self.assertIn("30000", command)
        self.assertIn(str(model), command)


if __name__ == "__main__":
    unittest.main()
