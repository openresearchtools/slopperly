import base64
import importlib
import importlib.util
import json
import re
import sys
import tempfile
import threading
import types
import unittest
import wave
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from slopperly.audit.network_guard import local_only_network

TEST_PACKAGE = "slopperly_plugin_test"


def _ensure_package(name: str) -> types.ModuleType:
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        module.__path__ = []
        sys.modules[name] = module
    return module


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def install_plugin_import_harness() -> None:
    _ensure_package(TEST_PACKAGE)
    _ensure_package(f"{TEST_PACKAGE}.models")
    _ensure_package(f"{TEST_PACKAGE}.models_plugins")
    _ensure_package(f"{TEST_PACKAGE}.models_plugins.text")
    _ensure_package(f"{TEST_PACKAGE}.models_plugins.audio")
    _ensure_package(f"{TEST_PACKAGE}.utils")

    if f"{TEST_PACKAGE}.models.base" not in sys.modules:
        _load_module(f"{TEST_PACKAGE}.models.base", ROOT / "models/base.py")

    helpers = types.ModuleType(f"{TEST_PACKAGE}.utils.helpers")
    helpers.clean_filename = lambda value: re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")
    helpers.solve_path = lambda filename: str(Path(tempfile.gettempdir()) / filename)
    helpers.remove_duplicate_phrases = lambda text: text
    sys.modules[f"{TEST_PACKAGE}.utils.helpers"] = helpers

    for name in [
        "slopperly",
        "slopperly.runtime",
        "slopperly.runtime.gateway",
        "slopperly.runtime.comfy",
        "slopperly.runtime.comfy.api_client",
        "slopperly.runtime.comfy.workflow_runner",
        "slopperly.runtime.llamacpp",
        "slopperly.runtime.llamacpp.client",
        "slopperly.runtime.vllm",
        "slopperly.runtime.vllm.stt_client",
        "slopperly.runtime.vllm.vlm_client",
        "slopperly.runtime.vllm_omni",
        "slopperly.runtime.vllm_omni.tts_client",
    ]:
        sys.modules[f"{TEST_PACKAGE}.{name}"] = importlib.import_module(name)


def load_plugin_module(kind: str, filename: str):
    install_plugin_import_harness()
    module_name = f"{TEST_PACKAGE}.models_plugins.{kind}.{filename}"
    return _load_module(module_name, ROOT / "models_plugins" / kind / f"{filename}.py")


class RuntimeHandler(BaseHTTPRequestHandler):
    chat_payload = {}
    comfy_prompt = {}
    comfy_prompts = []
    comfy_uploads = []
    speech_payloads = []
    transcription_body = b""
    wav_bytes = b"RIFF$\x00\x00\x00WAVEfmt "

    def log_message(self, *args):
        pass

    def _json(self, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _binary(self, body: bytes, content_type: str = "audio/wav"):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in {"/health", "/v1/models"}:
            return self._json({"data": [{"id": "local-model"}], "status": "ok"})
        if self.path == "/object_info":
            return self._json({
                "LoadImage": {},
                "DownloadAndLoadFlorence2Model": {},
                "Florence2Run": {},
            })
        if self.path == "/history/prompt-1":
            return self._json({
                "prompt-1": {
                    "outputs": {
                        "3": {
                            "text": ["A person stands in warm local light."],
                            "data": [
                                {
                                    "bboxes": [[10, 20, 80, 120]],
                                    "labels": ["person"],
                                }
                            ],
                        }
                    }
                }
            })
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        if self.path == "/v1/chat/completions":
            RuntimeHandler.chat_payload = json.loads(body.decode("utf-8"))
            is_video = any(
                part.get("type") == "video_url"
                for message in RuntimeHandler.chat_payload.get("messages", [])
                for part in (
                    message.get("content", [])
                    if isinstance(message.get("content"), list)
                    else []
                )
                if isinstance(part, dict)
            )
            if is_video:
                return self._json({
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps({
                                    "scene": "A local test clip.",
                                    "events": [
                                        {
                                            "start": 0.0,
                                            "end": 1.5,
                                            "description": "A caption from vLLM.",
                                        }
                                    ],
                                })
                            }
                        }
                    ],
                    "usage": {"prompt_tokens": 20, "completion_tokens": 15},
                })
            return self._json({
                "choices": [{"message": {"content": "wide shot, slow dolly, warm light"}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 7},
            })
        if self.path == "/v1/audio/speech":
            payload = json.loads(body.decode("utf-8"))
            RuntimeHandler.speech_payloads.append(payload)
            if payload.get("voice") == "json":
                return self._json({"b64_json": base64.b64encode(self.wav_bytes).decode("ascii")})
            return self._binary(self.wav_bytes)
        if self.path == "/v1/audio/transcriptions":
            RuntimeHandler.transcription_body = body
            return self._json({
                "text": "hello local world",
                "duration": 2.0,
                "language": "en",
                "segments": [
                    {"start": 0.0, "end": 1.0, "text": "hello local"},
                    {"start": 1.0, "end": 2.0, "text": "world"},
                ],
            })
        if self.path == "/upload/image":
            RuntimeHandler.comfy_uploads.append(body)
            return self._json({"name": "uploaded_source.png", "subfolder": "", "type": "input"})
        if self.path == "/prompt":
            RuntimeHandler.comfy_prompt = json.loads(body.decode("utf-8"))["prompt"]
            RuntimeHandler.comfy_prompts.append(RuntimeHandler.comfy_prompt)
            return self._json({"prompt_id": "prompt-1"})
        self.send_response(404)
        self.end_headers()


def _tiny_wav(path: Path):
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\0\0" * 3200)


class FakeStrips:
    def __init__(self, editor):
        self.editor = editor

    def new_effect(self, **kwargs):
        strip = SimpleNamespace(**kwargs)
        strip.location = [0.0, 0.0]
        strip.text = ""
        strip.frame_final_start = kwargs["frame_start"]
        strip.frame_final_duration = kwargs["length"]
        strip.channel = kwargs["channel"]
        strip.type = kwargs["type"]
        strip.right_handle = kwargs["frame_start"] + kwargs["length"]
        self.editor.created.append(strip)
        self.editor.strips_all.append(strip)
        return strip


class FakeSeqEditor:
    def __init__(self):
        self.created = []
        self.strips_all = []
        self.active_strip = None
        self.strips = FakeStrips(self)


class FakeImage:
    mode = "RGB"
    width = 128
    height = 96

    def save(self, path):
        Path(path).write_bytes(b"fake rgb image")

    def convert(self, mode):
        self.mode = mode
        return self

    def resize(self, size):
        return self


class LocalPluginPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), RuntimeHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.base = sys.modules.get(f"{TEST_PACKAGE}.models.base") or _load_module(
            f"{TEST_PACKAGE}.models.base",
            ROOT / "models/base.py",
        )

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=2)

    def setUp(self):
        RuntimeHandler.chat_payload = {}
        RuntimeHandler.comfy_prompt = {}
        RuntimeHandler.comfy_prompts = []
        RuntimeHandler.comfy_uploads = []
        RuntimeHandler.speech_payloads = []
        RuntimeHandler.transcription_body = b""

    def test_moviigen_generate_uses_llamacpp_plugin_path(self):
        module = load_plugin_module("text", "moviigen_rewriter")
        plugin = module.MoviiGenRewriterPlugin()
        inputs = self.base.ModelInputs(prompt="a lonely robot in a train station")
        prefs = SimpleNamespace(llamacpp_url=self.base_url, llamacpp_text_model="local-qwen")

        with local_only_network():
            result = plugin.generate(None, inputs, SimpleNamespace(), prefs)

        self.assertIn("wide shot", result)
        self.assertEqual(RuntimeHandler.chat_payload["model"], "local-qwen")
        self.assertEqual(RuntimeHandler.chat_payload["n_ctx"], 60000)
        self.assertEqual(RuntimeHandler.chat_payload["n_predict"], 30000)
        self.assertIn("llama.cpp usage", inputs.usage_note)

    def test_omnivoice_generate_uses_vllm_omni_plugin_path(self):
        module = load_plugin_module("audio", "omnivoice")
        plugin = module.OmniVoicePlugin()
        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(
                prompt="hello from the local runtime",
                audio_ref="/tmp/ref.wav",
                text_ref="hello",
                speed=1.2,
                seed=123,
            )
            scene = SimpleNamespace(omnivoice_instruct="warm narrator", omnivoice_language="EN")
            prefs = SimpleNamespace(vllm_omni_url=self.base_url)

            with local_only_network():
                output = plugin.generate(None, inputs, scene, prefs)
            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.wav_bytes)

        payload = RuntimeHandler.speech_payloads[-1]
        self.assertEqual(payload["model"], "k2-fsa/OmniVoice")
        self.assertEqual(payload["input"], "hello from the local runtime")
        self.assertEqual(payload["ref_audio"], "/tmp/ref.wav")
        self.assertEqual(payload["ref_text"], "hello")
        self.assertEqual(payload["speed"], 1.2)
        self.assertIn("warm narrator", payload["instructions"])

    def test_moss_generate_uses_vllm_omni_plugin_path(self):
        module = load_plugin_module("audio", "moss_tts")
        plugin = module.MossTTSPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(prompt="local moss voice", seed=321)
            scene = SimpleNamespace(
                moss_model_variant="nano",
                moss_ref_audio_path="/tmp/speaker.wav",
                moss_language="EN",
                moss_duration_tokens=128,
                moss_max_new_tokens=1024,
                moss_temperature=1.1,
                moss_top_p=0.7,
                moss_top_k=20,
            )
            prefs = SimpleNamespace(vllm_omni_url=self.base_url)

            with local_only_network():
                output = plugin.generate(None, inputs, scene, prefs)
            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.wav_bytes)

        payload = RuntimeHandler.speech_payloads[-1]
        self.assertEqual(payload["model"], "OpenMOSS-Team/MOSS-TTS-Nano")
        self.assertEqual(payload["ref_audio"], "/tmp/speaker.wav")
        self.assertIn("duration_tokens=128", payload["instructions"])

    def test_faster_whisper_generate_uses_vllm_plugin_path(self):
        module = load_plugin_module("text", "faster_whisper_transcribe")
        plugin = module.FasterWhisperTranscribePlugin()
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "speech.wav"
            _tiny_wav(wav_path)
            editor = FakeSeqEditor()
            scene = SimpleNamespace(
                whisper_model_size="large-v3-turbo",
                whisper_language="en",
                sequence_editor=editor,
                render=SimpleNamespace(fps=24, fps_base=1),
            )
            inputs = self.base.ModelInputs(
                audio_ref=str(wav_path),
                insert_frame_start=100,
                insert_channel=2,
            )
            prefs = SimpleNamespace(vllm_url=self.base_url)

            with local_only_network():
                plugin.generate(None, inputs, scene, prefs)

        self.assertIn(b"openai/whisper-large-v3-turbo", RuntimeHandler.transcription_body)
        self.assertEqual(len(editor.created), 2)
        self.assertEqual(editor.created[0].channel, 2)
        self.assertIn("hello local", editor.created[0].text)

    def test_florence2_caption_uses_comfy_plugin_path(self):
        module = load_plugin_module("text", "florence2")
        plugin = module.Florence2Plugin()
        scene = SimpleNamespace(florence2_mode="CAPTION", florence2_send_to_mask=False)
        inputs = self.base.ModelInputs(image=FakeImage(), seed=123)
        prefs = SimpleNamespace(comfyui_url=self.base_url)

        with local_only_network():
            pipe = plugin.load(prefs, scene)
            result = plugin.generate(pipe, inputs, scene, prefs)

        self.assertIn("warm local light", result)
        self.assertEqual(RuntimeHandler.comfy_prompts[0]["1"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(RuntimeHandler.comfy_prompts[0]["3"]["inputs"]["task"], "more_detailed_caption")
        self.assertEqual(RuntimeHandler.comfy_prompts[0]["3"]["inputs"]["seed"], 123)
        self.assertTrue(
            any(prompt["3"]["inputs"]["task"] == "caption_to_phrase_grounding"
                for prompt in RuntimeHandler.comfy_prompts)
        )
        self.assertIn(b'filename="slopperly_input_image_', RuntimeHandler.comfy_uploads[0])

    def test_marlin_video_captions_uses_vllm_vlm_plugin_path(self):
        module = load_plugin_module("text", "marlin_video_captions")
        plugin = module.MarlinVideoCaptionsPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            video_path = Path(tmp) / "clip.mp4"
            video_path.write_bytes(b"fake local video")
            editor = FakeSeqEditor()
            scene = SimpleNamespace(
                marlin_mode="CAPTION",
                marlin_find_query="",
                marlin_last_query="",
                marlin_speed="FAST",
                frame_end=148,
                sequence_editor=editor,
                render=SimpleNamespace(fps=24, fps_base=1),
            )
            inputs = self.base.ModelInputs(
                video_path=str(video_path),
                insert_frame_start=100,
                insert_channel=3,
            )
            prefs = SimpleNamespace(vllm_url=self.base_url, vllm_vlm_model="local-vlm")

            with local_only_network():
                pipe = plugin.load(prefs, scene)
                plugin.generate(pipe, inputs, scene, prefs)

        self.assertEqual(RuntimeHandler.chat_payload["model"], "local-vlm")
        content = RuntimeHandler.chat_payload["messages"][0]["content"]
        self.assertEqual(content[1]["type"], "video_url")
        self.assertTrue(content[1]["video_url"]["url"].startswith("file://"))
        self.assertEqual(len(editor.created), 2)
        self.assertIn("A local test clip.", editor.created[0].text)
        self.assertIn("A caption from vLLM.", editor.created[1].text)
        self.assertEqual(editor.created[1].channel, 3)


if __name__ == "__main__":
    unittest.main()
