import base64
import json
import tempfile
import threading
import unittest
import wave
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from slopperly.runtime.errors import RuntimeUnavailableError
from slopperly.runtime.llamacpp.client import LlamaCppClient
from slopperly.runtime.local_url import assert_local_http_url
from slopperly.runtime.vllm.stt_client import VllmSttClient
from slopperly.runtime.vllm.vlm_client import VllmVlmClient
from slopperly.runtime.vllm_omni.tts_client import VllmOmniTtsClient


class RuntimeHandler(BaseHTTPRequestHandler):
    last_json = {}
    last_multipart = b""
    wav_bytes = b"RIFF$\x00\x00\x00WAVEfmt "

    def log_message(self, *args):
        pass

    def _json(self, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _binary(self, body, content_type="audio/wav"):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/v1/models":
            return self._json({"data": [{"id": "local-model"}]})
        if self.path == "/props":
            return self._json({"default_generation_settings": {"n_ctx": 32768}})
        if self.path == "/health":
            return self._json({"status": "ok"})
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        if self.path == "/v1/chat/completions":
            RuntimeHandler.last_json = json.loads(body.decode("utf-8"))
            is_video = any(
                part.get("type") == "video_url"
                for message in RuntimeHandler.last_json.get("messages", [])
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
                                            "end": 1.0,
                                            "description": "A person waves.",
                                        }
                                    ],
                                })
                            }
                        }
                    ],
                })
            return self._json({
                "choices": [{"message": {"content": "wide shot, slow dolly, warm light"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 8},
            })
        if self.path == "/v1/audio/transcriptions":
            RuntimeHandler.last_multipart = body
            return self._json({
                "text": "hello local world",
                "duration": 2.0,
                "language": "en",
                "segments": [{"start": 0.0, "end": 2.0, "text": "hello local world"}],
            })
        if self.path == "/v1/audio/speech":
            RuntimeHandler.last_json = json.loads(body.decode("utf-8"))
            if RuntimeHandler.last_json.get("voice") == "json":
                encoded = base64.b64encode(RuntimeHandler.wav_bytes).decode("ascii")
                return self._json({"b64_json": encoded})
            return self._binary(RuntimeHandler.wav_bytes)
        self.send_response(404)
        self.end_headers()


def _tiny_wav(path: Path):
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\0\0" * 1600)


class LocalRuntimeClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), RuntimeHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=2)

    def setUp(self):
        RuntimeHandler.last_json = {}
        RuntimeHandler.last_multipart = b""

    def test_local_url_guard_rejects_cloud_hosts(self):
        with self.assertRaises(RuntimeUnavailableError):
            assert_local_http_url("https://example.com/v1", label="runtime")

    def test_llamacpp_chat_sends_context_and_token_defaults(self):
        text, diagnostics = LlamaCppClient(self.base_url).chat(
            [{"role": "user", "content": "make this cinematic"}],
            context_length=60000,
            max_new_tokens=30000,
        )
        self.assertIn("wide shot", text)
        self.assertEqual(RuntimeHandler.last_json["n_ctx"], 60000)
        self.assertEqual(RuntimeHandler.last_json["n_predict"], 30000)
        self.assertEqual(diagnostics["usage"]["completion_tokens"], 8)
        self.assertEqual(diagnostics["served_context_length"], 32768)
        self.assertIn("model/runtime capped", diagnostics["context_fallback"])

    def test_vllm_stt_posts_audio_multipart(self):
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "speech.wav"
            _tiny_wav(wav_path)
            result = VllmSttClient(self.base_url).transcribe(
                str(wav_path),
                model="openai/whisper-large-v3-turbo",
                language="en",
            )
        self.assertEqual(result["text"], "hello local world")
        self.assertIn(b"local-model", RuntimeHandler.last_multipart)
        self.assertIn(b'name="file"; filename="speech.wav"', RuntimeHandler.last_multipart)

    def test_vllm_stt_preserves_explicit_model_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "speech.wav"
            _tiny_wav(wav_path)
            VllmSttClient(self.base_url).transcribe(
                str(wav_path),
                model="custom/whisper",
                language="en",
            )
        self.assertIn(b"custom/whisper", RuntimeHandler.last_multipart)

    def test_vllm_vlm_posts_local_video_chat(self):
        with tempfile.TemporaryDirectory() as tmp:
            video_path = Path(tmp) / "clip.mp4"
            video_path.write_bytes(b"fake local video")
            result = VllmVlmClient(self.base_url).caption_video(
                str(video_path),
                model="local-vlm",
                duration_seconds=2.0,
                max_tokens=128,
            )
        self.assertEqual(result["scene"], "A local test clip.")
        self.assertEqual(result["events"][0]["description"], "A person waves.")
        self.assertEqual(RuntimeHandler.last_json["model"], "local-vlm")
        content = RuntimeHandler.last_json["messages"][0]["content"]
        self.assertEqual(content[1]["type"], "video_url")
        self.assertTrue(content[1]["video_url"]["url"].startswith("file://"))

    def test_vllm_vlm_resolves_default_single_served_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            video_path = Path(tmp) / "clip.mp4"
            video_path.write_bytes(b"fake local video")
            VllmVlmClient(self.base_url).caption_video(
                str(video_path),
                duration_seconds=2.0,
                max_tokens=128,
            )
        self.assertEqual(RuntimeHandler.last_json["model"], "local-model")

    def test_vllm_omni_speech_writes_binary_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "voice.wav"
            ref = Path(tmp) / "ref.wav"
            _tiny_wav(ref)
            result = VllmOmniTtsClient(self.base_url).speech(
                text="hello",
                output_path=str(out),
                model="k2-fsa/OmniVoice",
                ref_audio=str(ref),
                ref_text="hello",
                speed=1.1,
                seed=123,
                max_new_tokens=128,
                extra_params={"num_step": 24, "guidance_scale": 1.8},
            )
            self.assertEqual(result, str(out))
            self.assertEqual(out.read_bytes(), RuntimeHandler.wav_bytes)
        self.assertTrue(RuntimeHandler.last_json["ref_audio"].startswith("data:audio/x-wav;base64,"))
        self.assertEqual(RuntimeHandler.last_json["speed"], 1.1)
        self.assertEqual(RuntimeHandler.last_json["seed"], 123)
        self.assertEqual(RuntimeHandler.last_json["max_new_tokens"], 128)
        self.assertEqual(RuntimeHandler.last_json["extra_params"]["num_step"], 24)
        self.assertEqual(RuntimeHandler.last_json["extra_params"]["guidance_scale"], 1.8)

    def test_vllm_omni_speech_writes_json_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "voice_json.wav"
            VllmOmniTtsClient(self.base_url).speech(
                text="hello",
                output_path=str(out),
                model="OpenMOSS-Team/MOSS-TTS-Nano",
                voice="json",
            )
            self.assertEqual(out.read_bytes(), RuntimeHandler.wav_bytes)


if __name__ == "__main__":
    unittest.main()
