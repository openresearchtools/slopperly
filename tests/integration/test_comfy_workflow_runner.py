import json
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import WorkflowValidationError
from slopperly.runtime.gateway import SlopperlyRuntimeGateway
from slopperly.runtime.comfy.api_client import ComfyApiClient
from slopperly.runtime.comfy.workflow_runner import ComfyWorkflowRunner


class ComfyHandler(BaseHTTPRequestHandler):
    object_info_payload = {}
    last_prompt = {}
    upload_bodies = []
    request_order = []
    video_bytes = b"fake mp4 bytes from local comfy"
    audio_bytes = b"RIFF$\x00\x00\x00WAVEfmt "
    image_bytes = b"fake png bytes from local comfy"

    def log_message(self, *args):
        pass

    @classmethod
    def reset(cls, object_info_payload: dict):
        cls.object_info_payload = object_info_payload
        cls.last_prompt = {}
        cls.upload_bodies = []
        cls.request_order = []

    def _json(self, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _binary(self, body: bytes, content_type: str = "video/mp4"):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/object_info":
            ComfyHandler.request_order.append("/object_info")
            return self._json(self.object_info_payload)
        if parsed.path == "/history/prompt-1":
            ComfyHandler.request_order.append("/history")
            if any(
                node.get("class_type") == "AudioSeparation"
                for node in ComfyHandler.last_prompt.values()
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
                for node in ComfyHandler.last_prompt.values()
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
                for node in ComfyHandler.last_prompt.values()
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
                for node in ComfyHandler.last_prompt.values()
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
                for node in ComfyHandler.last_prompt.values()
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
                for node in ComfyHandler.last_prompt.values()
            ):
                output_node = "3" if "3" in ComfyHandler.last_prompt else "2"
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
                for node in ComfyHandler.last_prompt.values()
            ):
                output_node = "3" if "3" in ComfyHandler.last_prompt else "2"
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
                for node in ComfyHandler.last_prompt.values()
            ):
                output_node = "3" if "3" in ComfyHandler.last_prompt else "2"
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
                for node in ComfyHandler.last_prompt.values()
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
                node.get("class_type") == "Florence2Run"
                for node in ComfyHandler.last_prompt.values()
            ):
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
            if any(
                node.get("class_type") == "ailab_OmniGen"
                for node in ComfyHandler.last_prompt.values()
            ):
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            "5": {
                                "images": [
                                    {
                                        "filename": "slopperly_omnigen_00001_.png",
                                        "subfolder": "",
                                        "type": "output",
                                    }
                                ]
                            }
                        }
                    }
                })
            if any(
                node.get("class_type") == "TextEncodeQwenImageEditPlus"
                for node in ComfyHandler.last_prompt.values()
            ):
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            "18": {
                                "images": [
                                    {
                                        "filename": "slopperly_qwen_image_edit_00001_.png",
                                        "subfolder": "",
                                        "type": "output",
                                    }
                                ]
                            }
                        }
                    }
                })
            if (
                any(
                    node.get("class_type") == "UnetLoaderGGUF"
                    for node in ComfyHandler.last_prompt.values()
                )
                and any(
                    node.get("class_type") == "CLIPTextEncode"
                    for node in ComfyHandler.last_prompt.values()
                )
            ):
                output_node = "13" if "13" in ComfyHandler.last_prompt else "11"
                filename = (
                    "slopperly_qwen_image_2512_i2i_00001_.png"
                    if output_node == "13"
                    else "slopperly_qwen_image_2512_00001_.png"
                )
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            output_node: {
                                "images": [
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
                node.get("class_type") == "UNETLoader"
                and str((node.get("inputs") or {}).get("unet_name", "")).startswith("z_image")
                for node in ComfyHandler.last_prompt.values()
            ):
                output_node = "12" if "12" in ComfyHandler.last_prompt else "10"
                unet_name = next(
                    str((node.get("inputs") or {}).get("unet_name", ""))
                    for node in ComfyHandler.last_prompt.values()
                    if node.get("class_type") == "UNETLoader"
                )
                turbo = "turbo" in unet_name
                img2img = output_node == "12"
                filename = (
                    "slopperly_zimage_turbo_i2i_00001_.png"
                    if turbo and img2img
                    else "slopperly_zimage_turbo_00001_.png"
                    if turbo
                    else "slopperly_zimage_i2i_00001_.png"
                    if img2img
                    else "slopperly_zimage_00001_.png"
                )
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            output_node: {
                                "images": [
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
                node.get("class_type") == "UNETLoader"
                and str((node.get("inputs") or {}).get("unet_name", "")).startswith("anima-")
                for node in ComfyHandler.last_prompt.values()
            ):
                output_node = "11" if "11" in ComfyHandler.last_prompt else "9"
                filename = (
                    "slopperly_anima_i2i_00001_.png"
                    if output_node == "11"
                    else "slopperly_anima_00001_.png"
                )
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            output_node: {
                                "images": [
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
                node.get("class_type") == "UNETLoader"
                and str((node.get("inputs") or {}).get("unet_name", "")).startswith("ernie-image")
                for node in ComfyHandler.last_prompt.values()
            ):
                unet_name = next(
                    str((node.get("inputs") or {}).get("unet_name", ""))
                    for node in ComfyHandler.last_prompt.values()
                    if node.get("class_type") == "UNETLoader"
                )
                filename = (
                    "slopperly_ernie_image_turbo_00001_.png"
                    if "turbo" in unet_name
                    else "slopperly_ernie_image_00001_.png"
                )
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            "11": {
                                "images": [
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
                node.get("class_type") == "UNETLoader"
                and str((node.get("inputs") or {}).get("unet_name", "")).startswith("krea2_")
                for node in ComfyHandler.last_prompt.values()
            ):
                unet_name = next(
                    str((node.get("inputs") or {}).get("unet_name", ""))
                    for node in ComfyHandler.last_prompt.values()
                    if node.get("class_type") == "UNETLoader"
                )
                filename = (
                    "slopperly_krea2_turbo_00001_.png"
                    if "turbo" in unet_name
                    else "slopperly_krea2_base_00001_.png"
                )
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            "10": {
                                "images": [
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
                node.get("class_type") == "CheckpointLoaderSimple"
                and (node.get("inputs") or {}).get("ckpt_name") == "lumina_2.safetensors"
                for node in ComfyHandler.last_prompt.values()
            ):
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            "8": {
                                "images": [
                                    {
                                        "filename": "slopperly_lumina2_00001_.png",
                                        "subfolder": "",
                                        "type": "output",
                                    }
                                ]
                            }
                        }
                    }
                })
            if any(
                node.get("class_type") == "UNETLoader"
                and (node.get("inputs") or {}).get("unet_name") == "ideogram4_fp8_scaled.safetensors"
                for node in ComfyHandler.last_prompt.values()
            ):
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            "15": {
                                "images": [
                                    {
                                        "filename": "slopperly_ideogram4_00001_.png",
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
                        "38": {
                            "videos": [
                                {
                                    "filename": "ltx23_result.mp4",
                                    "subfolder": "video",
                                    "type": "output",
                                }
                            ]
                        }
                    }
                }
            })
        if parsed.path == "/view":
            ComfyHandler.request_order.append("/view")
            if (
                "stem_" in parsed.query
                or "mmaudio" in parsed.query
                or "stable_audio_3" in parsed.query
                or "ace_step_15" in parsed.query
                or "foundation1" in parsed.query
                or "chatterbox" in parsed.query
            ):
                return self._binary(self.audio_bytes, "audio/flac")
            if (
                "omnigen" in parsed.query
                or "qwen_image_edit" in parsed.query
                or "qwen_image_2512" in parsed.query
                or "zimage" in parsed.query
                or "anima" in parsed.query
                or "ernie_image" in parsed.query
                or "krea2" in parsed.query
                or "lumina2" in parsed.query
                or "ideogram4" in parsed.query
            ):
                return self._binary(self.image_bytes, "image/png")
            return self._binary(self.video_bytes)
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        if self.path in {"/upload/image", "/upload/video"}:
            ComfyHandler.request_order.append(self.path)
            ComfyHandler.upload_bodies.append(body)
            upload_count = len(ComfyHandler.upload_bodies)
            if self.path == "/upload/video":
                name = "uploaded_video.mp4" if upload_count == 1 else f"uploaded_video_{upload_count}.mp4"
            elif b".wav\"" in body or b".flac\"" in body or b".mp3\"" in body:
                name = "uploaded_audio.wav" if upload_count == 1 else f"uploaded_audio_{upload_count}.wav"
            else:
                name = "uploaded_source.png" if upload_count == 1 else f"uploaded_source_{upload_count}.png"
            return self._json({"name": name, "subfolder": "", "type": "input"})
        if self.path == "/prompt":
            ComfyHandler.request_order.append("/prompt")
            ComfyHandler.last_prompt = json.loads(body.decode("utf-8"))["prompt"]
            return self._json({"prompt_id": "prompt-1"})
        self.send_response(404)
        self.end_headers()


def _ltx23_object_info() -> dict:
    workflow = json.loads(
        (ROOT / "slopperly/workflows/comfy/ltx23_i2v/workflow.api.json").read_text(
            encoding="utf-8"
        )
    )
    return {node["class_type"]: {} for node in workflow.values()}


def _florence2_object_info() -> dict:
    workflow = json.loads(
        (ROOT / "slopperly/workflows/comfy/florence2_caption_ocr/workflow.api.json").read_text(
            encoding="utf-8"
        )
    )
    return {node["class_type"]: {} for node in workflow.values()}


def _stem_split_object_info() -> dict:
    workflow = json.loads(
        (ROOT / "slopperly/workflows/comfy/audio_stem_split_demucs/workflow.api.json").read_text(
            encoding="utf-8"
        )
    )
    return {node["class_type"]: {} for node in workflow.values()}


def _mmaudio_object_info() -> dict:
    workflow = json.loads(
        (ROOT / "slopperly/workflows/comfy/mmaudio_video_to_audio/workflow.api.json").read_text(
            encoding="utf-8"
        )
    )
    return {node["class_type"]: {} for node in workflow.values()}


def _stable_audio_3_object_info() -> dict:
    workflow = json.loads(
        (ROOT / "slopperly/workflows/comfy/stable_audio_3_medium_base/workflow.api.json").read_text(
            encoding="utf-8"
        )
    )
    return {node["class_type"]: {} for node in workflow.values()}


def _ace_step_object_info() -> dict:
    workflow = json.loads(
        (ROOT / "slopperly/workflows/comfy/ace_step_15_music/workflow.api.json").read_text(
            encoding="utf-8"
        )
    )
    return {node["class_type"]: {} for node in workflow.values()}


def _foundation1_object_info() -> dict:
    workflow = json.loads(
        (ROOT / "slopperly/workflows/comfy/foundation1_music_loop/workflow.api.json").read_text(
            encoding="utf-8"
        )
    )
    return {node["class_type"]: {} for node in workflow.values()}


def _chatterbox_object_info(workflow_id: str) -> dict:
    workflow = json.loads(
        (ROOT / "slopperly/workflows/comfy" / workflow_id / "workflow.api.json").read_text(
            encoding="utf-8"
        )
    )
    return {node["class_type"]: {} for node in workflow.values()}


def _omnigen_object_info() -> dict:
    workflow = json.loads(
        (ROOT / "slopperly/workflows/comfy/omnigen_v1_multi_image/workflow.api.json").read_text(
            encoding="utf-8"
        )
    )
    return {node["class_type"]: {} for node in workflow.values()}


def _qwen_image_edit_object_info() -> dict:
    workflow = json.loads(
        (
            ROOT
            / "slopperly/workflows/comfy/qwen_image_edit_2511_multi_gguf/workflow.api.json"
        ).read_text(encoding="utf-8")
    )
    return {node["class_type"]: {} for node in workflow.values()}


def _qwen_image_object_info(workflow_id: str) -> dict:
    workflow = json.loads(
        (ROOT / "slopperly/workflows/comfy" / workflow_id / "workflow.api.json").read_text(
            encoding="utf-8"
        )
    )
    return {node["class_type"]: {} for node in workflow.values()}


def _zimage_object_info(workflow_id: str) -> dict:
    workflow = json.loads(
        (ROOT / "slopperly/workflows/comfy" / workflow_id / "workflow.api.json").read_text(
            encoding="utf-8"
        )
    )
    return {node["class_type"]: {} for node in workflow.values()}


def _anima_object_info(workflow_id: str) -> dict:
    workflow = json.loads(
        (ROOT / "slopperly/workflows/comfy" / workflow_id / "workflow.api.json").read_text(
            encoding="utf-8"
        )
    )
    return {node["class_type"]: {} for node in workflow.values()}


def _ernie_object_info(workflow_id: str) -> dict:
    workflow = json.loads(
        (ROOT / "slopperly/workflows/comfy" / workflow_id / "workflow.api.json").read_text(
            encoding="utf-8"
        )
    )
    return {node["class_type"]: {} for node in workflow.values()}


def _krea_object_info(workflow_id: str) -> dict:
    workflow = json.loads(
        (ROOT / "slopperly/workflows/comfy" / workflow_id / "workflow.api.json").read_text(
            encoding="utf-8"
        )
    )
    return {node["class_type"]: {} for node in workflow.values()}


def _lumina_object_info() -> dict:
    workflow = json.loads(
        (ROOT / "slopperly/workflows/comfy/lumina2_t2i/workflow.api.json").read_text(
            encoding="utf-8"
        )
    )
    return {node["class_type"]: {} for node in workflow.values()}


def _ideogram_object_info() -> dict:
    workflow = json.loads(
        (ROOT / "slopperly/workflows/comfy/ideogram4_t2i/workflow.api.json").read_text(
            encoding="utf-8"
        )
    )
    return {node["class_type"]: {} for node in workflow.values()}


class ComfyWorkflowRunnerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), ComfyHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=2)

    def setUp(self):
        ComfyHandler.reset(_ltx23_object_info())
        self.gateway = SlopperlyRuntimeGateway(package_root=ROOT / "slopperly")

    def test_ltx23_pack_uploads_image_and_patches_api_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            destination = Path(tmp) / "result.mp4"
            source.write_bytes(b"local image fixture bytes")
            phases = []
            progress = []
            inputs = SimpleNamespace(
                prompt="local image to video",
                neg_prompt="static",
                image=str(source),
                width=1280,
                height=720,
                frames=49,
                fps=24,
                strength=0.65,
                seed=12345,
                phase_fn=phases.append,
                progress_fn=lambda step, total: progress.append((step, total)),
            )

            with local_only_network():
                result = self.gateway.run_comfy_workflow(
                    "ltx23_i2v",
                    inputs,
                    SimpleNamespace(),
                    SimpleNamespace(comfyui_url=self.base_url),
                    destination=str(destination),
                    timeout=2,
                )

            self.assertEqual(result, str(destination))
            self.assertEqual(destination.read_bytes(), ComfyHandler.video_bytes)

        self.assertEqual(progress, [(1, 5), (2, 5), (3, 5), (4, 5), (5, 5)])
        self.assertEqual(
            phases,
            [
                "Preparing Comfy workflow ltx23_i2v",
                "Patching Comfy workflow parameters",
                "Checking Comfy workflow nodes",
                "Uploading Comfy workflow inputs",
                "Queueing Comfy workflow",
                "Waiting for Comfy workflow output",
                "Collecting Comfy workflow artifacts",
                "Comfy workflow complete",
            ],
        )
        prompt = ComfyHandler.last_prompt
        self.assertEqual(prompt["7"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(prompt["11"]["inputs"]["text"], "local image to video")
        self.assertEqual(prompt["12"]["inputs"]["text"], "static")
        self.assertEqual(prompt["14"]["inputs"]["width"], 1280)
        self.assertEqual(prompt["14"]["inputs"]["height"], 720)
        self.assertEqual(prompt["14"]["inputs"]["length"], 49)
        self.assertEqual(prompt["16"]["inputs"]["frame_rate"], 24.0)
        self.assertEqual(prompt["15"]["inputs"]["strength"], 0.65)
        self.assertEqual(prompt["19"]["inputs"]["noise_seed"], 12345)
        self.assertIn(b'filename="source.png"', ComfyHandler.upload_bodies[0])
        self.assertLess(
            ComfyHandler.request_order.index("/object_info"),
            ComfyHandler.request_order.index("/prompt"),
        )
        self.assertLess(
            ComfyHandler.request_order.index("/upload/image"),
            ComfyHandler.request_order.index("/prompt"),
        )

    def test_missing_object_info_nodes_block_before_upload_or_queue(self):
        ComfyHandler.reset({"LoadImage": {}})
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            source.write_bytes(b"local image fixture bytes")
            inputs = SimpleNamespace(image=str(source))

            with self.assertRaises(WorkflowValidationError) as raised:
                with local_only_network():
                    self.gateway.run_comfy_workflow(
                        "ltx23_i2v",
                        inputs,
                        SimpleNamespace(),
                        SimpleNamespace(comfyui_url=self.base_url),
                        timeout=2,
                    )

        self.assertIn("missing required workflow node classes", str(raised.exception))
        self.assertEqual(ComfyHandler.upload_bodies, [])
        self.assertNotIn("/prompt", ComfyHandler.request_order)

    def test_florence_pack_collects_text_and_json_history_outputs(self):
        ComfyHandler.reset(_florence2_object_info())
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "caption.png"
            source.write_bytes(b"local image fixture bytes")
            inputs = SimpleNamespace(
                image=str(source),
                seed=123,
                phase_fn=lambda label: None,
                progress_fn=lambda step, total: None,
            )
            scene = SimpleNamespace(
                florence2_task="more_detailed_caption",
                florence2_text_input="",
            )

            with local_only_network():
                result = self.gateway.run_comfy_workflow(
                    "florence2_caption_ocr",
                    inputs,
                    scene,
                    SimpleNamespace(comfyui_url=self.base_url),
                    timeout=2,
                )

        self.assertIsInstance(result, list)
        self.assertEqual(result[0], "A person stands in warm local light.")
        self.assertEqual(json.loads(result[1])["labels"], ["person"])
        prompt = ComfyHandler.last_prompt
        self.assertEqual(prompt["1"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(prompt["3"]["inputs"]["task"], "more_detailed_caption")
        self.assertEqual(prompt["3"]["inputs"]["seed"], 123)

    def test_audio_stem_split_pack_uploads_audio_and_collects_four_outputs(self):
        ComfyHandler.reset(_stem_split_object_info())
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "song.wav"
            source.write_bytes(b"local wav fixture bytes")
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            inputs = SimpleNamespace(audio_ref=str(source))

            with local_only_network():
                result = runner.run_pack(
                    ROOT / "slopperly/workflows/comfy/audio_stem_split_demucs",
                    inputs,
                    SimpleNamespace(),
                    timeout=2,
                )

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 4)
        self.assertEqual([Path(path).name for path in result], [
            "slopperly_stem_bass_00001_.flac",
            "slopperly_stem_drums_00001_.flac",
            "slopperly_stem_other_00001_.flac",
            "slopperly_stem_vocals_00001_.flac",
        ])
        for path in result:
            self.assertEqual(Path(path).read_bytes(), ComfyHandler.audio_bytes)
        prompt = ComfyHandler.last_prompt
        self.assertEqual(prompt["1"]["inputs"]["audio"], "uploaded_audio.wav")
        self.assertEqual(prompt["2"]["class_type"], "AudioSeparation")
        self.assertEqual(prompt["3"]["inputs"]["audio"], ["2", 0])
        self.assertEqual(prompt["4"]["inputs"]["audio"], ["2", 1])
        self.assertEqual(prompt["5"]["inputs"]["audio"], ["2", 2])
        self.assertEqual(prompt["6"]["inputs"]["audio"], ["2", 3])
        self.assertIn(b'name="image"; filename="song.wav"', ComfyHandler.upload_bodies[0])

    def test_mmaudio_pack_uploads_video_and_collects_audio(self):
        ComfyHandler.reset(_mmaudio_object_info())
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "clip.mp4"
            destination = Path(tmp) / "mmaudio.flac"
            source.write_bytes(b"local mp4 fixture bytes")
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            inputs = SimpleNamespace(
                video_path=str(source),
                prompt="fabric movement and soft machine ambience",
                neg_prompt="speech",
                audio_length=1.5,
                steps=6,
                guidance=3.25,
                seed=135,
            )

            with local_only_network():
                result = runner.run_pack(
                    ROOT / "slopperly/workflows/comfy/mmaudio_video_to_audio",
                    inputs,
                    SimpleNamespace(mmaudio_force_offload=False),
                    destination=str(destination),
                    timeout=2,
                )

            self.assertEqual(result, str(destination))
            self.assertEqual(destination.read_bytes(), ComfyHandler.audio_bytes)
        prompt = ComfyHandler.last_prompt
        self.assertEqual(prompt["1"]["inputs"]["video"], "uploaded_video.mp4")
        self.assertEqual(prompt["2"]["inputs"]["mmaudio_model"], "mmaudio_large_44k_v2_fp16.safetensors")
        self.assertEqual(prompt["3"]["inputs"]["clip_model"], "apple_DFN5B-CLIP-ViT-H-14-384_fp16.safetensors")
        self.assertEqual(prompt["4"]["inputs"]["images"], ["1", 0])
        self.assertEqual(prompt["4"]["inputs"]["duration"], 1.5)
        self.assertEqual(prompt["4"]["inputs"]["steps"], 6)
        self.assertEqual(prompt["4"]["inputs"]["cfg"], 3.25)
        self.assertEqual(prompt["4"]["inputs"]["seed"], 135)
        self.assertEqual(prompt["4"]["inputs"]["prompt"], "fabric movement and soft machine ambience")
        self.assertEqual(prompt["4"]["inputs"]["negative_prompt"], "speech")
        self.assertFalse(prompt["4"]["inputs"]["force_offload"])
        self.assertEqual(prompt["5"]["inputs"]["audio"], ["4", 0])
        self.assertIn(b'name="video"; filename="clip.mp4"', ComfyHandler.upload_bodies[0])

    def test_stable_audio_3_pack_patches_audio_generation_graph(self):
        ComfyHandler.reset(_stable_audio_3_object_info())
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "stable_audio_3.flac"
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            inputs = SimpleNamespace(
                prompt="warm felt piano with soft drums",
                neg_prompt="speech, clipping",
                audio_length=2.5,
                steps=10,
                guidance=4.25,
                seed=777,
            )
            scene = SimpleNamespace(
                stable_audio_3_sampler="dpmpp_3m_sde",
                stable_audio_3_scheduler="karras",
                stable_audio_3_denoise=0.9,
            )

            with local_only_network():
                result = runner.run_pack(
                    ROOT / "slopperly/workflows/comfy/stable_audio_3_medium_base",
                    inputs,
                    scene,
                    destination=str(destination),
                    timeout=2,
                )

            self.assertEqual(result, str(destination))
            self.assertEqual(destination.read_bytes(), ComfyHandler.audio_bytes)

        prompt = ComfyHandler.last_prompt
        self.assertEqual(prompt["1"]["inputs"]["ckpt_name"], "stable_audio_3_medium_base.safetensors")
        self.assertEqual(prompt["2"]["inputs"]["clip_name"], "t5gemma_b_b_ul2.safetensors")
        self.assertEqual(prompt["2"]["inputs"]["type"], "stable_audio")
        self.assertEqual(prompt["3"]["inputs"]["text"], "warm felt piano with soft drums")
        self.assertEqual(prompt["4"]["inputs"]["text"], "speech, clipping")
        self.assertEqual(prompt["5"]["inputs"]["positive"], ["3", 0])
        self.assertEqual(prompt["5"]["inputs"]["negative"], ["4", 0])
        self.assertEqual(prompt["5"]["inputs"]["seconds_total"], 2.5)
        self.assertEqual(prompt["6"]["inputs"]["seconds"], 2.5)
        self.assertEqual(prompt["7"]["inputs"]["seed"], 777)
        self.assertEqual(prompt["7"]["inputs"]["steps"], 10)
        self.assertEqual(prompt["7"]["inputs"]["cfg"], 4.25)
        self.assertEqual(prompt["7"]["inputs"]["sampler_name"], "dpmpp_3m_sde")
        self.assertEqual(prompt["7"]["inputs"]["scheduler"], "karras")
        self.assertEqual(prompt["7"]["inputs"]["denoise"], 0.9)
        self.assertEqual(prompt["8"]["inputs"]["samples"], ["7", 0])
        self.assertEqual(prompt["9"]["inputs"]["audio"], ["8", 0])

    def test_ace_step_pack_patches_music_generation_graph(self):
        ComfyHandler.reset(_ace_step_object_info())
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "ace_step.flac"
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            inputs = SimpleNamespace(
                prompt="bright indie pop loop with warm bass",
                lyrics="[verse]\nlocal morning light",
                audio_length=2.5,
                steps=11,
                guidance=3.75,
                seed=24680,
                bpm=96,
                key_scale="D minor",
                time_signature="4",
            )
            scene = SimpleNamespace(
                ace_step_language="en",
                ace_step_generate_audio_codes=False,
                ace_step_aura_shift=3.25,
                ace_step_sampler="euler",
                ace_step_scheduler="simple",
                ace_step_denoise=0.95,
            )

            with local_only_network():
                result = runner.run_pack(
                    ROOT / "slopperly/workflows/comfy/ace_step_15_music",
                    inputs,
                    scene,
                    destination=str(destination),
                    timeout=2,
                )

            self.assertEqual(result, str(destination))
            self.assertEqual(destination.read_bytes(), ComfyHandler.audio_bytes)

        prompt = ComfyHandler.last_prompt
        self.assertEqual(prompt["1"]["class_type"], "UNETLoader")
        self.assertEqual(prompt["1"]["inputs"]["unet_name"], "acestep_v1.5_xl_base_bf16.safetensors")
        self.assertEqual(prompt["2"]["inputs"]["vae_name"], "ace_1.5_vae.safetensors")
        self.assertEqual(prompt["3"]["inputs"]["clip_name1"], "qwen_0.6b_ace15.safetensors")
        self.assertEqual(prompt["3"]["inputs"]["clip_name2"], "qwen_4b_ace15.safetensors")
        self.assertEqual(prompt["3"]["inputs"]["type"], "ace")
        self.assertEqual(prompt["4"]["inputs"]["tags"], "bright indie pop loop with warm bass")
        self.assertEqual(prompt["4"]["inputs"]["lyrics"], "[verse]\nlocal morning light")
        self.assertEqual(prompt["4"]["inputs"]["seed"], 24680)
        self.assertEqual(prompt["4"]["inputs"]["bpm"], 96)
        self.assertEqual(prompt["4"]["inputs"]["duration"], 2.5)
        self.assertEqual(prompt["4"]["inputs"]["timesignature"], "4")
        self.assertEqual(prompt["4"]["inputs"]["language"], "en")
        self.assertEqual(prompt["4"]["inputs"]["keyscale"], "D minor")
        self.assertFalse(prompt["4"]["inputs"]["generate_audio_codes"])
        self.assertEqual(prompt["5"]["inputs"]["conditioning"], ["4", 0])
        self.assertEqual(prompt["6"]["inputs"]["seconds"], 2.5)
        self.assertEqual(prompt["7"]["inputs"]["shift"], 3.25)
        self.assertEqual(prompt["8"]["inputs"]["model"], ["7", 0])
        self.assertEqual(prompt["8"]["inputs"]["positive"], ["4", 0])
        self.assertEqual(prompt["8"]["inputs"]["negative"], ["5", 0])
        self.assertEqual(prompt["8"]["inputs"]["latent_image"], ["6", 0])
        self.assertEqual(prompt["8"]["inputs"]["seed"], 24680)
        self.assertEqual(prompt["8"]["inputs"]["steps"], 11)
        self.assertEqual(prompt["8"]["inputs"]["cfg"], 3.75)
        self.assertEqual(prompt["8"]["inputs"]["denoise"], 0.95)
        self.assertEqual(prompt["9"]["inputs"]["samples"], ["8", 0])
        self.assertEqual(prompt["10"]["inputs"]["audio"], ["9", 0])

    def test_foundation1_pack_patches_structured_loop_generation_graph(self):
        ComfyHandler.reset(_foundation1_object_info())
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "foundation1.flac"
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            inputs = SimpleNamespace(
                prompt="clean house bass, clipped drums, bright stab, avoid speech",
                steps=14,
                seed=13579,
                foundation1_bpm="100 BPM",
                foundation1_bars="4 Bars",
                foundation1_key="D minor",
            )
            scene = SimpleNamespace(
                foundation1_cfg_scale=6.75,
                foundation1_sampler_type="k-heun",
                foundation1_sigma_min=0.25,
                foundation1_sigma_max=480.0,
                foundation1_unload_after_generate=True,
                foundation1_torch_compile=False,
                foundation1_init_noise_level=0.6,
            )

            with local_only_network():
                result = runner.run_pack(
                    ROOT / "slopperly/workflows/comfy/foundation1_music_loop",
                    inputs,
                    scene,
                    destination=str(destination),
                    timeout=2,
                )

            self.assertEqual(result, str(destination))
            self.assertEqual(destination.read_bytes(), ComfyHandler.audio_bytes)

        prompt = ComfyHandler.last_prompt
        self.assertEqual(prompt["1"]["class_type"], "Foundation1ModelLoader")
        self.assertEqual(prompt["1"]["inputs"]["model"], "Foundation-1/Foundation_1.safetensors")
        self.assertEqual(prompt["1"]["inputs"]["attention"], "auto")
        self.assertEqual(prompt["2"]["class_type"], "Foundation1Generate")
        self.assertEqual(prompt["2"]["inputs"]["model"], ["1", 0])
        self.assertEqual(prompt["2"]["inputs"]["tags"], "clean house bass, clipped drums, bright stab, avoid speech")
        self.assertEqual(prompt["2"]["inputs"]["bpm"], "100 BPM")
        self.assertEqual(prompt["2"]["inputs"]["bars"], "4 Bars")
        self.assertEqual(prompt["2"]["inputs"]["key"], "D minor")
        self.assertEqual(prompt["2"]["inputs"]["steps"], 14)
        self.assertEqual(prompt["2"]["inputs"]["cfg_scale"], 6.75)
        self.assertEqual(prompt["2"]["inputs"]["seed"], 13579)
        self.assertEqual(prompt["2"]["inputs"]["sampler_type"], "k-heun")
        self.assertEqual(prompt["2"]["inputs"]["sigma_min"], 0.25)
        self.assertEqual(prompt["2"]["inputs"]["sigma_max"], 480.0)
        self.assertTrue(prompt["2"]["inputs"]["unload_after_generate"])
        self.assertFalse(prompt["2"]["inputs"]["torch_compile"])
        self.assertEqual(prompt["2"]["inputs"]["init_noise_level"], 0.6)
        self.assertEqual(prompt["3"]["inputs"]["audio"], ["2", 0])

    def test_chatterbox_reference_tts_pack_uploads_audio_and_patches_graph(self):
        ComfyHandler.reset(_chatterbox_object_info("chatterbox_tts_vc_comfy"))
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "speaker.wav"
            destination = Path(tmp) / "chatterbox.flac"
            source.write_bytes(b"local wav fixture bytes")
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            inputs = SimpleNamespace(
                prompt="local reference speech",
                audio_ref=str(source),
                exaggeration=0.6,
                pace=0.4,
                temperature=0.7,
                seed=24601,
            )

            with local_only_network():
                result = runner.run_pack(
                    ROOT / "slopperly/workflows/comfy/chatterbox_tts_vc_comfy",
                    inputs,
                    SimpleNamespace(chatterbox_keep_model_loaded=True),
                    destination=str(destination),
                    timeout=2,
                )

            self.assertEqual(result, str(destination))
            self.assertEqual(destination.read_bytes(), ComfyHandler.audio_bytes)

        prompt = ComfyHandler.last_prompt
        self.assertEqual(prompt["1"]["class_type"], "LoadAudio")
        self.assertEqual(prompt["1"]["inputs"]["audio"], "uploaded_audio.wav")
        self.assertEqual(prompt["2"]["class_type"], "FL_ChatterboxTTS")
        self.assertEqual(prompt["2"]["inputs"]["audio_prompt"], ["1", 0])
        self.assertEqual(prompt["2"]["inputs"]["text"], "local reference speech")
        self.assertEqual(prompt["2"]["inputs"]["exaggeration"], 0.6)
        self.assertEqual(prompt["2"]["inputs"]["cfg_weight"], 0.4)
        self.assertEqual(prompt["2"]["inputs"]["temperature"], 0.7)
        self.assertEqual(prompt["2"]["inputs"]["seed"], 24601)
        self.assertTrue(prompt["2"]["inputs"]["keep_model_loaded"])
        self.assertEqual(prompt["3"]["inputs"]["audio"], ["2", 0])
        self.assertIn(b'name="image"; filename="speaker.wav"', ComfyHandler.upload_bodies[0])

    def test_chatterbox_vc_pack_uses_single_legacy_audio_for_both_inputs(self):
        ComfyHandler.reset(_chatterbox_object_info("chatterbox_vc_comfy"))
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.wav"
            destination = Path(tmp) / "chatterbox_vc.flac"
            source.write_bytes(b"local wav fixture bytes")
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            inputs = SimpleNamespace(audio_ref=str(source), seed=1357)

            with local_only_network():
                result = runner.run_pack(
                    ROOT / "slopperly/workflows/comfy/chatterbox_vc_comfy",
                    inputs,
                    SimpleNamespace(),
                    destination=str(destination),
                    timeout=2,
                )

            self.assertEqual(result, str(destination))
            self.assertEqual(destination.read_bytes(), ComfyHandler.audio_bytes)

        prompt = ComfyHandler.last_prompt
        self.assertEqual(prompt["1"]["inputs"]["audio"], "uploaded_audio.wav")
        self.assertEqual(prompt["2"]["class_type"], "FL_ChatterboxVC")
        self.assertEqual(prompt["2"]["inputs"]["input_audio"], ["1", 0])
        self.assertEqual(prompt["2"]["inputs"]["target_voice"], ["1", 0])
        self.assertEqual(prompt["2"]["inputs"]["seed"], 1357)
        self.assertEqual(prompt["3"]["inputs"]["audio"], ["2", 0])

    def test_chatterbox_turbo_reference_pack_uploads_audio_and_patches_graph(self):
        ComfyHandler.reset(_chatterbox_object_info("chatterbox_turbo_ref_tts_comfy"))
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "speaker.wav"
            destination = Path(tmp) / "chatterbox_turbo.flac"
            source.write_bytes(b"local wav fixture bytes")
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            inputs = SimpleNamespace(
                prompt="local turbo reference speech",
                audio_ref=str(source),
                temperature=0.7,
                seed=24602,
            )

            with local_only_network():
                result = runner.run_pack(
                    ROOT / "slopperly/workflows/comfy/chatterbox_turbo_ref_tts_comfy",
                    inputs,
                    SimpleNamespace(chatterbox_turbo_top_k=321),
                    destination=str(destination),
                    timeout=2,
                )

            self.assertEqual(result, str(destination))
            self.assertEqual(destination.read_bytes(), ComfyHandler.audio_bytes)

        prompt = ComfyHandler.last_prompt
        self.assertEqual(prompt["1"]["inputs"]["audio"], "uploaded_audio.wav")
        self.assertEqual(prompt["2"]["class_type"], "FL_ChatterboxTurboTTS")
        self.assertEqual(prompt["2"]["inputs"]["audio_prompt"], ["1", 0])
        self.assertEqual(prompt["2"]["inputs"]["text"], "local turbo reference speech")
        self.assertEqual(prompt["2"]["inputs"]["temperature"], 0.7)
        self.assertEqual(prompt["2"]["inputs"]["top_k"], 321)
        self.assertEqual(prompt["2"]["inputs"]["seed"], 24602)
        self.assertEqual(prompt["3"]["inputs"]["audio"], ["2", 0])

    def test_chatterbox_multilingual_reference_pack_uploads_audio_and_patches_graph(self):
        ComfyHandler.reset(_chatterbox_object_info("chatterbox_multilingual_ref_tts_comfy"))
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "speaker.wav"
            destination = Path(tmp) / "chatterbox_multilingual.flac"
            source.write_bytes(b"local wav fixture bytes")
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            inputs = SimpleNamespace(
                prompt="local multilingual reference speech",
                audio_ref=str(source),
                chatterbox_mtl_language="Spanish (es)",
                exaggeration=0.6,
                pace=0.4,
                temperature=0.75,
                seed=24603,
            )

            with local_only_network():
                result = runner.run_pack(
                    ROOT / "slopperly/workflows/comfy/chatterbox_multilingual_ref_tts_comfy",
                    inputs,
                    SimpleNamespace(chatterbox_multilingual_top_p=0.91),
                    destination=str(destination),
                    timeout=2,
                )

            self.assertEqual(result, str(destination))
            self.assertEqual(destination.read_bytes(), ComfyHandler.audio_bytes)

        prompt = ComfyHandler.last_prompt
        self.assertEqual(prompt["1"]["inputs"]["audio"], "uploaded_audio.wav")
        self.assertEqual(prompt["2"]["class_type"], "FL_ChatterboxMultilingualTTS")
        self.assertEqual(prompt["2"]["inputs"]["audio_prompt"], ["1", 0])
        self.assertEqual(prompt["2"]["inputs"]["text"], "local multilingual reference speech")
        self.assertEqual(prompt["2"]["inputs"]["language"], "Spanish (es)")
        self.assertEqual(prompt["2"]["inputs"]["exaggeration"], 0.6)
        self.assertEqual(prompt["2"]["inputs"]["cfg_weight"], 0.4)
        self.assertEqual(prompt["2"]["inputs"]["temperature"], 0.75)
        self.assertEqual(prompt["2"]["inputs"]["top_p"], 0.91)
        self.assertEqual(prompt["2"]["inputs"]["seed"], 24603)
        self.assertEqual(prompt["3"]["inputs"]["audio"], ["2", 0])

    def test_omnigen_pack_uploads_references_and_prunes_empty_slots(self):
        ComfyHandler.reset(_omnigen_object_info())
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.png"
            second = Path(tmp) / "second.png"
            destination = Path(tmp) / "omnigen.png"
            first.write_bytes(b"first local image")
            second.write_bytes(b"second local image")
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            inputs = SimpleNamespace(
                prompt="combine image_1 and image_2 into one local test image",
                images=[str(first), str(second), None],
                width=640,
                height=512,
                steps=9,
                guidance=3.25,
                seed=2026,
                omnigen_img_guidance_scale=1.7,
                omnigen_use_input_image_size_as_output=False,
                omnigen_model_precision="Auto",
                omnigen_memory_management="Memory Priority",
                omnigen_separate_cfg_infer=True,
                omnigen_max_input_image_size=768,
            )

            with local_only_network():
                result = runner.run_pack(
                    ROOT / "slopperly/workflows/comfy/omnigen_v1_multi_image",
                    inputs,
                    SimpleNamespace(),
                    destination=str(destination),
                    timeout=2,
                )

            self.assertEqual(result, str(destination))
            self.assertEqual(destination.read_bytes(), ComfyHandler.image_bytes)

        prompt = ComfyHandler.last_prompt
        self.assertEqual(len(ComfyHandler.upload_bodies), 2)
        self.assertEqual(prompt["1"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(prompt["2"]["inputs"]["image"], "uploaded_source_2.png")
        self.assertNotIn("3", prompt)
        self.assertEqual(prompt["4"]["class_type"], "ailab_OmniGen")
        self.assertEqual(prompt["4"]["inputs"]["image_1"], ["1", 0])
        self.assertEqual(prompt["4"]["inputs"]["image_2"], ["2", 0])
        self.assertNotIn("image_3", prompt["4"]["inputs"])
        self.assertEqual(prompt["4"]["inputs"]["prompt"], "combine image_1 and image_2 into one local test image")
        self.assertEqual(prompt["4"]["inputs"]["width"], 640)
        self.assertEqual(prompt["4"]["inputs"]["height"], 512)
        self.assertEqual(prompt["4"]["inputs"]["num_inference_steps"], 9)
        self.assertEqual(prompt["4"]["inputs"]["guidance_scale"], 3.25)
        self.assertEqual(prompt["4"]["inputs"]["img_guidance_scale"], 1.7)
        self.assertFalse(prompt["4"]["inputs"]["use_input_image_size_as_output"])
        self.assertEqual(prompt["4"]["inputs"]["max_input_image_size"], 768)
        self.assertIn(b'filename="first.png"', ComfyHandler.upload_bodies[0])
        self.assertIn(b'filename="second.png"', ComfyHandler.upload_bodies[1])

    def test_qwen_image_edit_pack_uploads_references_and_prunes_empty_slots(self):
        ComfyHandler.reset(_qwen_image_edit_object_info())
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.png"
            second = Path(tmp) / "second.png"
            destination = Path(tmp) / "qwen_edit.png"
            first.write_bytes(b"first local image")
            second.write_bytes(b"second local image")
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            inputs = SimpleNamespace(
                prompt="make the first object warmer using the second material",
                neg_prompt="text, watermark",
                images=[str(first), str(second), None],
                width=1024,
                height=1024,
                steps=4,
                seed=2511,
                qwen_image_edit_cfg=1.0,
                qwen_image_edit_sampler="euler",
                qwen_image_edit_scheduler="simple",
                qwen_image_edit_denoise=1.0,
                qwen_image_edit_model="qwen-image-edit-2511-Q5_K_M.gguf",
                qwen_image_edit_text_encoder="qwen_2.5_vl_7b_fp8_scaled.safetensors",
                qwen_image_edit_vae="qwen_image_vae.safetensors",
                qwen_image_edit_lightning_lora=(
                    "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"
                ),
                qwen_image_edit_lora_strength=1.0,
            )

            with local_only_network():
                result = runner.run_pack(
                    ROOT / "slopperly/workflows/comfy/qwen_image_edit_2511_multi_gguf",
                    inputs,
                    SimpleNamespace(),
                    destination=str(destination),
                    timeout=2,
                )

            self.assertEqual(result, str(destination))
            self.assertEqual(destination.read_bytes(), ComfyHandler.image_bytes)

        prompt = ComfyHandler.last_prompt
        self.assertEqual(len(ComfyHandler.upload_bodies), 2)
        self.assertEqual(prompt["6"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(prompt["9"]["inputs"]["image"], "uploaded_source_2.png")
        self.assertNotIn("10", prompt)
        self.assertEqual(prompt["1"]["inputs"]["unet_name"], "qwen-image-edit-2511-Q5_K_M.gguf")
        self.assertEqual(prompt["3"]["inputs"]["lora_name"], "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors")
        self.assertEqual(prompt["4"]["inputs"]["clip_name"], "qwen_2.5_vl_7b_fp8_scaled.safetensors")
        self.assertEqual(prompt["5"]["inputs"]["vae_name"], "qwen_image_vae.safetensors")
        self.assertEqual(prompt["7"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["7"]["inputs"]["height"], 1024)
        self.assertEqual(prompt["11"]["inputs"]["prompt"], "text, watermark")
        self.assertEqual(
            prompt["12"]["inputs"]["prompt"],
            "make the first object warmer using the second material",
        )
        self.assertEqual(prompt["16"]["inputs"]["seed"], 2511)
        self.assertEqual(prompt["16"]["inputs"]["steps"], 4)
        self.assertEqual(prompt["16"]["inputs"]["cfg"], 1.0)
        self.assertNotIn("image3", prompt["11"]["inputs"])
        self.assertNotIn("image3", prompt["12"]["inputs"])
        self.assertIn(b'filename="first.png"', ComfyHandler.upload_bodies[0])
        self.assertIn(b'filename="second.png"', ComfyHandler.upload_bodies[1])

    def test_qwen_image_t2i_pack_patches_api_workflow(self):
        ComfyHandler.reset(_qwen_image_object_info("qwen_image_2512_t2i_gguf"))
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "qwen_image.png"
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            inputs = SimpleNamespace(
                prompt="local Qwen Image text to image",
                neg_prompt="text, watermark",
                width=1024,
                height=1024,
                steps=4,
                seed=2512,
                qwen_image_cfg=1.0,
                qwen_image_sampler="euler",
                qwen_image_scheduler="simple",
                qwen_image_denoise=1.0,
                qwen_image_model="qwen-image-2512-Q5_K_M.gguf",
                qwen_image_text_encoder="qwen_2.5_vl_7b_fp8_scaled.safetensors",
                qwen_image_vae="qwen_image_vae.safetensors",
                qwen_image_lightning_lora=(
                    "Qwen-Image-2512-Lightning-4steps-V1.0-bf16.safetensors"
                ),
                qwen_image_lora_strength=1.0,
            )

            with local_only_network():
                result = runner.run_pack(
                    ROOT / "slopperly/workflows/comfy/qwen_image_2512_t2i_gguf",
                    inputs,
                    SimpleNamespace(),
                    destination=str(destination),
                    timeout=2,
                )

            self.assertEqual(result, str(destination))
            self.assertEqual(destination.read_bytes(), ComfyHandler.image_bytes)

        prompt = ComfyHandler.last_prompt
        self.assertEqual(ComfyHandler.upload_bodies, [])
        self.assertEqual(prompt["1"]["inputs"]["unet_name"], "qwen-image-2512-Q5_K_M.gguf")
        self.assertEqual(prompt["2"]["inputs"]["lora_name"], "Qwen-Image-2512-Lightning-4steps-V1.0-bf16.safetensors")
        self.assertEqual(prompt["4"]["inputs"]["clip_name"], "qwen_2.5_vl_7b_fp8_scaled.safetensors")
        self.assertEqual(prompt["5"]["inputs"]["vae_name"], "qwen_image_vae.safetensors")
        self.assertEqual(prompt["6"]["inputs"]["text"], "local Qwen Image text to image")
        self.assertEqual(prompt["7"]["inputs"]["text"], "text, watermark")
        self.assertEqual(prompt["8"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["8"]["inputs"]["height"], 1024)
        self.assertEqual(prompt["9"]["inputs"]["seed"], 2512)
        self.assertEqual(prompt["9"]["inputs"]["steps"], 4)
        self.assertEqual(prompt["9"]["inputs"]["cfg"], 1.0)
        self.assertEqual(prompt["9"]["inputs"]["denoise"], 1.0)

    def test_qwen_image_i2i_pack_uploads_image_and_patches_denoise(self):
        ComfyHandler.reset(_qwen_image_object_info("qwen_image_2512_i2i_gguf"))
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            destination = Path(tmp) / "qwen_image_i2i.png"
            source.write_bytes(b"local source image")
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            inputs = SimpleNamespace(
                prompt="local Qwen Image image to image",
                neg_prompt="text, watermark",
                image=str(source),
                width=1024,
                height=1024,
                steps=4,
                seed=2513,
                qwen_image_cfg=1.0,
                qwen_image_sampler="euler",
                qwen_image_scheduler="simple",
                qwen_image_denoise=0.35,
                qwen_image_model="qwen-image-2512-Q5_K_M.gguf",
                qwen_image_text_encoder="qwen_2.5_vl_7b_fp8_scaled.safetensors",
                qwen_image_vae="qwen_image_vae.safetensors",
                qwen_image_lightning_lora=(
                    "Qwen-Image-2512-Lightning-4steps-V1.0-bf16.safetensors"
                ),
                qwen_image_lora_strength=1.0,
            )

            with local_only_network():
                result = runner.run_pack(
                    ROOT / "slopperly/workflows/comfy/qwen_image_2512_i2i_gguf",
                    inputs,
                    SimpleNamespace(),
                    destination=str(destination),
                    timeout=2,
                )

            self.assertEqual(result, str(destination))
            self.assertEqual(destination.read_bytes(), ComfyHandler.image_bytes)

        prompt = ComfyHandler.last_prompt
        self.assertEqual(len(ComfyHandler.upload_bodies), 1)
        self.assertEqual(prompt["8"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(prompt["9"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["9"]["inputs"]["height"], 1024)
        self.assertEqual(prompt["11"]["inputs"]["seed"], 2513)
        self.assertEqual(prompt["11"]["inputs"]["steps"], 4)
        self.assertEqual(prompt["11"]["inputs"]["cfg"], 1.0)
        self.assertEqual(prompt["11"]["inputs"]["denoise"], 0.35)
        self.assertIn(b'filename="source.png"', ComfyHandler.upload_bodies[0])

    def test_zimage_base_packs_patch_t2i_and_i2i_graphs(self):
        ComfyHandler.reset(_zimage_object_info("zimage_t2i_i2i"))
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "zimage.png"
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            inputs = SimpleNamespace(
                prompt="local Z-Image text to image",
                neg_prompt="text, watermark",
                width=1024,
                height=1024,
                steps=30,
                seed=1201,
                zimage_cfg=7.0,
                zimage_sampler="res_multistep",
                zimage_scheduler="simple",
                zimage_denoise=1.0,
                zimage_model="z_image_bf16.safetensors",
                zimage_text_encoder="qwen_3_4b.safetensors",
                zimage_vae="ae.safetensors",
            )

            with local_only_network():
                result = runner.run_pack(
                    ROOT / "slopperly/workflows/comfy/zimage_t2i_i2i",
                    inputs,
                    SimpleNamespace(),
                    destination=str(destination),
                    timeout=2,
                )

            self.assertEqual(result, str(destination))
            self.assertEqual(destination.read_bytes(), ComfyHandler.image_bytes)

        prompt = ComfyHandler.last_prompt
        self.assertEqual(ComfyHandler.upload_bodies, [])
        self.assertEqual(prompt["1"]["inputs"]["unet_name"], "z_image_bf16.safetensors")
        self.assertEqual(prompt["3"]["inputs"]["clip_name"], "qwen_3_4b.safetensors")
        self.assertEqual(prompt["3"]["inputs"]["type"], "lumina2")
        self.assertEqual(prompt["4"]["inputs"]["vae_name"], "ae.safetensors")
        self.assertEqual(prompt["5"]["inputs"]["text"], "local Z-Image text to image")
        self.assertEqual(prompt["6"]["inputs"]["text"], "text, watermark")
        self.assertEqual(prompt["7"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["8"]["inputs"]["seed"], 1201)
        self.assertEqual(prompt["8"]["inputs"]["steps"], 30)
        self.assertEqual(prompt["8"]["inputs"]["cfg"], 7.0)
        self.assertEqual(prompt["8"]["inputs"]["sampler_name"], "res_multistep")

        ComfyHandler.reset(_zimage_object_info("zimage_t2i_i2i_img2img"))
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            destination = Path(tmp) / "zimage_i2i.png"
            source.write_bytes(b"local source image")
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            inputs.image = str(source)
            inputs.seed = 1202
            inputs.zimage_denoise = 0.35

            with local_only_network():
                result = runner.run_pack(
                    ROOT / "slopperly/workflows/comfy/zimage_t2i_i2i_img2img",
                    inputs,
                    SimpleNamespace(),
                    destination=str(destination),
                    timeout=2,
                )

            self.assertEqual(result, str(destination))
            self.assertEqual(destination.read_bytes(), ComfyHandler.image_bytes)

        prompt = ComfyHandler.last_prompt
        self.assertEqual(len(ComfyHandler.upload_bodies), 1)
        self.assertEqual(prompt["7"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(prompt["8"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["8"]["inputs"]["height"], 1024)
        self.assertEqual(prompt["10"]["inputs"]["seed"], 1202)
        self.assertEqual(prompt["10"]["inputs"]["steps"], 30)
        self.assertEqual(prompt["10"]["inputs"]["cfg"], 7.0)
        self.assertEqual(prompt["10"]["inputs"]["denoise"], 0.35)
        self.assertIn(b'filename="source.png"', ComfyHandler.upload_bodies[0])

    def test_zimage_turbo_packs_patch_t2i_and_i2i_graphs(self):
        ComfyHandler.reset(_zimage_object_info("zimage_turbo_t2i_i2i"))
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "zimage_turbo.png"
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            inputs = SimpleNamespace(
                prompt="local Z-Image Turbo text to image",
                neg_prompt="ignored by official turbo graph",
                width=1024,
                height=1024,
                steps=8,
                seed=1301,
                zimage_cfg=1.0,
                zimage_sampler="res_multistep",
                zimage_scheduler="simple",
                zimage_denoise=1.0,
                zimage_model="z_image_turbo_bf16.safetensors",
                zimage_text_encoder="qwen_3_4b.safetensors",
                zimage_vae="ae.safetensors",
            )

            with local_only_network():
                result = runner.run_pack(
                    ROOT / "slopperly/workflows/comfy/zimage_turbo_t2i_i2i",
                    inputs,
                    SimpleNamespace(),
                    destination=str(destination),
                    timeout=2,
                )

            self.assertEqual(result, str(destination))
            self.assertEqual(destination.read_bytes(), ComfyHandler.image_bytes)

        prompt = ComfyHandler.last_prompt
        self.assertEqual(ComfyHandler.upload_bodies, [])
        self.assertEqual(prompt["1"]["inputs"]["unet_name"], "z_image_turbo_bf16.safetensors")
        self.assertEqual(prompt["5"]["inputs"]["text"], "local Z-Image Turbo text to image")
        self.assertEqual(prompt["6"]["class_type"], "ConditioningZeroOut")
        self.assertEqual(prompt["8"]["inputs"]["cfg"], 1.0)
        self.assertEqual(prompt["8"]["inputs"]["steps"], 8)
        self.assertEqual(prompt["8"]["inputs"]["sampler_name"], "res_multistep")

        ComfyHandler.reset(_zimage_object_info("zimage_turbo_t2i_i2i_img2img"))
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            destination = Path(tmp) / "zimage_turbo_i2i.png"
            source.write_bytes(b"local source image")
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            inputs.image = str(source)
            inputs.seed = 1302
            inputs.zimage_denoise = 0.35

            with local_only_network():
                result = runner.run_pack(
                    ROOT / "slopperly/workflows/comfy/zimage_turbo_t2i_i2i_img2img",
                    inputs,
                    SimpleNamespace(),
                    destination=str(destination),
                    timeout=2,
                )

            self.assertEqual(result, str(destination))
            self.assertEqual(destination.read_bytes(), ComfyHandler.image_bytes)

        prompt = ComfyHandler.last_prompt
        self.assertEqual(len(ComfyHandler.upload_bodies), 1)
        self.assertEqual(prompt["7"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(prompt["8"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["10"]["inputs"]["seed"], 1302)
        self.assertEqual(prompt["10"]["inputs"]["steps"], 8)
        self.assertEqual(prompt["10"]["inputs"]["cfg"], 1.0)
        self.assertEqual(prompt["10"]["inputs"]["denoise"], 0.35)
        self.assertIn(b'filename="source.png"', ComfyHandler.upload_bodies[0])

    def test_anima_packs_patch_t2i_and_i2i_graphs(self):
        ComfyHandler.reset(_anima_object_info("anima_t2i_i2i"))
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "anima.png"
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            inputs = SimpleNamespace(
                prompt="local Anima text to image",
                neg_prompt="blur",
                width=1024,
                height=1024,
                steps=25,
                guidance=4.0,
                seed=2401,
                anima_model="anima-preview3-base.safetensors",
                anima_text_encoder="qwen_3_06b_base.safetensors",
                anima_clip_type="stable_diffusion",
                anima_vae="qwen_image_vae.safetensors",
                anima_sampler="er_sde",
                anima_scheduler="simple",
                anima_denoise=1.0,
            )

            with local_only_network():
                result = runner.run_pack(
                    ROOT / "slopperly/workflows/comfy/anima_t2i_i2i",
                    inputs,
                    SimpleNamespace(),
                    destination=str(destination),
                    timeout=2,
                )

            self.assertEqual(result, str(destination))
            self.assertEqual(destination.read_bytes(), ComfyHandler.image_bytes)

        prompt = ComfyHandler.last_prompt
        self.assertEqual(ComfyHandler.upload_bodies, [])
        self.assertEqual(prompt["1"]["inputs"]["unet_name"], "anima-preview3-base.safetensors")
        self.assertEqual(prompt["2"]["inputs"]["clip_name"], "qwen_3_06b_base.safetensors")
        self.assertEqual(prompt["2"]["inputs"]["type"], "stable_diffusion")
        self.assertEqual(prompt["3"]["inputs"]["vae_name"], "qwen_image_vae.safetensors")
        self.assertEqual(prompt["4"]["inputs"]["text"], "local Anima text to image")
        self.assertEqual(prompt["5"]["inputs"]["text"], "blur")
        self.assertEqual(prompt["6"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["6"]["inputs"]["height"], 1024)
        self.assertEqual(prompt["7"]["inputs"]["seed"], 2401)
        self.assertEqual(prompt["7"]["inputs"]["steps"], 25)
        self.assertEqual(prompt["7"]["inputs"]["cfg"], 4.0)
        self.assertEqual(prompt["7"]["inputs"]["sampler_name"], "er_sde")
        self.assertEqual(prompt["7"]["inputs"]["scheduler"], "simple")

        ComfyHandler.reset(_anima_object_info("anima_t2i_i2i_img2img"))
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            destination = Path(tmp) / "anima_i2i.png"
            source.write_bytes(b"local source image")
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            inputs.image = str(source)
            inputs.prompt = "local Anima image to image"
            inputs.seed = 2402
            inputs.anima_denoise = 0.35

            with local_only_network():
                result = runner.run_pack(
                    ROOT / "slopperly/workflows/comfy/anima_t2i_i2i_img2img",
                    inputs,
                    SimpleNamespace(),
                    destination=str(destination),
                    timeout=2,
                )

            self.assertEqual(result, str(destination))
            self.assertEqual(destination.read_bytes(), ComfyHandler.image_bytes)

        prompt = ComfyHandler.last_prompt
        self.assertEqual(len(ComfyHandler.upload_bodies), 1)
        self.assertEqual(prompt["4"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(prompt["5"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["5"]["inputs"]["height"], 1024)
        self.assertEqual(prompt["7"]["inputs"]["text"], "local Anima image to image")
        self.assertEqual(prompt["8"]["inputs"]["text"], "blur")
        self.assertEqual(prompt["9"]["inputs"]["seed"], 2402)
        self.assertEqual(prompt["9"]["inputs"]["steps"], 25)
        self.assertEqual(prompt["9"]["inputs"]["cfg"], 4.0)
        self.assertEqual(prompt["9"]["inputs"]["sampler_name"], "er_sde")
        self.assertEqual(prompt["9"]["inputs"]["scheduler"], "simple")
        self.assertAlmostEqual(prompt["9"]["inputs"]["denoise"], 0.35)
        self.assertIn(b'filename="source.png"', ComfyHandler.upload_bodies[0])

    def test_ernie_packs_patch_base_and_turbo_graphs(self):
        ComfyHandler.reset(_ernie_object_info("ernie_image_t2i"))
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "ernie.png"
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            sampling = {
                "sampling_mode": "on",
                "temperature": 0.6,
                "top_k": 64,
                "top_p": 0.8,
                "min_p": 0.05,
                "repetition_penalty": 1.05,
                "presence_penalty": 0.0,
                "seed": 3101,
            }
            inputs = SimpleNamespace(
                neg_prompt="text, watermark",
                width=1024,
                height=1024,
                batch=1,
                steps=50,
                guidance=4.0,
                seed=3101,
                ernie_model="ernie-image.safetensors",
                ernie_text_encoder="ministral-3-3b.safetensors",
                ernie_prompt_enhancer="ernie-image-prompt-enhancer.safetensors",
                ernie_clip_type="flux2",
                ernie_vae="flux2-vae.safetensors",
                ernie_sampler="euler",
                ernie_scheduler="simple",
                ernie_denoise=1.0,
                ernie_prompt_request="enhance local ERNIE base prompt",
                ernie_textgen_max_length=2048,
                ernie_textgen_sampling_mode=sampling,
                ernie_textgen_thinking=False,
                ernie_textgen_use_default_template=True,
            )

            with local_only_network():
                result = runner.run_pack(
                    ROOT / "slopperly/workflows/comfy/ernie_image_t2i",
                    inputs,
                    SimpleNamespace(),
                    destination=str(destination),
                    timeout=2,
                )

            self.assertEqual(result, str(destination))
            self.assertEqual(destination.read_bytes(), ComfyHandler.image_bytes)

        prompt = ComfyHandler.last_prompt
        self.assertEqual(ComfyHandler.upload_bodies, [])
        self.assertEqual(prompt["1"]["inputs"]["unet_name"], "ernie-image.safetensors")
        self.assertEqual(prompt["2"]["inputs"]["clip_name"], "ministral-3-3b.safetensors")
        self.assertEqual(prompt["2"]["inputs"]["type"], "flux2")
        self.assertEqual(prompt["3"]["inputs"]["vae_name"], "flux2-vae.safetensors")
        self.assertEqual(prompt["4"]["inputs"]["clip_name"], "ernie-image-prompt-enhancer.safetensors")
        self.assertEqual(prompt["5"]["inputs"]["prompt"], "enhance local ERNIE base prompt")
        self.assertEqual(prompt["5"]["inputs"]["sampling_mode"], sampling)
        self.assertEqual(prompt["6"]["inputs"]["text"], ["5", 0])
        self.assertEqual(prompt["7"]["inputs"]["text"], "text, watermark")
        self.assertEqual(prompt["8"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["8"]["inputs"]["height"], 1024)
        self.assertEqual(prompt["8"]["inputs"]["batch_size"], 1)
        self.assertEqual(prompt["9"]["inputs"]["seed"], 3101)
        self.assertEqual(prompt["9"]["inputs"]["steps"], 50)
        self.assertEqual(prompt["9"]["inputs"]["cfg"], 4.0)
        self.assertEqual(prompt["9"]["inputs"]["sampler_name"], "euler")
        self.assertEqual(prompt["9"]["inputs"]["scheduler"], "simple")

        ComfyHandler.reset(_ernie_object_info("ernie_image_turbo_t2i"))
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "ernie_turbo.png"
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            inputs.ernie_model = "ernie-image-turbo.safetensors"
            inputs.ernie_prompt_request = "enhance local ERNIE turbo prompt"
            inputs.seed = 3201
            inputs.steps = 8
            inputs.guidance = 1.0
            inputs.ernie_textgen_sampling_mode = {**sampling, "seed": 3201}

            with local_only_network():
                result = runner.run_pack(
                    ROOT / "slopperly/workflows/comfy/ernie_image_turbo_t2i",
                    inputs,
                    SimpleNamespace(),
                    destination=str(destination),
                    timeout=2,
                )

            self.assertEqual(result, str(destination))
            self.assertEqual(destination.read_bytes(), ComfyHandler.image_bytes)

        prompt = ComfyHandler.last_prompt
        self.assertEqual(prompt["1"]["inputs"]["unet_name"], "ernie-image-turbo.safetensors")
        self.assertEqual(prompt["5"]["inputs"]["prompt"], "enhance local ERNIE turbo prompt")
        self.assertEqual(prompt["5"]["inputs"]["sampling_mode"]["seed"], 3201)
        self.assertEqual(prompt["7"]["class_type"], "ConditioningZeroOut")
        self.assertEqual(prompt["7"]["inputs"]["conditioning"], ["6", 0])
        self.assertEqual(prompt["9"]["inputs"]["seed"], 3201)
        self.assertEqual(prompt["9"]["inputs"]["steps"], 8)
        self.assertEqual(prompt["9"]["inputs"]["cfg"], 1.0)

    def test_krea2_packs_patch_base_and_turbo_graphs(self):
        ComfyHandler.reset(_krea_object_info("krea2_base_t2i"))
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "krea2_base.png"
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            sampling = {
                "sampling_mode": "on",
                "temperature": 0.7,
                "top_k": 64,
                "top_p": 0.95,
                "min_p": 0.05,
                "repetition_penalty": 1.05,
                "presence_penalty": 0.0,
                "seed": 4101,
            }
            inputs = SimpleNamespace(
                neg_prompt="text, watermark",
                width=1024,
                height=1024,
                batch=1,
                seed=4101,
                krea_model="krea2_raw_fp8_scaled.safetensors",
                krea_text_encoder="qwen3vl_4b_fp8_scaled.safetensors",
                krea_clip_type="krea2",
                krea_vae="qwen_image_vae.safetensors",
                krea_sampler="euler",
                krea_scheduler="simple",
                krea_denoise=1.0,
                krea_steps=28,
                krea_guidance=4.5,
                krea_prompt_request="enhance local Krea base prompt",
                krea_textgen_max_length=512,
                krea_textgen_sampling_mode=sampling,
                krea_textgen_thinking=False,
                krea_textgen_use_default_template=True,
            )

            with local_only_network():
                result = runner.run_pack(
                    ROOT / "slopperly/workflows/comfy/krea2_base_t2i",
                    inputs,
                    SimpleNamespace(),
                    destination=str(destination),
                    timeout=2,
                )

            self.assertEqual(result, str(destination))
            self.assertEqual(destination.read_bytes(), ComfyHandler.image_bytes)

        prompt = ComfyHandler.last_prompt
        self.assertEqual(ComfyHandler.upload_bodies, [])
        self.assertEqual(prompt["1"]["inputs"]["unet_name"], "krea2_raw_fp8_scaled.safetensors")
        self.assertEqual(prompt["2"]["inputs"]["clip_name"], "qwen3vl_4b_fp8_scaled.safetensors")
        self.assertEqual(prompt["2"]["inputs"]["type"], "krea2")
        self.assertEqual(prompt["3"]["inputs"]["vae_name"], "qwen_image_vae.safetensors")
        self.assertEqual(prompt["4"]["inputs"]["prompt"], "enhance local Krea base prompt")
        self.assertEqual(prompt["4"]["inputs"]["sampling_mode"], sampling)
        self.assertEqual(prompt["5"]["inputs"]["text"], ["4", 0])
        self.assertEqual(prompt["6"]["inputs"]["text"], "text, watermark")
        self.assertEqual(prompt["7"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["7"]["inputs"]["height"], 1024)
        self.assertEqual(prompt["8"]["inputs"]["seed"], 4101)
        self.assertEqual(prompt["8"]["inputs"]["steps"], 28)
        self.assertEqual(prompt["8"]["inputs"]["cfg"], 4.5)
        self.assertEqual(prompt["8"]["inputs"]["sampler_name"], "euler")
        self.assertEqual(prompt["8"]["inputs"]["scheduler"], "simple")

        ComfyHandler.reset(_krea_object_info("krea2_turbo_t2i"))
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "krea2_turbo.png"
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            inputs.krea_model = "krea2_turbo_fp8_scaled.safetensors"
            inputs.krea_prompt_request = "enhance local Krea Turbo prompt"
            inputs.seed = 4201
            inputs.krea_steps = 8
            inputs.krea_guidance = 1.0
            inputs.krea_textgen_sampling_mode = {**sampling, "seed": 4201}

            with local_only_network():
                result = runner.run_pack(
                    ROOT / "slopperly/workflows/comfy/krea2_turbo_t2i",
                    inputs,
                    SimpleNamespace(),
                    destination=str(destination),
                    timeout=2,
                )

            self.assertEqual(result, str(destination))
            self.assertEqual(destination.read_bytes(), ComfyHandler.image_bytes)

        prompt = ComfyHandler.last_prompt
        self.assertEqual(prompt["1"]["inputs"]["unet_name"], "krea2_turbo_fp8_scaled.safetensors")
        self.assertEqual(prompt["4"]["inputs"]["prompt"], "enhance local Krea Turbo prompt")
        self.assertEqual(prompt["4"]["inputs"]["sampling_mode"]["seed"], 4201)
        self.assertEqual(prompt["6"]["class_type"], "ConditioningZeroOut")
        self.assertEqual(prompt["6"]["inputs"]["conditioning"], ["5", 0])
        self.assertEqual(prompt["8"]["inputs"]["seed"], 4201)
        self.assertEqual(prompt["8"]["inputs"]["steps"], 8)
        self.assertEqual(prompt["8"]["inputs"]["cfg"], 1.0)

    def test_lumina2_pack_patches_t2i_graph(self):
        ComfyHandler.reset(_lumina_object_info())
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "lumina2.png"
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            inputs = SimpleNamespace(
                prompt="local Lumina workflow render",
                neg_prompt="text, watermark",
                width=1024,
                height=1024,
                batch=1,
                seed=5101,
                steps=30,
                guidance=4.0,
                lumina_checkpoint="lumina_2.safetensors",
                lumina_system_prompt="superior",
                lumina_shift=6.0,
                lumina_sampler="res_multistep",
                lumina_scheduler="simple",
                lumina_denoise=1.0,
            )

            with local_only_network():
                result = runner.run_pack(
                    ROOT / "slopperly/workflows/comfy/lumina2_t2i",
                    inputs,
                    SimpleNamespace(),
                    destination=str(destination),
                    timeout=2,
                )

            self.assertEqual(result, str(destination))
            self.assertEqual(destination.read_bytes(), ComfyHandler.image_bytes)

        prompt = ComfyHandler.last_prompt
        self.assertEqual(ComfyHandler.upload_bodies, [])
        self.assertEqual(prompt["1"]["inputs"]["ckpt_name"], "lumina_2.safetensors")
        self.assertEqual(prompt["2"]["inputs"]["shift"], 6.0)
        self.assertEqual(prompt["3"]["class_type"], "CLIPTextEncodeLumina2")
        self.assertEqual(prompt["3"]["inputs"]["system_prompt"], "superior")
        self.assertEqual(prompt["3"]["inputs"]["user_prompt"], "local Lumina workflow render")
        self.assertEqual(prompt["4"]["inputs"]["text"], "text, watermark")
        self.assertEqual(prompt["5"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["5"]["inputs"]["height"], 1024)
        self.assertEqual(prompt["6"]["inputs"]["seed"], 5101)
        self.assertEqual(prompt["6"]["inputs"]["steps"], 30)
        self.assertEqual(prompt["6"]["inputs"]["cfg"], 4.0)
        self.assertEqual(prompt["6"]["inputs"]["sampler_name"], "res_multistep")
        self.assertEqual(prompt["6"]["inputs"]["scheduler"], "simple")

    def test_ideogram4_pack_patches_t2i_graph(self):
        ComfyHandler.reset(_ideogram_object_info())
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "ideogram4.png"
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            inputs = SimpleNamespace(
                prompt="local Ideogram 4 workflow render with readable sign text",
                width=1024,
                height=1024,
                batch=1,
                seed=4404,
                ideogram_model="ideogram4_fp8_scaled.safetensors",
                ideogram_unconditional_model="ideogram4_unconditional_fp8_scaled.safetensors",
                ideogram_text_encoder="qwen3vl_8b_fp8_scaled.safetensors",
                ideogram_clip_type="ideogram4",
                ideogram_vae="flux2-vae.safetensors",
                ideogram_sampler="euler",
                ideogram_steps=20,
                ideogram_guidance=4.0,
                ideogram_scheduler_mu=0.0,
                ideogram_scheduler_std=1.75,
                ideogram_cfg_override=3.0,
                ideogram_cfg_override_start=0.7,
                ideogram_cfg_override_end=1.0,
            )

            with local_only_network():
                result = runner.run_pack(
                    ROOT / "slopperly/workflows/comfy/ideogram4_t2i",
                    inputs,
                    SimpleNamespace(),
                    destination=str(destination),
                    timeout=2,
                )

            self.assertEqual(result, str(destination))
            self.assertEqual(destination.read_bytes(), ComfyHandler.image_bytes)

        prompt = ComfyHandler.last_prompt
        self.assertEqual(ComfyHandler.upload_bodies, [])
        self.assertEqual(prompt["1"]["inputs"]["unet_name"], "ideogram4_fp8_scaled.safetensors")
        self.assertEqual(prompt["2"]["inputs"]["unet_name"], "ideogram4_unconditional_fp8_scaled.safetensors")
        self.assertEqual(prompt["3"]["inputs"]["clip_name"], "qwen3vl_8b_fp8_scaled.safetensors")
        self.assertEqual(prompt["3"]["inputs"]["type"], "ideogram4")
        self.assertEqual(prompt["4"]["inputs"]["text"], "local Ideogram 4 workflow render with readable sign text")
        self.assertEqual(prompt["6"]["inputs"]["cfg"], 3.0)
        self.assertEqual(prompt["6"]["inputs"]["start_percent"], 0.7)
        self.assertEqual(prompt["6"]["inputs"]["end_percent"], 1.0)
        self.assertEqual(prompt["7"]["class_type"], "DualModelGuider")
        self.assertEqual(prompt["7"]["inputs"]["cfg"], 4.0)
        self.assertEqual(prompt["8"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["8"]["inputs"]["height"], 1024)
        self.assertEqual(prompt["9"]["inputs"]["noise_seed"], 4404)
        self.assertEqual(prompt["10"]["inputs"]["sampler_name"], "euler")
        self.assertEqual(prompt["11"]["class_type"], "Ideogram4Scheduler")
        self.assertEqual(prompt["11"]["inputs"]["steps"], 20)
        self.assertEqual(prompt["11"]["inputs"]["mu"], 0.0)
        self.assertEqual(prompt["11"]["inputs"]["std"], 1.75)
        self.assertEqual(prompt["13"]["inputs"]["vae_name"], "flux2-vae.safetensors")

    def test_indexed_multi_image_uploads_patch_distinct_nodes(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "indexed_pack"
            shutil.copytree(ROOT / "slopperly/workflows/comfy/ltx23_i2v", pack)

            workflow_path = pack / "workflow.api.json"
            workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
            workflow["107"] = {
                "class_type": "LoadImage",
                "inputs": {
                    "image": "second_placeholder.png",
                },
            }
            workflow["108"] = {
                "class_type": "LoadImage",
                "inputs": {
                    "image": "anchor_placeholder.png",
                },
            }
            workflow_path.write_text(json.dumps(workflow, indent=2), encoding="utf-8")

            schema_path = pack / "params.schema.json"
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            schema["inputs"]["image_prompts[1]"] = [
                {"node": "12", "input": "text"},
            ]
            schema["uploads"] = {
                "images[0]": [{"node": "7", "input": "image", "type": "input"}],
                "images[1]": [{"node": "107", "input": "image", "type": "input"}],
                "middle_images_paths[0].path": [
                    {"node": "108", "input": "image", "type": "input"},
                ],
            }
            schema_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")

            first = Path(tmp) / "first.png"
            second = Path(tmp) / "second.png"
            anchor = Path(tmp) / "anchor.png"
            output = Path(tmp) / "result.mp4"
            first.write_bytes(b"first local image")
            second.write_bytes(b"second local image")
            anchor.write_bytes(b"anchor local image")

            ComfyHandler.reset({node["class_type"]: {} for node in workflow.values()})
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            inputs = SimpleNamespace(
                images=[str(first), str(second)],
                image_prompts=["first local prompt", "second local prompt"],
                middle_images_paths=[(str(anchor), 0.5)],
                prompt="two local references",
                neg_prompt="",
                width=1280,
                height=720,
                frames=49,
                fps=24,
                strength=0.65,
                seed=5,
            )

            with local_only_network():
                result = runner.run_pack(
                    pack,
                    inputs,
                    SimpleNamespace(),
                    destination=str(output),
                    timeout=2,
                )

        self.assertEqual(result, str(output))
        self.assertEqual(len(ComfyHandler.upload_bodies), 3)
        prompt = ComfyHandler.last_prompt
        self.assertEqual(prompt["7"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(prompt["107"]["inputs"]["image"], "uploaded_source_2.png")
        self.assertEqual(prompt["108"]["inputs"]["image"], "uploaded_source_3.png")
        self.assertEqual(prompt["12"]["inputs"]["text"], "second local prompt")
        self.assertIn(b'filename="first.png"', ComfyHandler.upload_bodies[0])
        self.assertIn(b'filename="second.png"', ComfyHandler.upload_bodies[1])
        self.assertIn(b'filename="anchor.png"', ComfyHandler.upload_bodies[2])

    def test_upload_schema_can_use_video_endpoint_and_form_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "video_upload_pack"
            shutil.copytree(ROOT / "slopperly/workflows/comfy/ltx23_i2v", pack)

            workflow_path = pack / "workflow.api.json"
            workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
            workflow["109"] = {
                "class_type": "VHS_LoadVideo",
                "inputs": {
                    "video": "placeholder.mp4",
                },
            }
            workflow_path.write_text(json.dumps(workflow, indent=2), encoding="utf-8")

            schema_path = pack / "params.schema.json"
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            schema["uploads"] = {
                "video_path": [
                    {
                        "node": "109",
                        "input": "video",
                        "type": "input",
                        "endpoint": "/upload/video",
                        "form_field": "video",
                    }
                ]
            }
            schema_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")

            video = Path(tmp) / "clip.mp4"
            video.write_bytes(b"local video fixture bytes")
            output = Path(tmp) / "result.mp4"

            ComfyHandler.reset({node["class_type"]: {} for node in workflow.values()})
            runner = ComfyWorkflowRunner(ComfyApiClient(self.base_url))
            inputs = SimpleNamespace(
                video_path=str(video),
                prompt="local video upload",
                neg_prompt="",
                width=1280,
                height=720,
                frames=49,
                fps=24,
                strength=0.65,
                seed=7,
            )

            with local_only_network():
                result = runner.run_pack(
                    pack,
                    inputs,
                    SimpleNamespace(),
                    destination=str(output),
                    timeout=2,
                )

        self.assertEqual(result, str(output))
        self.assertIn("/upload/video", ComfyHandler.request_order)
        prompt = ComfyHandler.last_prompt
        self.assertEqual(prompt["109"]["inputs"]["video"], "uploaded_video.mp4")
        self.assertIn(b'name="video"; filename="clip.mp4"', ComfyHandler.upload_bodies[0])
        self.assertIn(b'name="type"', ComfyHandler.upload_bodies[0])


if __name__ == "__main__":
    unittest.main()
