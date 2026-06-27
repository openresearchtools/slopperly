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
    _ensure_package(f"{TEST_PACKAGE}.models_plugins.image")
    _ensure_package(f"{TEST_PACKAGE}.models_plugins.video")
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
    mp4_bytes = b"fake mp4 bytes from local comfy"
    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )

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
                "SaveImage": {},
                "UpscaleModelLoader": {},
                "ImageUpscaleWithModel": {},
                "ImageScale": {},
                "VHS_LoadVideo": {},
                "VHS_VideoCombine": {},
                "BiRefNetRMBG": {},
                "DownloadAndLoadFlorence2Model": {},
                "Florence2Run": {},
                "LoadAudio": {},
                "AudioSeparation": {},
                "SaveAudio": {},
                "UNETLoader": {},
                "VAELoader": {},
                "DualCLIPLoader": {},
                "TextEncodeAceStepAudio1.5": {},
                "EmptyAceStep1.5LatentAudio": {},
                "ConditioningZeroOut": {},
                "ModelSamplingAuraFlow": {},
                "CheckpointLoaderSimple": {},
                "CLIPLoader": {},
                "CLIPTextEncode": {},
                "ConditioningStableAudio": {},
                "EmptyLatentAudio": {},
                "KSampler": {},
                "VAEDecodeAudio": {},
                "MMAudioModelLoader": {},
                "MMAudioFeatureUtilsLoader": {},
                "MMAudioSampler": {},
                "MMAudioVoCoderLoader": {},
                "Foundation1ModelLoader": {},
                "Foundation1Generate": {},
                "FL_ChatterboxTTS": {},
                "FL_ChatterboxVC": {},
                "FL_ChatterboxTurboTTS": {},
                "FL_ChatterboxMultilingualTTS": {},
            })
        if self.path.startswith("/view"):
            if ".mp4" in self.path:
                return self._binary(self.mp4_bytes, "video/mp4")
            if ".flac" in self.path or ".wav" in self.path:
                return self._binary(self.wav_bytes, "audio/wav")
            return self._binary(self.png_bytes, "image/png")
        if self.path == "/history/prompt-1":
            if any(
                node.get("class_type") == "AudioSeparation"
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
            ):
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            "3": {
                                "audio": [
                                    {
                                        "filename": "slopperly_stem_bass_00001_.flac",
                                        "subfolder": "",
                                        "type": "output",
                                    }
                                ]
                            },
                            "4": {
                                "audio": [
                                    {
                                        "filename": "slopperly_stem_drums_00001_.flac",
                                        "subfolder": "",
                                        "type": "output",
                                    }
                                ]
                            },
                            "5": {
                                "audio": [
                                    {
                                        "filename": "slopperly_stem_other_00001_.flac",
                                        "subfolder": "",
                                        "type": "output",
                                    }
                                ]
                            },
                            "6": {
                                "audio": [
                                    {
                                        "filename": "slopperly_stem_vocals_00001_.flac",
                                        "subfolder": "",
                                        "type": "output",
                                    }
                                ]
                            },
                        }
                    }
                })
            if any(
                node.get("class_type") == "MMAudioSampler"
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
            ):
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            "5": {
                                "audio": [
                                    {
                                        "filename": "slopperly_mmaudio_00001_.flac",
                                        "subfolder": "",
                                        "type": "output",
                                    }
                                ]
                            }
                        }
                    }
                })
            if any(
                node.get("class_type") == "TextEncodeAceStepAudio1.5"
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
            ):
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            "10": {
                                "audio": [
                                    {
                                        "filename": "slopperly_ace_step_15_00001_.flac",
                                        "subfolder": "",
                                        "type": "output",
                                    }
                                ]
                            }
                        }
                    }
                })
            if any(
                node.get("class_type") == "Foundation1Generate"
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
            ):
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            "3": {
                                "audio": [
                                    {
                                        "filename": "slopperly_foundation1_00001_.flac",
                                        "subfolder": "",
                                        "type": "output",
                                    }
                                ]
                            }
                        }
                    }
                })
            if any(
                node.get("class_type") == "FL_ChatterboxVC"
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
            ):
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            "3": {
                                "audio": [
                                    {
                                        "filename": "slopperly_chatterbox_vc_00001_.flac",
                                        "subfolder": "",
                                        "type": "output",
                                    }
                                ]
                            }
                        }
                    }
                })
            if any(
                node.get("class_type") == "FL_ChatterboxTTS"
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
            ):
                output_node = "3" if "3" in RuntimeHandler.comfy_prompt else "2"
                filename = (
                    "slopperly_chatterbox_ref_00001_.flac"
                    if output_node == "3"
                    else "slopperly_chatterbox_00001_.flac"
                )
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            output_node: {
                                "audio": [
                                    {
                                        "filename": filename,
                                        "subfolder": "",
                                        "type": "output",
                                    }
                                ]
                            }
                        }
                    }
                })
            if any(
                node.get("class_type") == "FL_ChatterboxTurboTTS"
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
            ):
                output_node = "3" if "3" in RuntimeHandler.comfy_prompt else "2"
                filename = (
                    "slopperly_chatterbox_turbo_ref_00001_.flac"
                    if output_node == "3"
                    else "slopperly_chatterbox_turbo_00001_.flac"
                )
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            output_node: {
                                "audio": [
                                    {
                                        "filename": filename,
                                        "subfolder": "",
                                        "type": "output",
                                    }
                                ]
                            }
                        }
                    }
                })
            if any(
                node.get("class_type") == "FL_ChatterboxMultilingualTTS"
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
            ):
                output_node = "3" if "3" in RuntimeHandler.comfy_prompt else "2"
                filename = (
                    "slopperly_chatterbox_multilingual_ref_00001_.flac"
                    if output_node == "3"
                    else "slopperly_chatterbox_multilingual_00001_.flac"
                )
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            output_node: {
                                "audio": [
                                    {
                                        "filename": filename,
                                        "subfolder": "",
                                        "type": "output",
                                    }
                                ]
                            }
                        }
                    }
                })
            if any(
                node.get("class_type") == "VAEDecodeAudio"
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
            ):
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            "9": {
                                "audio": [
                                    {
                                        "filename": "slopperly_stable_audio_3_00001_.flac",
                                        "subfolder": "",
                                        "type": "output",
                                    }
                                ]
                            }
                        }
                    }
                })
            if any(
                node.get("class_type") == "BiRefNetRMBG"
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
            ):
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            "3": {
                                "images": [
                                    {
                                        "filename": "birefnet_rmbg.png",
                                        "subfolder": "",
                                        "type": "output",
                                    }
                                ]
                            }
                        }
                    }
                })
            if any(
                node.get("class_type") == "ImageUpscaleWithModel"
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
            ):
                if any(
                    node.get("class_type") == "VHS_VideoCombine"
                    for node in RuntimeHandler.comfy_prompt.values()
                    if isinstance(node, dict)
                ):
                    return self._json({
                        "prompt-1": {
                            "outputs": {
                                "5": {
                                    "gifs": [
                                        {
                                            "filename": "local_video_vsr.mp4",
                                            "subfolder": "",
                                            "type": "output",
                                            "format": "video/h264-mp4",
                                        }
                                    ]
                                }
                            }
                        }
                    })
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            "5": {
                                "images": [
                                    {
                                        "filename": "local_image_vsr.png",
                                        "subfolder": "",
                                        "type": "output",
                                    }
                                ]
                            }
                        }
                    }
                })
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
        if self.path in {"/upload/image", "/upload/video"}:
            RuntimeHandler.comfy_uploads.append(body)
            if self.path == "/upload/video":
                return self._json({"name": "uploaded_video.mp4", "subfolder": "", "type": "input"})
            if b".wav\"" in body or b".flac\"" in body or b".mp3\"" in body:
                return self._json({"name": "uploaded_audio.wav", "subfolder": "", "type": "input"})
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

    def test_birefnet_rmbg_uses_comfy_plugin_path(self):
        module = load_plugin_module("image", "birefnet")
        plugin = module.BiRefNetPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            scene = SimpleNamespace()
            inputs = self.base.ModelInputs(image=FakeImage(), seed=456, frames=1)
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, scene)
                output = plugin.generate(pipe, inputs, scene, prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["1"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(prompt["2"]["class_type"], "BiRefNetRMBG")
        self.assertEqual(prompt["2"]["inputs"]["model"], "BiRefNet-HR")
        self.assertEqual(prompt["2"]["inputs"]["background"], "Alpha")
        self.assertIn(b'filename="slopperly_input_image_', RuntimeHandler.comfy_uploads[-1])

    def test_local_image_vsr_uses_comfy_plugin_path(self):
        module = load_plugin_module("image", "maxine_vsr")
        plugin = module.MaxineVSRPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            scene = SimpleNamespace()
            inputs = self.base.ModelInputs(image=FakeImage(), width=64, height=48, seed=789, frames=1)
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, scene)
                output = plugin.generate(pipe, inputs, scene, prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["1"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(prompt["2"]["inputs"]["model_name"], "RealESRGAN_x4.pth")
        self.assertEqual(prompt["3"]["class_type"], "ImageUpscaleWithModel")
        self.assertEqual(prompt["4"]["inputs"]["width"], 64)
        self.assertEqual(prompt["4"]["inputs"]["height"], 48)
        self.assertEqual(prompt["4"]["inputs"]["crop"], "center")
        self.assertIn(b'filename="slopperly_input_image_', RuntimeHandler.comfy_uploads[-1])

    def test_local_video_vsr_uses_comfy_plugin_path(self):
        module = load_plugin_module("video", "maxine_vsr_video")
        plugin = module.MaxineVSRVideoPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            video_path = Path(tmp) / "clip.mp4"
            video_path.write_bytes(b"fake local video")
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            scene = SimpleNamespace()
            inputs = self.base.ModelInputs(
                video_path=str(video_path),
                width=64,
                height=48,
                fps=12.5,
                seed=790,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, scene)
                output = plugin.generate(pipe, inputs, scene, prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.mp4_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["1"]["inputs"]["video"], "uploaded_video.mp4")
        self.assertEqual(prompt["1"]["inputs"]["force_rate"], 0)
        self.assertEqual(prompt["1"]["inputs"]["custom_width"], 0)
        self.assertEqual(prompt["1"]["inputs"]["frame_load_cap"], 0)
        self.assertEqual(prompt["2"]["inputs"]["model_name"], "RealESRGAN_x4.pth")
        self.assertEqual(prompt["3"]["class_type"], "ImageUpscaleWithModel")
        self.assertEqual(prompt["4"]["inputs"]["width"], 64)
        self.assertEqual(prompt["4"]["inputs"]["height"], 48)
        self.assertEqual(prompt["5"]["class_type"], "VHS_VideoCombine")
        self.assertEqual(prompt["5"]["inputs"]["frame_rate"], 12.5)
        self.assertEqual(prompt["5"]["inputs"]["format"], "video/h264-mp4")
        self.assertEqual(prompt["5"]["inputs"]["audio"], ["1", 2])
        self.assertIn(b'name="video"; filename="clip.mp4"', RuntimeHandler.comfy_uploads[-1])

    def test_stem_split_uses_comfy_plugin_path(self):
        module = load_plugin_module("audio", "stem_split")
        plugin = module.StemSplitterPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "song.wav"
            _tiny_wav(wav_path)
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            scene = SimpleNamespace(
                stem_split_model="htdemucs_ft",
                stem_split_vocals=True,
                stem_split_drums=True,
                stem_split_bass=True,
                stem_split_other=True,
                stem_split_guitar=False,
                stem_split_piano=False,
            )
            inputs = self.base.ModelInputs(audio_ref=str(wav_path))
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, scene)
                result = plugin.generate(pipe, inputs, scene, prefs)

            self.assertTrue(result.startswith(module._MULTI_STEM_PREFIX))
            stems = json.loads(result[len(module._MULTI_STEM_PREFIX):])
            self.assertEqual(list(stems), ["vocals", "drums", "bass", "other"])
            for stem_path in stems.values():
                self.assertEqual(Path(stem_path).read_bytes(), RuntimeHandler.wav_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["1"]["class_type"], "LoadAudio")
        self.assertEqual(prompt["1"]["inputs"]["audio"], "uploaded_audio.wav")
        self.assertEqual(prompt["2"]["class_type"], "AudioSeparation")
        self.assertEqual(prompt["3"]["inputs"]["audio"], ["2", 0])
        self.assertEqual(prompt["4"]["inputs"]["audio"], ["2", 1])
        self.assertEqual(prompt["5"]["inputs"]["audio"], ["2", 2])
        self.assertEqual(prompt["6"]["inputs"]["audio"], ["2", 3])
        self.assertIn(b'name="image"; filename="song.wav"', RuntimeHandler.comfy_uploads[-1])

    def test_mmaudio_uses_comfy_plugin_path(self):
        module = load_plugin_module("audio", "mmaudio")
        plugin = module.MMAudioPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            video_path = Path(tmp) / "clip.mp4"
            video_path.write_bytes(b"fake local video")
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            scene = SimpleNamespace(
                mmaudio_force_offload=False,
                mmaudio_mask_away_clip=True,
            )
            inputs = self.base.ModelInputs(
                prompt="soft machinery and room tone",
                neg_prompt="speech, music",
                video_path=str(video_path),
                audio_length=1.25,
                steps=7,
                guidance=2.5,
                seed=2468,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, scene)
                output = plugin.generate(pipe, inputs, scene, prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.wav_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["1"]["inputs"]["video"], "uploaded_video.mp4")
        self.assertEqual(prompt["2"]["class_type"], "MMAudioModelLoader")
        self.assertEqual(prompt["2"]["inputs"]["mmaudio_model"], "mmaudio_large_44k_v2_fp16.safetensors")
        self.assertEqual(prompt["2"]["inputs"]["base_precision"], "fp16")
        self.assertEqual(prompt["3"]["class_type"], "MMAudioFeatureUtilsLoader")
        self.assertEqual(prompt["3"]["inputs"]["vae_model"], "mmaudio_vae_44k_fp16.safetensors")
        self.assertEqual(prompt["3"]["inputs"]["mode"], "44k")
        self.assertEqual(prompt["4"]["class_type"], "MMAudioSampler")
        self.assertEqual(prompt["4"]["inputs"]["images"], ["1", 0])
        self.assertEqual(prompt["4"]["inputs"]["duration"], 1.25)
        self.assertEqual(prompt["4"]["inputs"]["steps"], 7)
        self.assertEqual(prompt["4"]["inputs"]["cfg"], 2.5)
        self.assertEqual(prompt["4"]["inputs"]["seed"], 2468)
        self.assertEqual(prompt["4"]["inputs"]["prompt"], "soft machinery and room tone")
        self.assertEqual(prompt["4"]["inputs"]["negative_prompt"], "speech, music")
        self.assertTrue(prompt["4"]["inputs"]["mask_away_clip"])
        self.assertFalse(prompt["4"]["inputs"]["force_offload"])
        self.assertEqual(prompt["5"]["class_type"], "SaveAudio")
        self.assertEqual(prompt["5"]["inputs"]["audio"], ["4", 0])
        self.assertIn(b'name="video"; filename="clip.mp4"', RuntimeHandler.comfy_uploads[-1])

    def test_stable_audio_3_uses_comfy_plugin_path(self):
        module = load_plugin_module("audio", "_stable_audio_3")
        plugin = module.StableAudio3Plugin()
        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            scene = SimpleNamespace(
                stable_audio_3_sampler="dpmpp_3m_sde",
                stable_audio_3_scheduler="karras",
            )
            inputs = self.base.ModelInputs(
                prompt="warm tape piano, brushed drums, rounded bass",
                neg_prompt="speech, clipping",
                audio_length=2.0,
                steps=9,
                guidance=5.5,
                seed=31415,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, scene)
                output = plugin.generate(pipe, inputs, scene, prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.wav_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["1"]["class_type"], "CheckpointLoaderSimple")
        self.assertEqual(prompt["1"]["inputs"]["ckpt_name"], "stable_audio_3_medium_base.safetensors")
        self.assertEqual(prompt["2"]["class_type"], "CLIPLoader")
        self.assertEqual(prompt["2"]["inputs"]["clip_name"], "t5gemma_b_b_ul2.safetensors")
        self.assertEqual(prompt["2"]["inputs"]["type"], "stable_audio")
        self.assertEqual(prompt["3"]["inputs"]["text"], "warm tape piano, brushed drums, rounded bass")
        self.assertEqual(prompt["4"]["inputs"]["text"], "speech, clipping")
        self.assertEqual(prompt["5"]["class_type"], "ConditioningStableAudio")
        self.assertEqual(prompt["5"]["inputs"]["seconds_total"], 2.0)
        self.assertEqual(prompt["6"]["class_type"], "EmptyLatentAudio")
        self.assertEqual(prompt["6"]["inputs"]["seconds"], 2.0)
        self.assertEqual(prompt["7"]["class_type"], "KSampler")
        self.assertEqual(prompt["7"]["inputs"]["steps"], 9)
        self.assertEqual(prompt["7"]["inputs"]["cfg"], 5.5)
        self.assertEqual(prompt["7"]["inputs"]["seed"], 31415)
        self.assertEqual(prompt["7"]["inputs"]["sampler_name"], "dpmpp_3m_sde")
        self.assertEqual(prompt["7"]["inputs"]["scheduler"], "karras")
        self.assertEqual(prompt["8"]["class_type"], "VAEDecodeAudio")
        self.assertEqual(prompt["9"]["class_type"], "SaveAudio")
        self.assertEqual(prompt["9"]["inputs"]["audio"], ["8", 0])

    def test_ace_step_uses_comfy_plugin_path(self):
        module = load_plugin_module("audio", "ace_step")
        plugin = module.AceStepPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            scene = SimpleNamespace(
                ace_step_language="en",
                ace_step_sampler="euler",
                ace_step_scheduler="simple",
                ace_step_aura_shift=3.25,
                ace_step_generate_audio_codes=False,
            )
            inputs = self.base.ModelInputs(
                prompt="bright local indie pop loop",
                lyrics="[verse]\nlocal sunlight",
                audio_length=2.0,
                steps=9,
                guidance=3.75,
                seed=24680,
                bpm=96,
                key_scale="D minor",
                time_signature="4",
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, scene)
                output = plugin.generate(pipe, inputs, scene, prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.wav_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["1"]["inputs"]["unet_name"], "acestep_v1.5_xl_base_bf16.safetensors")
        self.assertEqual(prompt["2"]["inputs"]["vae_name"], "ace_1.5_vae.safetensors")
        self.assertEqual(prompt["3"]["inputs"]["clip_name1"], "qwen_0.6b_ace15.safetensors")
        self.assertEqual(prompt["3"]["inputs"]["clip_name2"], "qwen_4b_ace15.safetensors")
        self.assertEqual(prompt["3"]["inputs"]["type"], "ace")
        self.assertEqual(prompt["4"]["inputs"]["tags"], "bright local indie pop loop")
        self.assertEqual(prompt["4"]["inputs"]["lyrics"], "[verse]\nlocal sunlight")
        self.assertEqual(prompt["4"]["inputs"]["duration"], 2.0)
        self.assertEqual(prompt["4"]["inputs"]["seed"], 24680)
        self.assertEqual(prompt["4"]["inputs"]["bpm"], 96)
        self.assertEqual(prompt["4"]["inputs"]["timesignature"], "4")
        self.assertEqual(prompt["4"]["inputs"]["keyscale"], "D minor")
        self.assertFalse(prompt["4"]["inputs"]["generate_audio_codes"])
        self.assertEqual(prompt["5"]["inputs"]["conditioning"], ["4", 0])
        self.assertEqual(prompt["6"]["inputs"]["seconds"], 2.0)
        self.assertEqual(prompt["7"]["inputs"]["shift"], 3.25)
        self.assertEqual(prompt["8"]["inputs"]["seed"], 24680)
        self.assertEqual(prompt["8"]["inputs"]["steps"], 9)
        self.assertEqual(prompt["8"]["inputs"]["cfg"], 3.75)
        self.assertEqual(prompt["8"]["inputs"]["sampler_name"], "euler")
        self.assertEqual(prompt["8"]["inputs"]["scheduler"], "simple")
        self.assertEqual(prompt["9"]["inputs"]["samples"], ["8", 0])
        self.assertEqual(prompt["10"]["inputs"]["audio"], ["9", 0])

    def test_foundation_music_uses_comfy_plugin_path(self):
        module = load_plugin_module("audio", "foundation_music")
        plugin = module.FoundationMusicPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            scene = SimpleNamespace(
                foundation1_cfg_scale=6.5,
                foundation1_sampler_type="k-dpm-fast",
            )
            inputs = self.base.ModelInputs(
                prompt="clean house bass, clipped drums, bright stab",
                neg_prompt="speech, vocals",
                audio_length=15.0,
                steps=12,
                seed=4242,
                bpm=128,
                key_scale="A minor",
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, scene)
                output = plugin.generate(pipe, inputs, scene, prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.wav_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["1"]["class_type"], "Foundation1ModelLoader")
        self.assertEqual(prompt["1"]["inputs"]["model"], "Foundation-1/Foundation_1.safetensors")
        self.assertEqual(prompt["1"]["inputs"]["attention"], "auto")
        self.assertEqual(prompt["2"]["class_type"], "Foundation1Generate")
        self.assertEqual(
            prompt["2"]["inputs"]["tags"],
            "clean house bass, clipped drums, bright stab, avoid speech, vocals",
        )
        self.assertEqual(prompt["2"]["inputs"]["bpm"], "128 BPM")
        self.assertEqual(prompt["2"]["inputs"]["bars"], "8 Bars")
        self.assertEqual(prompt["2"]["inputs"]["key"], "A minor")
        self.assertEqual(prompt["2"]["inputs"]["steps"], 12)
        self.assertEqual(prompt["2"]["inputs"]["cfg_scale"], 6.5)
        self.assertEqual(prompt["2"]["inputs"]["seed"], 4242)
        self.assertEqual(prompt["2"]["inputs"]["sampler_type"], "k-dpm-fast")
        self.assertEqual(prompt["3"]["class_type"], "SaveAudio")
        self.assertEqual(prompt["3"]["inputs"]["audio"], ["2", 0])

    def test_chatterbox_uses_comfy_tts_plugin_path(self):
        module = load_plugin_module("audio", "chatterbox")
        plugin = module.ChatterboxPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            scene = SimpleNamespace(chatterbox_keep_model_loaded=True)
            inputs = self.base.ModelInputs(
                prompt="local chatterbox narration",
                audio_length=2.0,
                exaggeration=0.65,
                pace=0.35,
                temperature=0.9,
                seed=5150,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, scene)
                output = plugin.generate(pipe, inputs, scene, prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.wav_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["1"]["class_type"], "FL_ChatterboxTTS")
        self.assertEqual(prompt["1"]["inputs"]["text"], "local chatterbox narration")
        self.assertEqual(prompt["1"]["inputs"]["exaggeration"], 0.65)
        self.assertEqual(prompt["1"]["inputs"]["cfg_weight"], 0.35)
        self.assertEqual(prompt["1"]["inputs"]["temperature"], 0.9)
        self.assertEqual(prompt["1"]["inputs"]["seed"], 5150)
        self.assertTrue(prompt["1"]["inputs"]["keep_model_loaded"])
        self.assertEqual(prompt["2"]["class_type"], "SaveAudio")
        self.assertEqual(prompt["2"]["inputs"]["audio"], ["1", 0])

    def test_chatterbox_uses_comfy_reference_tts_plugin_path(self):
        module = load_plugin_module("audio", "chatterbox")
        plugin = module.ChatterboxPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "speaker.wav"
            _tiny_wav(wav_path)
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            scene = SimpleNamespace(chatterbox_use_cpu=False)
            inputs = self.base.ModelInputs(
                prompt="match the supplied local reference",
                audio_ref=str(wav_path),
                exaggeration=0.55,
                pace=0.45,
                temperature=0.75,
                seed=6160,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, scene)
                output = plugin.generate(pipe, inputs, scene, prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.wav_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["1"]["class_type"], "LoadAudio")
        self.assertEqual(prompt["1"]["inputs"]["audio"], "uploaded_audio.wav")
        self.assertEqual(prompt["2"]["class_type"], "FL_ChatterboxTTS")
        self.assertEqual(prompt["2"]["inputs"]["audio_prompt"], ["1", 0])
        self.assertEqual(prompt["2"]["inputs"]["text"], "match the supplied local reference")
        self.assertEqual(prompt["2"]["inputs"]["seed"], 6160)
        self.assertEqual(prompt["3"]["class_type"], "SaveAudio")
        self.assertEqual(prompt["3"]["inputs"]["audio"], ["2", 0])
        self.assertIn(b'name="image"; filename="speaker.wav"', RuntimeHandler.comfy_uploads[-1])

    def test_chatterbox_voice_clone_uses_comfy_vc_plugin_path(self):
        module = load_plugin_module("audio", "chatterbox")
        plugin = module.ChatterboxPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "source.wav"
            _tiny_wav(wav_path)
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            scene = SimpleNamespace()
            inputs = self.base.ModelInputs(
                audio_ref=str(wav_path),
                is_voice_clone=True,
                seed=7170,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, scene)
                output = plugin.generate(pipe, inputs, scene, prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.wav_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["1"]["class_type"], "LoadAudio")
        self.assertEqual(prompt["1"]["inputs"]["audio"], "uploaded_audio.wav")
        self.assertEqual(prompt["2"]["class_type"], "FL_ChatterboxVC")
        self.assertEqual(prompt["2"]["inputs"]["input_audio"], ["1", 0])
        self.assertEqual(prompt["2"]["inputs"]["target_voice"], ["1", 0])
        self.assertEqual(prompt["2"]["inputs"]["seed"], 7170)
        self.assertIn("legacy single audio picker", inputs.usage_note)
        self.assertEqual(prompt["3"]["class_type"], "SaveAudio")
        self.assertEqual(prompt["3"]["inputs"]["audio"], ["2", 0])

    def test_chatterbox_turbo_uses_comfy_tts_plugin_path(self):
        module = load_plugin_module("audio", "chatterbox_turbo")
        plugin = module.ChatterboxTurboPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            scene = SimpleNamespace(
                chatterbox_turbo_top_k=777,
                chatterbox_turbo_top_p=0.85,
                chatterbox_turbo_repetition_penalty=1.4,
            )
            inputs = self.base.ModelInputs(
                prompt="local turbo narration [laugh]",
                audio_length=2.0,
                exaggeration=0.65,
                pace=0.35,
                temperature=0.72,
                seed=8180,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, scene)
                output = plugin.generate(pipe, inputs, scene, prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.wav_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["1"]["class_type"], "FL_ChatterboxTurboTTS")
        self.assertEqual(prompt["1"]["inputs"]["text"], "local turbo narration [laugh]")
        self.assertEqual(prompt["1"]["inputs"]["temperature"], 0.72)
        self.assertEqual(prompt["1"]["inputs"]["top_k"], 777)
        self.assertEqual(prompt["1"]["inputs"]["top_p"], 0.85)
        self.assertEqual(prompt["1"]["inputs"]["repetition_penalty"], 1.4)
        self.assertEqual(prompt["1"]["inputs"]["seed"], 8180)
        self.assertEqual(prompt["2"]["class_type"], "SaveAudio")
        self.assertEqual(prompt["2"]["inputs"]["audio"], ["1", 0])

    def test_chatterbox_turbo_uses_comfy_reference_tts_plugin_path(self):
        module = load_plugin_module("audio", "chatterbox_turbo")
        plugin = module.ChatterboxTurboPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "speaker.wav"
            _tiny_wav(wav_path)
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            scene = SimpleNamespace(chatterbox_turbo_top_k=1234)
            inputs = self.base.ModelInputs(
                prompt="turbo reference speech",
                audio_ref=str(wav_path),
                temperature=0.66,
                seed=8280,
                is_voice_clone=True,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, scene)
                output = plugin.generate(pipe, inputs, scene, prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.wav_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["1"]["class_type"], "LoadAudio")
        self.assertEqual(prompt["1"]["inputs"]["audio"], "uploaded_audio.wav")
        self.assertEqual(prompt["2"]["class_type"], "FL_ChatterboxTurboTTS")
        self.assertEqual(prompt["2"]["inputs"]["audio_prompt"], ["1", 0])
        self.assertEqual(prompt["2"]["inputs"]["text"], "turbo reference speech")
        self.assertEqual(prompt["2"]["inputs"]["temperature"], 0.66)
        self.assertEqual(prompt["2"]["inputs"]["top_k"], 1234)
        self.assertEqual(prompt["2"]["inputs"]["seed"], 8280)
        self.assertIn("reference-audio TTS", inputs.usage_note)
        self.assertEqual(prompt["3"]["class_type"], "SaveAudio")
        self.assertIn(b'name="image"; filename="speaker.wav"', RuntimeHandler.comfy_uploads[-1])

    def test_chatterbox_multilingual_uses_comfy_tts_plugin_path(self):
        module = load_plugin_module("audio", "chatterbox_multilingual")
        plugin = module.ChatterboxMultilingualPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            scene = SimpleNamespace(
                chatterbox_mtl_language="fr",
                chatterbox_multilingual_repetition_penalty=2.5,
                chatterbox_multilingual_min_p=0.07,
                chatterbox_multilingual_top_p=0.92,
            )
            inputs = self.base.ModelInputs(
                prompt="bonjour depuis le moteur local",
                exaggeration=0.6,
                pace=0.4,
                temperature=0.7,
                seed=8380,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, scene)
                output = plugin.generate(pipe, inputs, scene, prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.wav_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["1"]["class_type"], "FL_ChatterboxMultilingualTTS")
        self.assertEqual(prompt["1"]["inputs"]["text"], "bonjour depuis le moteur local")
        self.assertEqual(prompt["1"]["inputs"]["language"], "French (fr)")
        self.assertEqual(prompt["1"]["inputs"]["exaggeration"], 0.6)
        self.assertEqual(prompt["1"]["inputs"]["cfg_weight"], 0.4)
        self.assertEqual(prompt["1"]["inputs"]["temperature"], 0.7)
        self.assertEqual(prompt["1"]["inputs"]["repetition_penalty"], 2.5)
        self.assertEqual(prompt["1"]["inputs"]["min_p"], 0.07)
        self.assertEqual(prompt["1"]["inputs"]["top_p"], 0.92)
        self.assertEqual(prompt["1"]["inputs"]["seed"], 8380)
        self.assertEqual(prompt["2"]["class_type"], "SaveAudio")
        self.assertEqual(prompt["2"]["inputs"]["audio"], ["1", 0])

    def test_chatterbox_multilingual_uses_comfy_reference_tts_plugin_path(self):
        module = load_plugin_module("audio", "chatterbox_multilingual")
        plugin = module.ChatterboxMultilingualPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "speaker.wav"
            _tiny_wav(wav_path)
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            scene = SimpleNamespace(chatterbox_mtl_language="ja")
            inputs = self.base.ModelInputs(
                prompt="local multilingual reference speech",
                audio_ref=str(wav_path),
                exaggeration=0.55,
                pace=0.45,
                temperature=0.75,
                seed=8480,
                is_voice_clone=True,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, scene)
                output = plugin.generate(pipe, inputs, scene, prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.wav_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["1"]["class_type"], "LoadAudio")
        self.assertEqual(prompt["1"]["inputs"]["audio"], "uploaded_audio.wav")
        self.assertEqual(prompt["2"]["class_type"], "FL_ChatterboxMultilingualTTS")
        self.assertEqual(prompt["2"]["inputs"]["audio_prompt"], ["1", 0])
        self.assertEqual(prompt["2"]["inputs"]["language"], "Japanese (ja)")
        self.assertEqual(prompt["2"]["inputs"]["seed"], 8480)
        self.assertIn("reference-audio TTS", inputs.usage_note)
        self.assertEqual(prompt["3"]["class_type"], "SaveAudio")
        self.assertIn(b'name="image"; filename="speaker.wav"', RuntimeHandler.comfy_uploads[-1])

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
