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

    def test_vllm_launch_accepts_stt_profile_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            venv = Path(tmp) / "vllm-venv"
            make_executable(venv / "bin/python")
            supervisor = VllmSupervisor(venv=venv, url="http://127.0.0.1:8090")
            command = supervisor.launch_command(
                "openai/whisper-large-v3-turbo",
                served_model_name="openai/whisper-large-v3-turbo",
                max_num_batched_tokens=2048,
                gpu_memory_utilization=0.35,
                max_num_seqs=1,
                enforce_eager=True,
            )
        self.assertIn("--served-model-name", command)
        self.assertIn("openai/whisper-large-v3-turbo", command)
        self.assertIn("--max-num-batched-tokens", command)
        self.assertIn("2048", command)
        self.assertIn("--gpu-memory-utilization", command)
        self.assertIn("0.35", command)
        self.assertIn("--max-num-seqs", command)
        self.assertIn("1", command)
        self.assertIn("--enforce-eager", command)

    def test_vllm_launch_accepts_multimodal_profile_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            venv = root / "vllm-venv"
            make_executable(venv / "bin/python")
            model = root / "models/qwen-vl"
            model.mkdir(parents=True)
            supervisor = VllmSupervisor(
                venv=venv,
                url="http://127.0.0.1:8090",
                allowed_local_media_path=root,
            )
            command = supervisor.launch_command(
                str(model),
                served_model_name="Qwen/Qwen2.5-VL-7B-Instruct",
                download_dir=root / "runtime-cache",
                max_model_len=4096,
                gpu_memory_utilization=0.82,
                cpu_offload_gb=6,
                max_num_seqs=1,
                limit_mm_per_prompt={"video": {"count": 1, "num_frames": 8}, "image": 0},
                media_io_kwargs={"video": {"num_frames": 8, "backend": "pyav"}},
                mm_processor_cache_gb=0,
                enforce_eager=True,
            )
        self.assertIn("--served-model-name", command)
        self.assertIn("Qwen/Qwen2.5-VL-7B-Instruct", command)
        self.assertIn("--download-dir", command)
        self.assertIn("--max-model-len", command)
        self.assertIn("4096", command)
        self.assertIn("--cpu-offload-gb", command)
        self.assertIn("6.0", command)
        self.assertIn("--limit-mm-per-prompt", command)
        self.assertIn('"num_frames": 8', command[command.index("--limit-mm-per-prompt") + 1])
        self.assertIn("--media-io-kwargs", command)
        self.assertIn('"backend": "pyav"', command[command.index("--media-io-kwargs") + 1])
        self.assertIn("--enforce-eager", command)

    def test_vllm_omni_launch_uses_local_openai_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            venv = Path(tmp) / "vllm-omni-venv"
            make_executable(venv / "bin/vllm-omni")
            supervisor = VllmOmniSupervisor(venv=venv, url="http://127.0.0.1:8091")
            self.assertFalse([step for step in supervisor.preflight() if step.status == "BLOCKED"])
            command = supervisor.launch_command("k2-fsa/OmniVoice")
        self.assertEqual(command[1:4], ["serve", "k2-fsa/OmniVoice", "--omni"])
        self.assertIn("k2-fsa/OmniVoice", command)
        self.assertIn("8091", command)
        self.assertIn("--allowed-local-media-path", command)
        self.assertIn("--download-dir", command)

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
        self.assertIn("--n-gpu-layers", command)
        self.assertIn("999", command)
        self.assertIn("--flash-attn", command)
        self.assertIn("on", command)
        self.assertIn("--parallel", command)
        self.assertIn("1", command)
        self.assertIn(str(model), command)


if __name__ == "__main__":
    unittest.main()
