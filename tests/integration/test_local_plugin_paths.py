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
    helpers.ILLUMINATION_OPTIONS = {
        "golden time": "Warm golden hour lighting with enhanced warm colors and soft shadows",
    }
    helpers.find_strip_by_name = _find_strip_by_name
    helpers.get_strip_path = _get_strip_path
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
        if self.path == "/props":
            return self._json({"default_generation_settings": {"n_ctx": 32768}})
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
                "PreviewAny": {},
                "LoadAudio": {},
                "AudioSeparation": {},
                "SaveAudio": {},
                "UNETLoader": {},
                "VAELoader": {},
                "DualCLIPLoader": {},
                "EmptySD3LatentImage": {},
                "FluxGuidance": {},
                "InstructPixToPixConditioning": {},
                "CannyEdgePreprocessor": {},
                "DepthAnythingV2Preprocessor": {},
                "TextEncodeAceStepAudio1.5": {},
                "EmptyAceStep1.5LatentAudio": {},
                "ConditioningZeroOut": {},
                "ModelSamplingAuraFlow": {},
                "CheckpointLoaderSimple": {},
                "CLIPLoader": {},
                "CLIPTextEncodeLumina2": {},
                "CLIPTextEncode": {},
                "EmptyFlux2LatentImage": {},
                "TextGenerate": {},
                "CFGGuider": {},
                "Flux2Scheduler": {},
                "ReferenceLatent": {},
                "CFGOverride": {},
                "DualModelGuider": {},
                "RandomNoise": {},
                "KSamplerSelect": {},
                "BasicScheduler": {},
                "BasicGuider": {},
                "ModelSamplingFlux": {},
                "ModelSamplingSD3": {},
                "CLIPVisionLoader": {},
                "CLIPVisionEncode": {},
                "StyleModelLoader": {},
                "StyleModelApply": {},
                "Ideogram4Scheduler": {},
                "SamplerCustomAdvanced": {},
                "KSamplerAdvanced": {},
                "ConditioningStableAudio": {},
                "EmptyLatentAudio": {},
                "EmptyLatentImage": {},
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
                "ailab_OmniGen": {},
                "SlopperlyDiffusersImageGenerate": {},
                "UnetLoaderGGUF": {},
                "TextEncodeQwenImageEditPlus": {},
                "FluxKontextImageScale": {},
                "FluxKontextMultiReferenceLatentMethod": {},
                "LoraLoaderModelOnly": {},
                "VAEEncode": {},
                "VAEDecode": {},
                "VAEDecodeTiled": {},
                "WanImageToVideo": {},
                "Wan22ImageToVideoLatent": {},
                "CreateVideo": {},
                "SaveVideo": {},
                "UnetLoaderGGUFDisTorch2MultiGPU": {},
                "VAELoaderMultiGPU": {},
                "CLIPLoaderMultiGPU": {},
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
                node.get("class_type") == "Wan22ImageToVideoLatent"
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
            ):
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            "11": {
                                "gifs": [
                                    {
                                        "filename": "slopperly_wan22_ti2v_5b.mp4",
                                        "subfolder": "",
                                        "type": "output",
                                        "format": "video/h264-mp4",
                                    }
                                ]
                            }
                        }
                    }
                })
            if any(
                node.get("class_type") == "WanImageToVideo"
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
            ):
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            "17": {
                                "videos": [
                                    {
                                        "filename": "slopperly_wan22_i2v_a14b_native16.mp4",
                                        "subfolder": "video",
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
            if any(
                node.get("class_type") == "ailab_OmniGen"
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
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
                node.get("class_type") == "SlopperlyDiffusersImageGenerate"
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
            ):
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            "2": {
                                "images": [
                                    {
                                        "filename": "slopperly_nucleus_image_00001_.png",
                                        "subfolder": "",
                                        "type": "output",
                                    }
                                ]
                            }
                        }
                    }
                })
            if any(
                node.get("class_type") == "LoraLoaderModelOnly"
                and (node.get("inputs") or {}).get("lora_name")
                == "relighting-kontext-dev-lora-v3-comfy.safetensors"
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
            ):
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            "136": {
                                "images": [
                                    {
                                        "filename": "slopperly_kontext_relight_00001_.png",
                                        "subfolder": "",
                                        "type": "output",
                                    }
                                ]
                            }
                        }
                    }
                })
            if any(
                node.get("class_type") == "UnetLoaderGGUF"
                and (node.get("inputs") or {}).get("unet_name")
                == "flux1-kontext-dev-Q5_K_M.gguf"
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
            ):
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            "136": {
                                "images": [
                                    {
                                        "filename": "slopperly_flux_kontext_edit_00001_.png",
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
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
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
                    node.get("class_type") == "LoraLoaderModelOnly"
                    and str((node.get("inputs") or {}).get("lora_name", "")).startswith("flux2-klein-schematic-")
                    for node in RuntimeHandler.comfy_prompt.values()
                    if isinstance(node, dict)
                )
            ):
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            "19": {
                                "images": [
                                    {
                                        "filename": "slopperly_flux2_klein_9b_schematic_00001_.png",
                                        "subfolder": "",
                                        "type": "output",
                                    }
                                ]
                            }
                        }
                    }
                })
            if any(
                node.get("class_type") == "CannyEdgePreprocessor"
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
            ):
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            "13": {
                                "images": [
                                    {
                                        "filename": "slopperly_flux1_canny_control_00001_.png",
                                        "subfolder": "",
                                        "type": "output",
                                    }
                                ]
                            }
                        }
                    }
                })
            if any(
                node.get("class_type") == "DepthAnythingV2Preprocessor"
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
            ):
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            "14": {
                                "images": [
                                    {
                                        "filename": "slopperly_flux1_depth_control_00001_.png",
                                        "subfolder": "",
                                        "type": "output",
                                    }
                                ]
                            }
                        }
                    }
                })
            if any(
                node.get("class_type") == "StyleModelApply"
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
            ):
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            "9": {
                                "images": [
                                    {
                                        "filename": "slopperly_flux_redux_restyle_00001_.png",
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
                    node.get("class_type") == "UNETLoader"
                    and str((node.get("inputs") or {}).get("unet_name", "")).startswith("flux-2-klein-")
                    for node in RuntimeHandler.comfy_prompt.values()
                    if isinstance(node, dict)
                )
            ):
                output_node = "18" if "18" in RuntimeHandler.comfy_prompt else "13"
                suffix = "9b" if any(
                    node.get("class_type") == "UNETLoader"
                    and "9b" in str((node.get("inputs") or {}).get("unet_name", ""))
                    for node in RuntimeHandler.comfy_prompt.values()
                    if isinstance(node, dict)
                ) else "4b"
                filename = (
                    f"slopperly_flux2_klein_{suffix}_edit_00001_.png"
                    if output_node == "18"
                    else f"slopperly_flux2_klein_{suffix}_00001_.png"
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
            if (
                any(
                    node.get("class_type") == "UnetLoaderGGUF"
                    and (node.get("inputs") or {}).get("unet_name") == "flux2-dev-Q5_K_M.gguf"
                    for node in RuntimeHandler.comfy_prompt.values()
                    if isinstance(node, dict)
                )
            ):
                output_node = "18" if "18" in RuntimeHandler.comfy_prompt else "13"
                filename = (
                    "slopperly_flux2_dev_gguf_quality_refs_00001_.png"
                    if output_node == "18"
                    else "slopperly_flux2_dev_gguf_quality_00001_.png"
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
            if (
                any(
                    node.get("class_type") == "UnetLoaderGGUF"
                    for node in RuntimeHandler.comfy_prompt.values()
                    if isinstance(node, dict)
                )
                and any(
                    node.get("class_type") == "CLIPTextEncode"
                    for node in RuntimeHandler.comfy_prompt.values()
                    if isinstance(node, dict)
                )
            ):
                output_node = "13" if "13" in RuntimeHandler.comfy_prompt else "11"
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
                node.get("class_type") == "UnetLoaderGGUF"
                and str((node.get("inputs") or {}).get("unet_name", "")).startswith("z-image")
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
            ):
                output_node = "12" if "12" in RuntimeHandler.comfy_prompt else "10"
                unet_name = next(
                    str((node.get("inputs") or {}).get("unet_name", ""))
                    for node in RuntimeHandler.comfy_prompt.values()
                    if isinstance(node, dict) and node.get("class_type") == "UnetLoaderGGUF"
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
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
            ):
                output_node = "11" if "11" in RuntimeHandler.comfy_prompt else "9"
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
                node.get("class_type") == "UnetLoaderGGUF"
                and str((node.get("inputs") or {}).get("unet_name", "")).startswith("ernie-image")
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
            ):
                return self._json({
                    "prompt-1": {
                        "outputs": {
                            "11": {
                                "images": [
                                    {
                                        "filename": "slopperly_ernie_image_00001_.png",
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
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
            ):
                unet_name = next(
                    str((node.get("inputs") or {}).get("unet_name", ""))
                    for node in RuntimeHandler.comfy_prompt.values()
                    if isinstance(node, dict) and node.get("class_type") == "UNETLoader"
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
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
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
                node.get("class_type") == "UnetLoaderGGUF"
                and (node.get("inputs") or {}).get("unet_name") == "ideogram4-transformer-q5_0.gguf"
                for node in RuntimeHandler.comfy_prompt.values()
                if isinstance(node, dict)
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
            florence_data = {
                "bboxes": [[10, 20, 80, 120]],
                "labels": ["person"],
            }
            return self._json({
                "prompt-1": {
                    "outputs": {
                        "4": {
                            "ui": {"text": ["A person stands in warm local light."]},
                        },
                        "5": {
                            "ui": {"text": [json.dumps(florence_data)]},
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
            if self.path == "/upload/video" or b".mp4\"" in body or b".mov\"" in body or b".webm\"" in body:
                return self._json({"name": "uploaded_video.mp4", "subfolder": "", "type": "input"})
            if b".wav\"" in body or b".flac\"" in body or b".mp3\"" in body:
                return self._json({"name": "uploaded_audio.wav", "subfolder": "", "type": "input"})
            image_uploads = [
                upload for upload in RuntimeHandler.comfy_uploads
                if b".wav\"" not in upload and b".flac\"" not in upload and b".mp3\"" not in upload
            ]
            count = len(image_uploads)
            name = "uploaded_source.png" if count == 1 else f"uploaded_source_{count}.png"
            return self._json({"name": name, "subfolder": "", "type": "input"})
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


def _find_strip_by_name(scene, name):
    editor = getattr(scene, "sequence_editor", None)
    strips = getattr(editor, "strips", None)
    if not isinstance(strips, list):
        strips = getattr(editor, "strips_all", [])
    for strip in strips or []:
        if getattr(strip, "name", "") == name:
            return strip
    return None


def _get_strip_path(strip):
    return getattr(strip, "filepath", None) or getattr(strip, "path", None)


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
        self.assertIn("n_ctx=32768", inputs.usage_note)

    def test_omnivoice_generate_uses_vllm_omni_plugin_path(self):
        module = load_plugin_module("audio", "omnivoice")
        plugin = module.OmniVoicePlugin()
        with tempfile.TemporaryDirectory() as tmp:
            ref = Path(tmp) / "ref.wav"
            _tiny_wav(ref)
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(
                prompt="hello from the local runtime",
                audio_ref=str(ref),
                text_ref="hello",
                speed=1.2,
                steps=24,
                guidance=1.8,
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
        self.assertTrue(payload["ref_audio"].startswith("data:audio/x-wav;base64,"))
        self.assertEqual(payload["ref_text"], "hello")
        self.assertEqual(payload["speed"], 1.2)
        self.assertEqual(payload["language"], "English")
        self.assertEqual(payload["seed"], 123)
        self.assertEqual(payload["extra_params"]["num_step"], 24)
        self.assertEqual(payload["extra_params"]["guidance_scale"], 1.8)
        self.assertIn("warm narrator", payload["instructions"])

    def test_moss_generate_uses_vllm_omni_plugin_path(self):
        module = load_plugin_module("audio", "moss_tts")
        plugin = module.MossTTSPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            ref = Path(tmp) / "speaker.wav"
            _tiny_wav(ref)
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(prompt="local moss voice", audio_ref=str(ref), seed=321)
            scene = SimpleNamespace(
                moss_model_variant="nano",
                moss_ref_audio_path=str(ref),
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
        self.assertEqual(payload["model"], "local-model")
        self.assertTrue(payload["ref_audio"].startswith("data:audio/x-wav;base64,"))
        self.assertNotIn("voice", payload)
        self.assertNotIn("instructions", payload)
        self.assertEqual(payload["language"], "English")
        self.assertEqual(payload["seed"], 321)
        self.assertEqual(payload["max_new_tokens"], 128)
        self.assertEqual(payload["extra_params"]["max_new_frames"], 128)
        self.assertEqual(payload["extra_params"]["text_temperature"], 1.1)
        self.assertEqual(payload["extra_params"]["text_top_p"], 0.7)
        self.assertEqual(payload["extra_params"]["text_top_k"], 20)
        self.assertEqual(payload["extra_params"]["audio_temperature"], 1.1)
        self.assertEqual(payload["extra_params"]["audio_top_p"], 0.7)
        self.assertEqual(payload["extra_params"]["audio_top_k"], 20)

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

        self.assertIn(b"local-model", RuntimeHandler.transcription_body)
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
        self.assertEqual(RuntimeHandler.comfy_prompts[0]["4"]["class_type"], "PreviewAny")
        self.assertEqual(RuntimeHandler.comfy_prompts[0]["4"]["inputs"]["source"], ["3", 2])
        self.assertEqual(RuntimeHandler.comfy_prompts[0]["5"]["class_type"], "PreviewAny")
        self.assertEqual(RuntimeHandler.comfy_prompts[0]["5"]["inputs"]["source"], ["3", 3])
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

    def test_omnigen_uses_comfy_multi_image_plugin_path(self):
        module = load_plugin_module("image", "omnigen")
        plugin = module.OmniGenPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.png"
            second = Path(tmp) / "second.png"
            first.write_bytes(b"first local image")
            second.write_bytes(b"second local image")
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            scene = SimpleNamespace(
                sequence_editor=SimpleNamespace(strips=[
                    SimpleNamespace(name="first", type="IMAGE", filepath=str(first)),
                    SimpleNamespace(name="second", type="IMAGE", filepath=str(second)),
                ]),
                omnigen_prompt_1="Build a compact product render",
                omnigen_prompt_2=", using the second reference for color",
                omnigen_prompt_3="",
                omnigen_strip_1="first",
                omnigen_strip_2="second",
                omnigen_strip_3="",
                img_guidance_scale=1.65,
            )
            inputs = self.base.ModelInputs(
                prompt="fallback prompt",
                width=640,
                height=512,
                steps=8,
                guidance=3.1,
                seed=9090,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, scene)
                output = plugin.generate(pipe, inputs, scene, prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["1"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(prompt["2"]["inputs"]["image"], "uploaded_source_2.png")
        self.assertNotIn("3", prompt)
        self.assertEqual(prompt["4"]["class_type"], "ailab_OmniGen")
        self.assertIn("Build a compact product render", prompt["4"]["inputs"]["prompt"])
        self.assertIn("<img><|image_1|></img>", prompt["4"]["inputs"]["prompt"])
        self.assertIn("<img><|image_2|></img>", prompt["4"]["inputs"]["prompt"])
        self.assertNotIn("image_3", prompt["4"]["inputs"])
        self.assertEqual(prompt["4"]["inputs"]["width"], 640)
        self.assertEqual(prompt["4"]["inputs"]["height"], 512)
        self.assertEqual(prompt["4"]["inputs"]["num_inference_steps"], 8)
        self.assertEqual(prompt["4"]["inputs"]["guidance_scale"], 3.1)
        self.assertEqual(prompt["4"]["inputs"]["img_guidance_scale"], 1.65)
        self.assertTrue(prompt["4"]["inputs"]["use_input_image_size_as_output"])
        self.assertEqual(prompt["4"]["inputs"]["memory_management"], "Memory Priority")
        self.assertIn(b'filename="first.png"', RuntimeHandler.comfy_uploads[0])
        self.assertIn(b'filename="second.png"', RuntimeHandler.comfy_uploads[1])

    def test_qwen_image_edit_uses_comfy_multi_image_plugin_path(self):
        module = load_plugin_module("image", "qwen_image_edit")
        plugin = module.QwenImageEditPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.png"
            second = Path(tmp) / "second.png"
            third = Path(tmp) / "third.png"
            first.write_bytes(b"first local image")
            second.write_bytes(b"second local image")
            third.write_bytes(b"third local image")
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            scene = SimpleNamespace(
                sequence_editor=SimpleNamespace(strips=[
                    SimpleNamespace(name="second", type="IMAGE", filepath=str(second)),
                    SimpleNamespace(name="third", type="IMAGE", filepath=str(third)),
                ]),
                qwen_strip_1="second",
                qwen_strip_2="third",
                qwen_strip_3="",
            )
            inputs = self.base.ModelInputs(
                prompt="make image one look like the references",
                neg_prompt="text, watermark",
                image=str(first),
                width=1024,
                height=1024,
                steps=4,
                seed=2511,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, scene)
                output = plugin.generate(pipe, inputs, scene, prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["6"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(prompt["9"]["inputs"]["image"], "uploaded_source_2.png")
        self.assertEqual(prompt["10"]["inputs"]["image"], "uploaded_source_3.png")
        self.assertEqual(prompt["1"]["inputs"]["unet_name"], "qwen-image-edit-2511-Q5_K_M.gguf")
        self.assertEqual(prompt["4"]["inputs"]["type"], "qwen_image")
        self.assertEqual(prompt["7"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["7"]["inputs"]["height"], 1024)
        self.assertEqual(prompt["11"]["inputs"]["prompt"], "text, watermark")
        self.assertEqual(prompt["12"]["inputs"]["prompt"], "make image one look like the references")
        self.assertEqual(prompt["16"]["inputs"]["steps"], 4)
        self.assertEqual(prompt["16"]["inputs"]["cfg"], 1.0)
        self.assertIn(b'filename="first.png"', RuntimeHandler.comfy_uploads[0])
        self.assertIn(b'filename="second.png"', RuntimeHandler.comfy_uploads[1])
        self.assertIn(b'filename="third.png"', RuntimeHandler.comfy_uploads[2])

    def test_qwen_image_uses_comfy_t2i_plugin_path(self):
        module = load_plugin_module("image", "qwen_image")
        plugin = module.QwenImagePlugin()
        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(
                prompt="local Qwen Image text to image",
                neg_prompt="text, watermark",
                width=1024,
                height=1024,
                steps=4,
                guidance=1.0,
                seed=2512,
                frames=1,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace())
                output = plugin.generate(pipe, inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(RuntimeHandler.comfy_uploads, [])
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

    def test_qwen_image_uses_comfy_i2i_plugin_path(self):
        module = load_plugin_module("image", "qwen_image")
        plugin = module.QwenImagePlugin()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            source.write_bytes(b"local source image")
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(
                prompt="local Qwen Image image to image",
                neg_prompt="text, watermark",
                image=str(source),
                mode="img2img",
                width=1024,
                height=1024,
                steps=4,
                guidance=1.0,
                strength=0.65,
                seed=2513,
                frames=1,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace())
                output = plugin.generate(pipe, inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["8"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(prompt["9"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["9"]["inputs"]["height"], 1024)
        self.assertEqual(prompt["11"]["inputs"]["seed"], 2513)
        self.assertEqual(prompt["11"]["inputs"]["steps"], 4)
        self.assertEqual(prompt["11"]["inputs"]["cfg"], 1.0)
        self.assertAlmostEqual(prompt["11"]["inputs"]["denoise"], 0.35)
        self.assertIn(b'filename="source.png"', RuntimeHandler.comfy_uploads[-1])

    def test_zimage_uses_comfy_t2i_and_i2i_plugin_paths(self):
        module = load_plugin_module("image", "zimage")
        plugin = module.ZImagePlugin()
        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(
                prompt="local Z-Image text to image",
                neg_prompt="text, watermark",
                width=1024,
                height=1024,
                steps=30,
                guidance=7.0,
                seed=1201,
                frames=1,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace())
                output = plugin.generate(pipe, inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(RuntimeHandler.comfy_uploads, [])
        self.assertEqual(prompt["1"]["class_type"], "UnetLoaderGGUF")
        self.assertEqual(prompt["1"]["inputs"]["unet_name"], "z-image-Q5_K_M.gguf")
        self.assertEqual(prompt["3"]["inputs"]["clip_name"], "qwen_3_4b.safetensors")
        self.assertEqual(prompt["3"]["inputs"]["type"], "lumina2")
        self.assertEqual(prompt["4"]["inputs"]["vae_name"], "ae.safetensors")
        self.assertEqual(prompt["5"]["inputs"]["text"], "local Z-Image text to image")
        self.assertEqual(prompt["6"]["inputs"]["text"], "text, watermark")
        self.assertEqual(prompt["7"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["8"]["inputs"]["seed"], 1201)
        self.assertEqual(prompt["8"]["inputs"]["steps"], 30)
        self.assertEqual(prompt["8"]["inputs"]["cfg"], 7.0)

        with tempfile.TemporaryDirectory() as tmp:
            RuntimeHandler.comfy_uploads = []
            source = Path(tmp) / "source.png"
            source.write_bytes(b"local source image")
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(
                prompt="local Z-Image image to image",
                neg_prompt="text, watermark",
                image=str(source),
                mode="img2img",
                width=1024,
                height=1024,
                steps=30,
                guidance=7.0,
                strength=0.65,
                seed=1202,
                frames=1,
            )

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace())
                output = plugin.generate(pipe, inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["7"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(prompt["8"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["10"]["inputs"]["seed"], 1202)
        self.assertEqual(prompt["10"]["inputs"]["steps"], 30)
        self.assertEqual(prompt["10"]["inputs"]["cfg"], 7.0)
        self.assertAlmostEqual(prompt["10"]["inputs"]["denoise"], 0.35)
        self.assertIn(b'filename="source.png"', RuntimeHandler.comfy_uploads[-1])

    def test_zimage_turbo_uses_comfy_t2i_and_i2i_plugin_paths(self):
        module = load_plugin_module("image", "zimage")
        plugin = module.ZImageTurboPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(
                prompt="local Z-Image Turbo text to image",
                neg_prompt="this is recorded as unmapped",
                width=1024,
                height=1024,
                steps=8,
                guidance=0.0,
                seed=1301,
                frames=1,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace())
                output = plugin.generate(pipe, inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(RuntimeHandler.comfy_uploads, [])
        self.assertEqual(prompt["1"]["class_type"], "UnetLoaderGGUF")
        self.assertEqual(prompt["1"]["inputs"]["unet_name"], "z-image-turbo-Q5_K_M.gguf")
        self.assertEqual(prompt["5"]["inputs"]["text"], "local Z-Image Turbo text to image")
        self.assertEqual(prompt["6"]["class_type"], "ConditioningZeroOut")
        self.assertEqual(prompt["8"]["inputs"]["seed"], 1301)
        self.assertEqual(prompt["8"]["inputs"]["steps"], 8)
        self.assertEqual(prompt["8"]["inputs"]["cfg"], 1.0)
        self.assertIn("negative prompt field is preserved", inputs.usage_note)

        with tempfile.TemporaryDirectory() as tmp:
            RuntimeHandler.comfy_uploads = []
            source = Path(tmp) / "source.png"
            source.write_bytes(b"local source image")
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(
                prompt="local Z-Image Turbo image to image",
                neg_prompt="this is recorded as unmapped",
                image=str(source),
                mode="img2img",
                width=1024,
                height=1024,
                steps=8,
                guidance=0.0,
                strength=0.65,
                seed=1302,
                frames=1,
            )

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace())
                output = plugin.generate(pipe, inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["7"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(prompt["8"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["10"]["inputs"]["seed"], 1302)
        self.assertEqual(prompt["10"]["inputs"]["steps"], 8)
        self.assertEqual(prompt["10"]["inputs"]["cfg"], 1.0)
        self.assertAlmostEqual(prompt["10"]["inputs"]["denoise"], 0.35)
        self.assertIn(b'filename="source.png"', RuntimeHandler.comfy_uploads[-1])

    def test_anima_uses_comfy_t2i_and_i2i_plugin_paths(self):
        module = load_plugin_module("image", "anima")
        plugin = module.AnimaPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(
                prompt="local Anima text to image",
                neg_prompt="text, watermark",
                width=1024,
                height=1024,
                steps=25,
                guidance=4.0,
                seed=2401,
                frames=1,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace())
                output = plugin.generate(pipe, inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(RuntimeHandler.comfy_uploads, [])
        self.assertEqual(prompt["1"]["class_type"], "UnetLoaderGGUF")
        self.assertEqual(prompt["1"]["inputs"]["unet_name"], "anima-preview3-base-Q5_K_M.gguf")
        self.assertEqual(prompt["2"]["inputs"]["clip_name"], "qwen_3_06b_base.safetensors")
        self.assertEqual(prompt["2"]["inputs"]["type"], "stable_diffusion")
        self.assertEqual(prompt["3"]["inputs"]["vae_name"], "qwen_image_vae.safetensors")
        self.assertEqual(prompt["4"]["inputs"]["text"], "local Anima text to image")
        self.assertEqual(prompt["5"]["inputs"]["text"], "text, watermark")
        self.assertEqual(prompt["6"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["7"]["inputs"]["seed"], 2401)
        self.assertEqual(prompt["7"]["inputs"]["steps"], 25)
        self.assertEqual(prompt["7"]["inputs"]["cfg"], 4.0)
        self.assertEqual(prompt["7"]["inputs"]["sampler_name"], "er_sde")
        self.assertEqual(prompt["7"]["inputs"]["scheduler"], "simple")

        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            lora_inputs = self.base.ModelInputs(
                prompt="local Anima text to image with selected LoRA",
                neg_prompt="text, watermark",
                width=1024,
                height=1024,
                steps=25,
                guidance=4.0,
                seed=2403,
                frames=1,
            )
            enabled = [SimpleNamespace(name="anima_local_style", weight_value=0.6, enabled=True)]

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace(), enabled_items=enabled)
                output = plugin.generate(pipe, lora_inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        lora_prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(lora_prompt["90"]["class_type"], "LoraLoaderModelOnly")
        self.assertEqual(lora_prompt["90"]["inputs"]["model"], ["1", 0])
        self.assertEqual(lora_prompt["90"]["inputs"]["lora_name"], "anima_local_style.safetensors")
        self.assertEqual(lora_prompt["90"]["inputs"]["strength_model"], 0.6)
        self.assertEqual(lora_prompt["7"]["inputs"]["model"], ["90", 0])
        self.assertIn("applied 1 selected LoRA", lora_inputs.usage_note)
        self.assertFalse(hasattr(lora_inputs, "_slopperly_comfy_workflow_mutator"))

        with tempfile.TemporaryDirectory() as tmp:
            RuntimeHandler.comfy_uploads = []
            source = Path(tmp) / "source.png"
            source.write_bytes(b"local source image")
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(
                prompt="local Anima image to image",
                neg_prompt="text, watermark",
                image=str(source),
                mode="img2img",
                width=1024,
                height=1024,
                steps=25,
                guidance=4.0,
                strength=0.65,
                seed=2402,
                frames=1,
            )

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace())
                output = plugin.generate(pipe, inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["4"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(prompt["5"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["7"]["inputs"]["text"], "local Anima image to image")
        self.assertEqual(prompt["8"]["inputs"]["text"], "text, watermark")
        self.assertEqual(prompt["9"]["inputs"]["seed"], 2402)
        self.assertEqual(prompt["9"]["inputs"]["steps"], 25)
        self.assertEqual(prompt["9"]["inputs"]["cfg"], 4.0)
        self.assertAlmostEqual(prompt["9"]["inputs"]["denoise"], 0.35)
        self.assertIn(b'filename="source.png"', RuntimeHandler.comfy_uploads[-1])

        with tempfile.TemporaryDirectory() as tmp:
            RuntimeHandler.comfy_uploads = []
            source = Path(tmp) / "source.png"
            source.write_bytes(b"local source image")
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            lora_inputs = self.base.ModelInputs(
                prompt="local Anima image to image with selected LoRA",
                neg_prompt="text, watermark",
                image=str(source),
                mode="img2img",
                width=1024,
                height=1024,
                steps=25,
                guidance=4.0,
                strength=0.65,
                seed=2404,
                frames=1,
            )
            enabled = [
                SimpleNamespace(name="styles/anima_i2i_style.safetensors", weight_value=0.7, enabled=True)
            ]

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace(), enabled_items=enabled)
                output = plugin.generate(pipe, lora_inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        lora_prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(lora_prompt["90"]["class_type"], "LoraLoaderModelOnly")
        self.assertEqual(lora_prompt["90"]["inputs"]["model"], ["1", 0])
        self.assertEqual(lora_prompt["90"]["inputs"]["lora_name"], "anima_i2i_style.safetensors")
        self.assertEqual(lora_prompt["90"]["inputs"]["strength_model"], 0.7)
        self.assertEqual(lora_prompt["9"]["inputs"]["model"], ["90", 0])
        self.assertAlmostEqual(lora_prompt["9"]["inputs"]["denoise"], 0.35)
        self.assertIn("applied 1 selected LoRA", lora_inputs.usage_note)
        self.assertFalse(hasattr(lora_inputs, "_slopperly_comfy_workflow_mutator"))

    def test_ernie_uses_comfy_t2i_plugin_paths(self):
        module = load_plugin_module("image", "ernie")
        plugin = module.ErniePlugin()
        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(
                prompt="local ERNIE text to image",
                neg_prompt="text, watermark",
                width=1024,
                height=1024,
                steps=50,
                guidance=4.0,
                seed=3101,
                frames=1,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace())
                output = plugin.generate(pipe, inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(RuntimeHandler.comfy_uploads, [])
        self.assertEqual(prompt["1"]["class_type"], "UnetLoaderGGUF")
        self.assertEqual(prompt["1"]["inputs"]["unet_name"], "ernie-image-Q5_K_M.gguf")
        self.assertEqual(prompt["2"]["inputs"]["clip_name"], "ministral-3-3b.safetensors")
        self.assertEqual(prompt["2"]["inputs"]["type"], "flux2")
        self.assertEqual(prompt["3"]["inputs"]["vae_name"], "flux2-vae.safetensors")
        self.assertEqual(prompt["4"]["inputs"]["clip_name"], "ernie-image-prompt-enhancer.safetensors")
        self.assertIn("local ERNIE text to image", prompt["5"]["inputs"]["prompt"])
        self.assertEqual(prompt["5"]["inputs"]["sampling_mode"], "on")
        self.assertEqual(prompt["5"]["inputs"]["sampling_mode.seed"], 3101)
        self.assertEqual(prompt["5"]["inputs"]["sampling_mode.temperature"], 0.6)
        self.assertEqual(prompt["6"]["inputs"]["text"], ["5", 0])
        self.assertEqual(prompt["7"]["inputs"]["text"], "text, watermark")
        self.assertEqual(prompt["8"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["8"]["inputs"]["height"], 1024)
        self.assertEqual(prompt["9"]["inputs"]["seed"], 3101)
        self.assertEqual(prompt["9"]["inputs"]["steps"], 50)
        self.assertEqual(prompt["9"]["inputs"]["cfg"], 4.0)

    def test_ernie_turbo_uses_comfy_t2i_plugin_path(self):
        module = load_plugin_module("image", "ernie_turbo")
        plugin = module.ErnieTurboPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(
                prompt="local ERNIE Turbo text to image",
                neg_prompt="recorded as unmapped",
                width=1024,
                height=1024,
                steps=8,
                guidance=1.0,
                seed=3201,
                frames=1,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace())
                output = plugin.generate(pipe, inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(RuntimeHandler.comfy_uploads, [])
        self.assertEqual(prompt["1"]["class_type"], "UnetLoaderGGUF")
        self.assertEqual(prompt["1"]["inputs"]["unet_name"], "ernie-image-turbo-Q5_K_M.gguf")
        self.assertIn("local ERNIE Turbo text to image", prompt["5"]["inputs"]["prompt"])
        self.assertEqual(prompt["5"]["inputs"]["sampling_mode"], "on")
        self.assertEqual(prompt["5"]["inputs"]["sampling_mode.seed"], 3201)
        self.assertEqual(prompt["7"]["class_type"], "ConditioningZeroOut")
        self.assertEqual(prompt["9"]["inputs"]["seed"], 3201)
        self.assertEqual(prompt["9"]["inputs"]["steps"], 8)
        self.assertEqual(prompt["9"]["inputs"]["cfg"], 1.0)
        self.assertIn("negative prompt field is preserved", inputs.usage_note)

    def test_krea2_base_uses_comfy_t2i_plugin_path(self):
        module = load_plugin_module("image", "_krea2_base")
        plugin = module.Krea2BasePlugin()
        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(
                prompt="local Krea 2 RAW text to image",
                neg_prompt="text, watermark",
                width=1024,
                height=1024,
                steps=28,
                guidance=4.5,
                seed=4101,
                frames=1,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace())
                output = plugin.generate(pipe, inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(RuntimeHandler.comfy_uploads, [])
        self.assertEqual(prompt["1"]["class_type"], "UnetLoaderGGUF")
        self.assertEqual(prompt["1"]["inputs"]["unet_name"], "krea2_raw-Q5_K_M.gguf")
        self.assertEqual(prompt["2"]["inputs"]["clip_name"], "qwen3vl_4b_fp8_scaled.safetensors")
        self.assertEqual(prompt["2"]["inputs"]["type"], "krea2")
        self.assertEqual(prompt["3"]["inputs"]["vae_name"], "qwen_image_vae.safetensors")
        self.assertIn("local Krea 2 RAW text to image", prompt["4"]["inputs"]["prompt"])
        self.assertEqual(prompt["4"]["inputs"]["sampling_mode"], "on")
        self.assertEqual(prompt["4"]["inputs"]["sampling_mode.seed"], 4101)
        self.assertEqual(prompt["5"]["inputs"]["text"], ["4", 0])
        self.assertEqual(prompt["6"]["inputs"]["text"], "text, watermark")
        self.assertEqual(prompt["7"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["7"]["inputs"]["height"], 1024)
        self.assertEqual(prompt["8"]["inputs"]["seed"], 4101)
        self.assertEqual(prompt["8"]["inputs"]["steps"], 28)
        self.assertEqual(prompt["8"]["inputs"]["cfg"], 4.5)

        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            lora_inputs = self.base.ModelInputs(
                prompt="local Krea 2 RAW with selected LoRA",
                neg_prompt="text, watermark",
                width=1024,
                height=1024,
                steps=28,
                guidance=4.5,
                seed=4102,
                frames=1,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)
            enabled = [SimpleNamespace(name="krea_local_style", weight_value=0.55, enabled=True)]

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace(), enabled_items=enabled)
                output = plugin.generate(pipe, lora_inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        lora_prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(lora_prompt["90"]["class_type"], "LoraLoaderModelOnly")
        self.assertEqual(lora_prompt["90"]["inputs"]["model"], ["1", 0])
        self.assertEqual(lora_prompt["90"]["inputs"]["lora_name"], "krea_local_style.safetensors")
        self.assertEqual(lora_prompt["90"]["inputs"]["strength_model"], 0.55)
        self.assertEqual(lora_prompt["8"]["inputs"]["model"], ["90", 0])
        self.assertIn("applied 1 selected LoRA", lora_inputs.usage_note)
        self.assertFalse(hasattr(lora_inputs, "_slopperly_comfy_workflow_mutator"))

    def test_krea2_turbo_uses_comfy_t2i_plugin_path(self):
        module = load_plugin_module("image", "krea2_turbo")
        plugin = module.Krea2TurboPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(
                prompt="local Krea 2 Turbo text to image",
                neg_prompt="recorded as unmapped",
                width=1024,
                height=1024,
                steps=8,
                guidance=1.0,
                seed=4201,
                frames=1,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace())
                output = plugin.generate(pipe, inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(RuntimeHandler.comfy_uploads, [])
        self.assertEqual(prompt["1"]["class_type"], "UnetLoaderGGUF")
        self.assertEqual(prompt["1"]["inputs"]["unet_name"], "krea2_turbo-Q5_K_M.gguf")
        self.assertEqual(prompt["2"]["inputs"]["clip_name"], "qwen3vl_4b_fp8_scaled.safetensors")
        self.assertEqual(prompt["2"]["inputs"]["type"], "krea2")
        self.assertIn("local Krea 2 Turbo text to image", prompt["4"]["inputs"]["prompt"])
        self.assertEqual(prompt["4"]["inputs"]["sampling_mode"], "on")
        self.assertEqual(prompt["4"]["inputs"]["sampling_mode.seed"], 4201)
        self.assertEqual(prompt["5"]["inputs"]["text"], ["4", 0])
        self.assertEqual(prompt["6"]["class_type"], "ConditioningZeroOut")
        self.assertEqual(prompt["8"]["inputs"]["seed"], 4201)
        self.assertEqual(prompt["8"]["inputs"]["steps"], 8)
        self.assertEqual(prompt["8"]["inputs"]["cfg"], 1.0)
        self.assertIn("negative prompt field is preserved", inputs.usage_note)

        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            lora_inputs = self.base.ModelInputs(
                prompt="local Krea 2 Turbo with selected LoRA",
                neg_prompt="recorded as unmapped",
                width=1024,
                height=1024,
                steps=8,
                guidance=1.0,
                seed=4202,
                frames=1,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)
            enabled = [
                SimpleNamespace(name="krea_turbo_style.safetensors", weight_value=0.7, enabled=True)
            ]

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace(), enabled_items=enabled)
                output = plugin.generate(pipe, lora_inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        lora_prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(lora_prompt["90"]["class_type"], "LoraLoaderModelOnly")
        self.assertEqual(lora_prompt["90"]["inputs"]["model"], ["1", 0])
        self.assertEqual(lora_prompt["90"]["inputs"]["lora_name"], "krea_turbo_style.safetensors")
        self.assertEqual(lora_prompt["90"]["inputs"]["strength_model"], 0.7)
        self.assertEqual(lora_prompt["8"]["inputs"]["model"], ["90", 0])
        self.assertIn("applied 1 selected LoRA", lora_inputs.usage_note)
        self.assertIn("negative prompt field is preserved", lora_inputs.usage_note)
        self.assertFalse(hasattr(lora_inputs, "_slopperly_comfy_workflow_mutator"))

    def test_lumina2_uses_comfy_t2i_plugin_path(self):
        module = load_plugin_module("image", "lumina2")
        plugin = module.Lumina2Plugin()
        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(
                prompt="local Lumina text to image",
                neg_prompt="text, watermark",
                width=1024,
                height=1024,
                steps=30,
                guidance=4.0,
                seed=5101,
                frames=1,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace())
                output = plugin.generate(pipe, inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(RuntimeHandler.comfy_uploads, [])
        self.assertEqual(prompt["1"]["inputs"]["ckpt_name"], "lumina_2.safetensors")
        self.assertEqual(prompt["2"]["class_type"], "ModelSamplingAuraFlow")
        self.assertEqual(prompt["2"]["inputs"]["shift"], 6.0)
        self.assertEqual(prompt["3"]["class_type"], "CLIPTextEncodeLumina2")
        self.assertEqual(prompt["3"]["inputs"]["system_prompt"], "superior")
        self.assertEqual(prompt["3"]["inputs"]["user_prompt"], "local Lumina text to image")
        self.assertEqual(prompt["4"]["inputs"]["text"], "text, watermark")
        self.assertEqual(prompt["5"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["5"]["inputs"]["height"], 1024)
        self.assertEqual(prompt["6"]["inputs"]["seed"], 5101)
        self.assertEqual(prompt["6"]["inputs"]["steps"], 30)
        self.assertEqual(prompt["6"]["inputs"]["cfg"], 4.0)
        self.assertEqual(prompt["6"]["inputs"]["sampler_name"], "res_multistep")
        self.assertEqual(prompt["6"]["inputs"]["scheduler"], "simple")

    def test_ideogram4_uses_comfy_t2i_plugin_path(self):
        module = load_plugin_module("image", "ideogram4")
        plugin = module.Ideogram4Plugin()
        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(
                prompt="local Ideogram 4 poster with readable text",
                width=1024,
                height=1024,
                steps=20,
                guidance=4.0,
                seed=4404,
                frames=1,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)
            scene = SimpleNamespace(ideogram_prompt_upsampling=True)
            enabled = [SimpleNamespace(name="local_style", weight_value=0.75, enabled=True)]

            with local_only_network():
                pipe = plugin.load(prefs, scene, enabled_items=enabled)
                output = plugin.generate(pipe, inputs, scene, prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(RuntimeHandler.comfy_uploads, [])
        self.assertEqual(prompt["1"]["class_type"], "UnetLoaderGGUF")
        self.assertEqual(prompt["2"]["class_type"], "UnetLoaderGGUF")
        self.assertEqual(prompt["1"]["inputs"]["unet_name"], "ideogram4-transformer-q5_0.gguf")
        self.assertEqual(prompt["2"]["inputs"]["unet_name"], "ideogram4-unconditional_transformer-q5_0.gguf")
        self.assertEqual(prompt["3"]["inputs"]["clip_name"], "qwen3vl_8b_fp8_scaled.safetensors")
        self.assertEqual(prompt["3"]["inputs"]["type"], "ideogram4")
        self.assertEqual(prompt["4"]["inputs"]["text"], "local Ideogram 4 poster with readable text")
        self.assertEqual(prompt["6"]["inputs"]["cfg"], 3.0)
        self.assertEqual(prompt["6"]["inputs"]["start_percent"], 0.7)
        self.assertEqual(prompt["6"]["inputs"]["end_percent"], 1.0)
        self.assertEqual(prompt["7"]["class_type"], "DualModelGuider")
        self.assertEqual(prompt["7"]["inputs"]["cfg"], 4.0)
        self.assertEqual(prompt["8"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["8"]["inputs"]["height"], 1024)
        self.assertEqual(prompt["9"]["inputs"]["noise_seed"], 4404)
        self.assertEqual(prompt["10"]["inputs"]["sampler_name"], "euler")
        self.assertEqual(prompt["11"]["inputs"]["steps"], 20)
        self.assertEqual(prompt["11"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["11"]["inputs"]["height"], 1024)
        self.assertEqual(prompt["11"]["inputs"]["std"], 1.75)
        self.assertEqual(prompt["13"]["inputs"]["vae_name"], "flux2-vae.safetensors")
        self.assertIn("dynamic project LoRA injection is not mapped", inputs.usage_note)
        self.assertIn("prompt upsampling UI is preserved", inputs.usage_note)

    def test_flux_canny_uses_comfy_control_plugin_path(self):
        module = load_plugin_module("image", "flux_canny")
        plugin = module.FluxCannyPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            source.write_bytes(b"local canny source image")
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(
                prompt="local FLUX.1 Canny control render",
                image=str(source),
                width=1024,
                height=768,
                steps=28,
                guidance=3.5,
                strength=0.45,
                seed=6101,
                frames=1,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace())
                output = plugin.generate(pipe, inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["1"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(prompt["2"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["2"]["inputs"]["height"], 768)
        self.assertEqual(prompt["3"]["class_type"], "CannyEdgePreprocessor")
        self.assertEqual(prompt["3"]["inputs"]["low_threshold"], 50)
        self.assertEqual(prompt["3"]["inputs"]["high_threshold"], 200)
        self.assertEqual(prompt["3"]["inputs"]["resolution"], 1024)
        self.assertEqual(prompt["4"]["class_type"], "UnetLoaderGGUF")
        self.assertEqual(prompt["4"]["inputs"]["unet_name"], "flux1-canny-dev-fp16-Q5_0-GGUF.gguf")
        self.assertNotIn("weight_dtype", prompt["4"]["inputs"])
        self.assertEqual(prompt["5"]["inputs"]["vae_name"], "ae.safetensors")
        self.assertEqual(prompt["6"]["inputs"]["clip_name1"], "clip_l.safetensors")
        self.assertEqual(prompt["6"]["inputs"]["clip_name2"], "t5xxl_fp16.safetensors")
        self.assertEqual(prompt["7"]["inputs"]["text"], "local FLUX.1 Canny control render")
        self.assertEqual(prompt["8"]["inputs"]["text"], "")
        self.assertEqual(prompt["9"]["inputs"]["guidance"], 3.5)
        self.assertEqual(prompt["10"]["class_type"], "InstructPixToPixConditioning")
        self.assertEqual(prompt["11"]["inputs"]["seed"], 6101)
        self.assertEqual(prompt["11"]["inputs"]["steps"], 28)
        self.assertEqual(prompt["11"]["inputs"]["cfg"], 1.0)
        self.assertIn("image strength slider is preserved", inputs.usage_note)
        self.assertIn(b'filename="source.png"', RuntimeHandler.comfy_uploads[-1])

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            source.write_bytes(b"local canny lora source image")
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            lora_inputs = self.base.ModelInputs(
                prompt="local FLUX.1 Canny control render with selected LoRA",
                image=str(source),
                width=1024,
                height=768,
                steps=28,
                guidance=3.5,
                strength=0.45,
                seed=6111,
                frames=1,
            )
            enabled = [
                SimpleNamespace(name="styles/canny_control_style", weight_value=0.65, enabled=True)
            ]

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace(), enabled_items=enabled)
                output = plugin.generate(pipe, lora_inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        lora_prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(lora_prompt["90"]["class_type"], "LoraLoaderModelOnly")
        self.assertEqual(lora_prompt["90"]["inputs"]["model"], ["4", 0])
        self.assertEqual(lora_prompt["90"]["inputs"]["lora_name"], "canny_control_style.safetensors")
        self.assertEqual(lora_prompt["90"]["inputs"]["strength_model"], 0.65)
        self.assertEqual(lora_prompt["11"]["inputs"]["model"], ["90", 0])
        self.assertIn("applied 1 selected LoRA", lora_inputs.usage_note)
        self.assertFalse(hasattr(lora_inputs, "_slopperly_comfy_workflow_mutator"))

    def test_flux_depth_uses_comfy_control_plugin_path(self):
        module = load_plugin_module("image", "flux_depth")
        plugin = module.FluxDepthPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            source.write_bytes(b"local depth source image")
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(
                prompt="local FLUX.1 Depth control render",
                image=str(source),
                width=768,
                height=1024,
                steps=28,
                guidance=3.5,
                strength=0.45,
                seed=6102,
                frames=1,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace())
                output = plugin.generate(pipe, inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["1"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(prompt["2"]["inputs"]["width"], 768)
        self.assertEqual(prompt["2"]["inputs"]["height"], 1024)
        self.assertEqual(prompt["3"]["class_type"], "DepthAnythingV2Preprocessor")
        self.assertEqual(prompt["3"]["inputs"]["ckpt_name"], "depth_anything_v2_vitl.pth")
        self.assertEqual(prompt["3"]["inputs"]["resolution"], 768)
        self.assertEqual(prompt["4"]["class_type"], "UnetLoaderGGUF")
        self.assertEqual(prompt["4"]["inputs"]["unet_name"], "flux1-depth-dev-fp16-Q5_0-GGUF.gguf")
        self.assertNotIn("weight_dtype", prompt["4"]["inputs"])
        self.assertEqual(prompt["5"]["inputs"]["lora_name"], "flux1-depth-dev-lora.safetensors")
        self.assertEqual(prompt["5"]["inputs"]["strength_model"], 1.0)
        self.assertEqual(prompt["6"]["inputs"]["vae_name"], "ae.safetensors")
        self.assertEqual(prompt["7"]["inputs"]["clip_name1"], "clip_l.safetensors")
        self.assertEqual(prompt["7"]["inputs"]["clip_name2"], "t5xxl_fp16.safetensors")
        self.assertEqual(prompt["8"]["inputs"]["text"], "local FLUX.1 Depth control render")
        self.assertEqual(prompt["9"]["inputs"]["text"], "")
        self.assertEqual(prompt["10"]["inputs"]["guidance"], 3.5)
        self.assertEqual(prompt["11"]["class_type"], "InstructPixToPixConditioning")
        self.assertEqual(prompt["12"]["inputs"]["seed"], 6102)
        self.assertEqual(prompt["12"]["inputs"]["steps"], 28)
        self.assertEqual(prompt["12"]["inputs"]["cfg"], 2.0)
        self.assertIn("image strength slider is preserved", inputs.usage_note)
        self.assertIn(b'filename="source.png"', RuntimeHandler.comfy_uploads[-1])

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            source.write_bytes(b"local depth lora source image")
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            lora_inputs = self.base.ModelInputs(
                prompt="local FLUX.1 Depth control render with selected LoRA",
                image=str(source),
                width=768,
                height=1024,
                steps=28,
                guidance=3.5,
                strength=0.45,
                seed=6112,
                frames=1,
            )
            enabled = [
                SimpleNamespace(name="depth_control_style.safetensors", weight_value=0.7, enabled=True)
            ]

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace(), enabled_items=enabled)
                output = plugin.generate(pipe, lora_inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        lora_prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(lora_prompt["90"]["class_type"], "LoraLoaderModelOnly")
        self.assertEqual(lora_prompt["90"]["inputs"]["model"], ["5", 0])
        self.assertEqual(lora_prompt["90"]["inputs"]["lora_name"], "depth_control_style.safetensors")
        self.assertEqual(lora_prompt["90"]["inputs"]["strength_model"], 0.7)
        self.assertEqual(lora_prompt["12"]["inputs"]["model"], ["90", 0])
        self.assertIn("applied 1 selected LoRA", lora_inputs.usage_note)
        self.assertFalse(hasattr(lora_inputs, "_slopperly_comfy_workflow_mutator"))

    def test_flux_redux_uses_comfy_restyle_plugin_path(self):
        module = load_plugin_module("image", "flux_redux")
        plugin = module.FluxReduxPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            source.write_bytes(b"local redux source image")
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(
                image=str(source),
                width=1024,
                height=768,
                steps=25,
                guidance=3.5,
                seed=6201,
                frames=1,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace())
                output = plugin.generate(pipe, inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["40"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(prompt["27"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["27"]["inputs"]["height"], 768)
        self.assertEqual(prompt["30"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["30"]["inputs"]["height"], 768)
        self.assertEqual(prompt["12"]["class_type"], "UnetLoaderGGUF")
        self.assertEqual(prompt["12"]["inputs"]["unet_name"], "flux1-dev-Q5_K_M.gguf")
        self.assertNotIn("weight_dtype", prompt["12"]["inputs"])
        self.assertEqual(prompt["11"]["inputs"]["clip_name1"], "t5xxl_fp16.safetensors")
        self.assertEqual(prompt["11"]["inputs"]["clip_name2"], "clip_l.safetensors")
        self.assertEqual(prompt["10"]["inputs"]["vae_name"], "ae.safetensors")
        self.assertEqual(prompt["38"]["inputs"]["clip_name"], "sigclip_vision_patch14_384.safetensors")
        self.assertEqual(prompt["42"]["inputs"]["style_model_name"], "flux1-redux-dev.safetensors")
        self.assertEqual(prompt["39"]["inputs"]["crop"], "center")
        self.assertEqual(prompt["41"]["inputs"]["strength"], 1.0)
        self.assertEqual(prompt["41"]["inputs"]["strength_type"], "multiply")
        self.assertEqual(prompt["6"]["inputs"]["text"], "")
        self.assertEqual(prompt["26"]["inputs"]["guidance"], 3.5)
        self.assertEqual(prompt["17"]["inputs"]["steps"], 25)
        self.assertEqual(prompt["25"]["inputs"]["noise_seed"], 6201)
        self.assertEqual(prompt["41"]["class_type"], "StyleModelApply")
        self.assertIn(b'filename="source.png"', RuntimeHandler.comfy_uploads[-1])

    def test_flux_kontext_uses_comfy_edit_plugin_path(self):
        module = load_plugin_module("image", "flux_kontext")
        plugin = module.FluxKontextPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            source.write_bytes(b"local kontext source image")
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(
                prompt="turn the cup red while preserving the table layout",
                image=str(source),
                width=1024,
                height=768,
                steps=28,
                guidance=3.5,
                strength=0.65,
                seed=6301,
                frames=1,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace())
                output = plugin.generate(pipe, inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["142"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(prompt["188"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["188"]["inputs"]["height"], 768)
        self.assertEqual(prompt["37"]["class_type"], "UnetLoaderGGUF")
        self.assertEqual(prompt["37"]["inputs"]["unet_name"], "flux1-kontext-dev-Q5_K_M.gguf")
        self.assertNotIn("weight_dtype", prompt["37"]["inputs"])
        self.assertEqual(prompt["38"]["inputs"]["clip_name1"], "clip_l.safetensors")
        self.assertEqual(prompt["38"]["inputs"]["clip_name2"], "t5xxl_fp8_e4m3fn_scaled.safetensors")
        self.assertEqual(prompt["38"]["inputs"]["type"], "flux")
        self.assertEqual(prompt["39"]["inputs"]["vae_name"], "ae.safetensors")
        self.assertEqual(prompt["6"]["inputs"]["text"], "turn the cup red while preserving the table layout")
        self.assertEqual(prompt["35"]["inputs"]["guidance"], 3.5)
        self.assertEqual(prompt["31"]["inputs"]["seed"], 6301)
        self.assertEqual(prompt["31"]["inputs"]["steps"], 28)
        self.assertEqual(prompt["31"]["inputs"]["cfg"], 1.0)
        self.assertEqual(prompt["31"]["inputs"]["sampler_name"], "euler")
        self.assertEqual(prompt["31"]["inputs"]["scheduler"], "simple")
        self.assertEqual(prompt["31"]["inputs"]["denoise"], 1.0)
        self.assertEqual(prompt["42"]["class_type"], "FluxKontextImageScale")
        self.assertEqual(prompt["177"]["class_type"], "ReferenceLatent")
        self.assertEqual(prompt["135"]["class_type"], "ConditioningZeroOut")
        self.assertIn("image strength slider is preserved", inputs.usage_note)
        self.assertIn(b'filename="source.png"', RuntimeHandler.comfy_uploads[-1])

    def test_flux_kontext_accepts_collected_image_object(self):
        class FakeImage:
            def save(self, path):
                Path(path).write_bytes(b"temporary kontext image object")

        module = load_plugin_module("image", "flux_kontext")
        plugin = module.FluxKontextPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(
                prompt="make the collected image look like red ceramic",
                image=FakeImage(),
                width=1024,
                height=1024,
                steps=28,
                guidance=3.5,
                seed=6302,
                frames=1,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace())
                output = plugin.generate(pipe, inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["142"]["inputs"]["image"], "uploaded_source.png")
        self.assertIn(b'filename="slopperly_image_', RuntimeHandler.comfy_uploads[-1])

    def test_kontext_relight_uses_comfy_lora_plugin_path(self):
        module = load_plugin_module("image", "kontext_relight")
        plugin = module.KontextRelightPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            source.write_bytes(b"local relight source image")
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(
                prompt="",
                image=str(source),
                width=1024,
                height=768,
                steps=28,
                guidance=3.5,
                seed=6401,
                frames=1,
            )
            scene = SimpleNamespace(
                illumination_style="golden time",
                light_direction="left",
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, scene)
                output = plugin.generate(pipe, inputs, scene, prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        expected_prompt = (
            "Relight the image with golden time lighting coming from the left. "
            "Warm golden hour lighting with enhanced warm colors and soft shadows "
            "Maintain the identity of the foreground subjects."
        )
        self.assertEqual(prompt["142"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(prompt["188"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["188"]["inputs"]["height"], 768)
        self.assertEqual(prompt["37"]["class_type"], "UnetLoaderGGUF")
        self.assertEqual(prompt["37"]["inputs"]["unet_name"], "flux1-kontext-dev-Q5_K_M.gguf")
        self.assertNotIn("weight_dtype", prompt["37"]["inputs"])
        self.assertEqual(prompt["50"]["inputs"]["lora_name"], "relighting-kontext-dev-lora-v3-comfy.safetensors")
        self.assertEqual(prompt["50"]["inputs"]["strength_model"], 0.75)
        self.assertEqual(prompt["38"]["inputs"]["clip_name1"], "clip_l.safetensors")
        self.assertEqual(prompt["38"]["inputs"]["clip_name2"], "t5xxl_fp8_e4m3fn_scaled.safetensors")
        self.assertEqual(prompt["38"]["inputs"]["type"], "flux")
        self.assertEqual(prompt["39"]["inputs"]["vae_name"], "ae.safetensors")
        self.assertEqual(prompt["6"]["inputs"]["text"], expected_prompt)
        self.assertEqual(prompt["35"]["inputs"]["guidance"], 3.5)
        self.assertEqual(prompt["31"]["inputs"]["seed"], 6401)
        self.assertEqual(prompt["31"]["inputs"]["steps"], 28)
        self.assertEqual(prompt["31"]["inputs"]["cfg"], 1.0)
        self.assertEqual(prompt["31"]["inputs"]["sampler_name"], "euler")
        self.assertEqual(prompt["31"]["inputs"]["scheduler"], "simple")
        self.assertEqual(prompt["31"]["inputs"]["denoise"], 1.0)
        self.assertEqual(prompt["42"]["class_type"], "FluxKontextImageScale")
        self.assertEqual(prompt["177"]["class_type"], "ReferenceLatent")
        self.assertEqual(prompt["135"]["class_type"], "ConditioningZeroOut")
        self.assertIn(b'filename="source.png"', RuntimeHandler.comfy_uploads[-1])

    def test_flux2_dev_uses_comfy_t2i_and_reference_plugin_paths(self):
        module = load_plugin_module("image", "flux2_dev")
        plugin = module.Flux2DevPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            prefs = SimpleNamespace(comfyui_url=self.base_url)
            t2i_inputs = self.base.ModelInputs(
                prompt="local FLUX.2 Dev Q5 text to image",
                width=1024,
                height=1024,
                steps=8,
                guidance=3.5,
                seed=42034,
                frames=1,
            )

            RuntimeHandler.comfy_uploads = []
            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace())
                output = plugin.generate(pipe, t2i_inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

            t2i_prompt = RuntimeHandler.comfy_prompts[-1]
            self.assertEqual(RuntimeHandler.comfy_uploads, [])
            self.assertEqual(t2i_prompt["1"]["class_type"], "UnetLoaderGGUF")
            self.assertEqual(t2i_prompt["1"]["inputs"]["unet_name"], "flux2-dev-Q5_K_M.gguf")
            self.assertEqual(t2i_prompt["2"]["inputs"]["clip_name"], "mistral_3_small_flux2_fp8.safetensors")
            self.assertEqual(t2i_prompt["2"]["inputs"]["type"], "flux2")
            self.assertEqual(t2i_prompt["3"]["inputs"]["vae_name"], "flux2-vae.safetensors")
            self.assertEqual(t2i_prompt["4"]["inputs"]["text"], "local FLUX.2 Dev Q5 text to image")
            self.assertEqual(t2i_prompt["6"]["inputs"]["cfg"], 3.5)
            self.assertEqual(t2i_prompt["7"]["inputs"]["noise_seed"], 42034)
            self.assertEqual(t2i_prompt["9"]["inputs"]["steps"], 8)
            self.assertEqual(t2i_prompt["9"]["inputs"]["width"], 1024)
            self.assertEqual(t2i_prompt["10"]["inputs"]["height"], 1024)

            source = Path(tmp) / "source.png"
            ref1 = Path(tmp) / "ref1.png"
            ref2 = Path(tmp) / "ref2.png"
            ref3 = Path(tmp) / "ref3.png"
            source.write_bytes(b"local flux dev source image")
            ref1.write_bytes(b"local flux dev reference one")
            ref2.write_bytes(b"local flux dev reference two")
            ref3.write_bytes(b"local flux dev reference three")
            scene = SimpleNamespace(
                sequence_editor=SimpleNamespace(strips=[
                    SimpleNamespace(name="ref1", type="IMAGE", filepath=str(ref1)),
                    SimpleNamespace(name="ref2", type="IMAGE", filepath=str(ref2)),
                    SimpleNamespace(name="ref3", type="IMAGE", filepath=str(ref3)),
                ]),
                flux_strip_1="ref1",
                flux_strip_2="ref2",
                flux_strip_3="ref3",
            )
            ref_inputs = self.base.ModelInputs(
                prompt="combine local FLUX.2 Dev references",
                image=str(source),
                width=1024,
                height=1024,
                steps=8,
                guidance=3.5,
                seed=42035,
                frames=1,
            )

            RuntimeHandler.comfy_uploads = []
            with local_only_network():
                pipe = plugin.load(prefs, scene)
                output = plugin.generate(pipe, ref_inputs, scene, prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        ref_prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(len(RuntimeHandler.comfy_uploads), 3)
        self.assertEqual(ref_prompt["3"]["class_type"], "UnetLoaderGGUF")
        self.assertEqual(ref_prompt["3"]["inputs"]["unet_name"], "flux2-dev-Q5_K_M.gguf")
        self.assertEqual(ref_prompt["4"]["inputs"]["clip_name"], "mistral_3_small_flux2_fp8.safetensors")
        self.assertEqual(ref_prompt["5"]["inputs"]["vae_name"], "flux2-vae.safetensors")
        self.assertEqual(ref_prompt["1"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(ref_prompt["19"]["inputs"]["image"], "uploaded_source_2.png")
        self.assertEqual(ref_prompt["24"]["inputs"]["image"], "uploaded_source_3.png")
        self.assertEqual(ref_prompt["6"]["inputs"]["text"], "combine local FLUX.2 Dev references")
        self.assertEqual(ref_prompt["11"]["inputs"]["cfg"], 3.5)
        self.assertEqual(ref_prompt["12"]["inputs"]["noise_seed"], 42035)
        self.assertEqual(ref_prompt["14"]["inputs"]["steps"], 8)
        self.assertEqual(ref_prompt["11"]["inputs"]["positive"], ["27", 0])
        self.assertIn(b'filename="source.png"', RuntimeHandler.comfy_uploads[0])
        self.assertIn(b'filename="ref1.png"', RuntimeHandler.comfy_uploads[1])
        self.assertIn(b'filename="ref2.png"', RuntimeHandler.comfy_uploads[2])
        self.assertIn("three certified ReferenceLatent slots", ref_inputs.usage_note)

    def test_flux2_klein_4b_uses_comfy_t2i_and_edit_plugin_paths(self):
        module = load_plugin_module("image", "flux2_klein_4b")
        plugin = module.Flux2Klein4BPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            t2i_inputs = self.base.ModelInputs(
                prompt="local FLUX.2 Klein 4B text to image",
                width=1024,
                height=1024,
                steps=4,
                guidance=1.0,
                seed=42004,
                frames=1,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            RuntimeHandler.comfy_uploads = []
            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace())
                output = plugin.generate(pipe, t2i_inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

            t2i_prompt = RuntimeHandler.comfy_prompts[-1]
            self.assertEqual(RuntimeHandler.comfy_uploads, [])
            self.assertEqual(t2i_prompt["1"]["class_type"], "UnetLoaderGGUF")
            self.assertEqual(t2i_prompt["1"]["inputs"]["unet_name"], "flux-2-klein-4b-Q5_K_M.gguf")
            self.assertEqual(t2i_prompt["2"]["inputs"]["clip_name"], "qwen_3_4b.safetensors")
            self.assertEqual(t2i_prompt["2"]["inputs"]["type"], "flux2")
            self.assertEqual(t2i_prompt["3"]["inputs"]["vae_name"], "flux2-vae.safetensors")
            self.assertEqual(t2i_prompt["4"]["inputs"]["text"], "local FLUX.2 Klein 4B text to image")
            self.assertEqual(t2i_prompt["6"]["inputs"]["cfg"], 1.0)
            self.assertEqual(t2i_prompt["7"]["inputs"]["noise_seed"], 42004)
            self.assertEqual(t2i_prompt["9"]["inputs"]["steps"], 4)
            self.assertEqual(t2i_prompt["9"]["inputs"]["width"], 1024)
            self.assertEqual(t2i_prompt["10"]["inputs"]["height"], 1024)

            lora_inputs = self.base.ModelInputs(
                prompt="local FLUX.2 Klein 4B text to image with selected LoRA",
                width=1024,
                height=1024,
                steps=4,
                guidance=1.0,
                seed=42006,
                frames=1,
            )
            enabled = [SimpleNamespace(name="styles/klein_local_style", weight_value=0.55, enabled=True)]

            RuntimeHandler.comfy_uploads = []
            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace(), enabled_items=enabled)
                output = plugin.generate(pipe, lora_inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

            lora_prompt = RuntimeHandler.comfy_prompts[-1]
            self.assertEqual(lora_prompt["90"]["class_type"], "LoraLoaderModelOnly")
            self.assertEqual(lora_prompt["90"]["inputs"]["model"], ["1", 0])
            self.assertEqual(lora_prompt["90"]["inputs"]["lora_name"], "klein_local_style.safetensors")
            self.assertEqual(lora_prompt["90"]["inputs"]["strength_model"], 0.55)
            self.assertEqual(lora_prompt["6"]["inputs"]["model"], ["90", 0])
            self.assertIn("applied 1 selected LoRA", lora_inputs.usage_note)
            self.assertFalse(hasattr(lora_inputs, "_slopperly_comfy_workflow_mutator"))

            source = Path(tmp) / "source.png"
            ref = Path(tmp) / "ref.png"
            source.write_bytes(b"local flux source image")
            ref.write_bytes(b"local flux reference image")
            scene = SimpleNamespace(
                sequence_editor=SimpleNamespace(strips=[
                    SimpleNamespace(name="ref", type="IMAGE", filepath=str(ref)),
                ]),
                klein_strip_1="ref",
                klein_strip_2="",
                klein_strip_3="",
            )
            edit_inputs = self.base.ModelInputs(
                prompt="edit the local FLUX.2 Klein image",
                image=str(source),
                mode="img2img",
                width=1024,
                height=1024,
                steps=4,
                guidance=1.0,
                strength=0.65,
                seed=42005,
                frames=1,
            )

            RuntimeHandler.comfy_uploads = []
            with local_only_network():
                pipe = plugin.load(prefs, scene)
                output = plugin.generate(pipe, edit_inputs, scene, prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        edit_prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(len(RuntimeHandler.comfy_uploads), 2)
        self.assertEqual(edit_prompt["1"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(edit_prompt["19"]["inputs"]["image"], "uploaded_source_2.png")
        self.assertEqual(edit_prompt["3"]["class_type"], "UnetLoaderGGUF")
        self.assertEqual(edit_prompt["3"]["inputs"]["unet_name"], "flux-2-klein-4b-Q5_K_M.gguf")
        self.assertEqual(edit_prompt["2"]["inputs"]["width"], 1024)
        self.assertEqual(edit_prompt["14"]["inputs"]["steps"], 4)
        self.assertEqual(edit_prompt["12"]["inputs"]["noise_seed"], 42005)
        self.assertEqual(edit_prompt["11"]["inputs"]["positive"], ["27", 0])
        self.assertEqual(edit_prompt["22"]["inputs"]["latent"], ["21", 0])
        self.assertNotIn("24", edit_prompt)
        self.assertNotIn("25", edit_prompt)
        self.assertNotIn("26", edit_prompt)
        self.assertNotIn("latent", edit_prompt["27"]["inputs"])
        self.assertNotIn("latent", edit_prompt["28"]["inputs"])
        self.assertIn(b'filename="source.png"', RuntimeHandler.comfy_uploads[0])
        self.assertIn(b'filename="ref.png"', RuntimeHandler.comfy_uploads[1])
        self.assertIn("denoise/strength input", edit_inputs.usage_note)

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            ref = Path(tmp) / "ref.png"
            source.write_bytes(b"local flux source image")
            ref.write_bytes(b"local flux reference image")
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            scene = SimpleNamespace(
                sequence_editor=SimpleNamespace(strips=[
                    SimpleNamespace(name="ref", type="IMAGE", filepath=str(ref)),
                ]),
                klein_strip_1="ref",
                klein_strip_2="",
                klein_strip_3="",
            )
            lora_edit_inputs = self.base.ModelInputs(
                prompt="edit the local FLUX.2 Klein image with selected LoRA",
                image=str(source),
                mode="img2img",
                width=1024,
                height=1024,
                steps=4,
                guidance=1.0,
                strength=0.65,
                seed=42007,
                frames=1,
            )
            enabled = [
                SimpleNamespace(name="klein_edit_style.safetensors", weight_value=0.7, enabled=True)
            ]

            RuntimeHandler.comfy_uploads = []
            with local_only_network():
                pipe = plugin.load(prefs, scene, enabled_items=enabled)
                output = plugin.generate(pipe, lora_edit_inputs, scene, prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        lora_edit_prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(len(RuntimeHandler.comfy_uploads), 2)
        self.assertEqual(lora_edit_prompt["90"]["class_type"], "LoraLoaderModelOnly")
        self.assertEqual(lora_edit_prompt["90"]["inputs"]["model"], ["3", 0])
        self.assertEqual(lora_edit_prompt["90"]["inputs"]["lora_name"], "klein_edit_style.safetensors")
        self.assertEqual(lora_edit_prompt["90"]["inputs"]["strength_model"], 0.7)
        self.assertEqual(lora_edit_prompt["11"]["inputs"]["model"], ["90", 0])
        self.assertEqual(lora_edit_prompt["1"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(lora_edit_prompt["19"]["inputs"]["image"], "uploaded_source_2.png")
        self.assertNotIn("24", lora_edit_prompt)
        self.assertNotIn("25", lora_edit_prompt)
        self.assertNotIn("26", lora_edit_prompt)
        self.assertIn("applied 1 selected LoRA", lora_edit_inputs.usage_note)
        self.assertIn("denoise/strength input", lora_edit_inputs.usage_note)
        self.assertFalse(hasattr(lora_edit_inputs, "_slopperly_comfy_workflow_mutator"))

    def test_flux2_klein_9b_uses_comfy_t2i_and_edit_plugin_paths(self):
        module = load_plugin_module("image", "flux2_klein_9b")
        plugin = module.Flux2Klein9BPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            t2i_inputs = self.base.ModelInputs(
                prompt="local FLUX.2 Klein 9B text to image",
                width=1024,
                height=1024,
                steps=4,
                guidance=1.0,
                seed=42009,
                frames=1,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            RuntimeHandler.comfy_uploads = []
            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace())
                output = plugin.generate(pipe, t2i_inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

            t2i_prompt = RuntimeHandler.comfy_prompts[-1]
            self.assertEqual(RuntimeHandler.comfy_uploads, [])
            self.assertEqual(t2i_prompt["1"]["class_type"], "UnetLoaderGGUF")
            self.assertEqual(t2i_prompt["1"]["inputs"]["unet_name"], "flux-2-klein-9b-Q5_K_M.gguf")
            self.assertEqual(t2i_prompt["2"]["inputs"]["clip_name"], "qwen_3_8b_fp8mixed.safetensors")
            self.assertEqual(t2i_prompt["2"]["inputs"]["type"], "flux2")
            self.assertEqual(t2i_prompt["3"]["inputs"]["vae_name"], "full_encoder_small_decoder.safetensors")
            self.assertEqual(t2i_prompt["4"]["inputs"]["text"], "local FLUX.2 Klein 9B text to image")
            self.assertEqual(t2i_prompt["6"]["inputs"]["cfg"], 1.0)
            self.assertEqual(t2i_prompt["7"]["inputs"]["noise_seed"], 42009)
            self.assertEqual(t2i_prompt["9"]["inputs"]["steps"], 4)
            self.assertEqual(t2i_prompt["9"]["inputs"]["width"], 1024)
            self.assertEqual(t2i_prompt["10"]["inputs"]["height"], 1024)

            source = Path(tmp) / "source.png"
            ref = Path(tmp) / "ref.png"
            source.write_bytes(b"local flux source image")
            ref.write_bytes(b"local flux reference image")
            scene = SimpleNamespace(
                sequence_editor=SimpleNamespace(strips=[
                    SimpleNamespace(name="ref", type="IMAGE", filepath=str(ref)),
                ]),
                klein_strip_1="ref",
                klein_strip_2="",
                klein_strip_3="",
            )
            edit_inputs = self.base.ModelInputs(
                prompt="edit the local FLUX.2 Klein 9B image",
                image=str(source),
                mode="img2img",
                width=1024,
                height=1024,
                steps=4,
                guidance=1.0,
                strength=0.65,
                seed=42010,
                frames=1,
            )

            RuntimeHandler.comfy_uploads = []
            with local_only_network():
                pipe = plugin.load(prefs, scene)
                output = plugin.generate(pipe, edit_inputs, scene, prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        edit_prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(len(RuntimeHandler.comfy_uploads), 2)
        self.assertEqual(edit_prompt["1"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(edit_prompt["19"]["inputs"]["image"], "uploaded_source_2.png")
        self.assertEqual(edit_prompt["3"]["class_type"], "UnetLoaderGGUF")
        self.assertEqual(edit_prompt["3"]["inputs"]["unet_name"], "flux-2-klein-9b-Q5_K_M.gguf")
        self.assertEqual(edit_prompt["4"]["inputs"]["clip_name"], "qwen_3_8b_fp8mixed.safetensors")
        self.assertEqual(edit_prompt["5"]["inputs"]["vae_name"], "full_encoder_small_decoder.safetensors")
        self.assertEqual(edit_prompt["6"]["inputs"]["text"], "edit the local FLUX.2 Klein 9B image")
        self.assertEqual(edit_prompt["14"]["inputs"]["steps"], 4)
        self.assertEqual(edit_prompt["12"]["inputs"]["noise_seed"], 42010)
        self.assertEqual(edit_prompt["11"]["inputs"]["positive"], ["27", 0])
        self.assertEqual(edit_prompt["22"]["inputs"]["latent"], ["21", 0])
        self.assertNotIn("24", edit_prompt)
        self.assertNotIn("25", edit_prompt)
        self.assertNotIn("26", edit_prompt)
        self.assertNotIn("latent", edit_prompt["27"]["inputs"])
        self.assertNotIn("latent", edit_prompt["28"]["inputs"])
        self.assertIn(b'filename="source.png"', RuntimeHandler.comfy_uploads[0])
        self.assertIn(b'filename="ref.png"', RuntimeHandler.comfy_uploads[1])
        self.assertIn("denoise/strength input", edit_inputs.usage_note)

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            ref = Path(tmp) / "ref.png"
            source.write_bytes(b"local flux source image")
            ref.write_bytes(b"local flux reference image")
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            scene = SimpleNamespace(
                sequence_editor=SimpleNamespace(strips=[
                    SimpleNamespace(name="ref", type="IMAGE", filepath=str(ref)),
                ]),
                klein_strip_1="ref",
                klein_strip_2="",
                klein_strip_3="",
            )
            lora_edit_inputs = self.base.ModelInputs(
                prompt="edit the local FLUX.2 Klein 9B image with selected LoRA",
                image=str(source),
                mode="img2img",
                width=1024,
                height=1024,
                steps=4,
                guidance=1.0,
                strength=0.65,
                seed=42011,
                frames=1,
            )
            enabled = [
                SimpleNamespace(name="klein_9b_edit_style.safetensors", weight_value=0.6, enabled=True)
            ]

            RuntimeHandler.comfy_uploads = []
            with local_only_network():
                pipe = plugin.load(prefs, scene, enabled_items=enabled)
                output = plugin.generate(pipe, lora_edit_inputs, scene, prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        lora_edit_prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(len(RuntimeHandler.comfy_uploads), 2)
        self.assertEqual(lora_edit_prompt["90"]["class_type"], "LoraLoaderModelOnly")
        self.assertEqual(lora_edit_prompt["90"]["inputs"]["model"], ["3", 0])
        self.assertEqual(lora_edit_prompt["90"]["inputs"]["lora_name"], "klein_9b_edit_style.safetensors")
        self.assertEqual(lora_edit_prompt["90"]["inputs"]["strength_model"], 0.6)
        self.assertEqual(lora_edit_prompt["11"]["inputs"]["model"], ["90", 0])
        self.assertEqual(lora_edit_prompt["1"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(lora_edit_prompt["19"]["inputs"]["image"], "uploaded_source_2.png")
        self.assertNotIn("24", lora_edit_prompt)
        self.assertNotIn("25", lora_edit_prompt)
        self.assertNotIn("26", lora_edit_prompt)
        self.assertIn("applied 1 selected LoRA", lora_edit_inputs.usage_note)
        self.assertIn("denoise/strength input", lora_edit_inputs.usage_note)
        self.assertFalse(hasattr(lora_edit_inputs, "_slopperly_comfy_workflow_mutator"))

    def test_flux2_klein_schematic_uses_comfy_lora_plugin_path(self):
        module = load_plugin_module("image", "flux2_klein_9b_schematic")
        plugin = module.Flux2Klein9BSchematicPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            source.write_bytes(b"local schematic source image")
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(
                prompt="Generate an amodal segmentation mask of bicycle in the input image.",
                image=str(source),
                width=640,
                height=480,
                steps=20,
                guidance=5.0,
                seed=42011,
                frames=1,
            )
            scene = SimpleNamespace(
                klein_schematic_mode="AMODAL_SEG",
                klein_schematic_target="bicycle",
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            RuntimeHandler.comfy_uploads = []
            with local_only_network():
                pipe = plugin.load(prefs, scene)
                output = plugin.generate(pipe, inputs, scene, prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(len(RuntimeHandler.comfy_uploads), 1)
        self.assertEqual(prompt["1"]["inputs"]["image"], "uploaded_source.png")
        self.assertEqual(prompt["3"]["class_type"], "UnetLoaderGGUF")
        self.assertEqual(prompt["3"]["inputs"]["unet_name"], "flux-2-klein-base-9b-Q5_K_M.gguf")
        self.assertEqual(prompt["4"]["inputs"]["lora_name"], "flux2-klein-schematic-amodal-segmentation-lora.safetensors")
        self.assertEqual(prompt["4"]["inputs"]["strength_model"], 0.8)
        self.assertEqual(prompt["5"]["inputs"]["clip_name"], "qwen_3_8b.safetensors")
        self.assertEqual(prompt["6"]["inputs"]["vae_name"], "flux2-vae.safetensors")
        self.assertEqual(prompt["7"]["inputs"]["text"], "Generate an amodal segmentation mask of bicycle in the input image.")
        self.assertEqual(prompt["8"]["inputs"]["text"], "text, worst quality, blurry, ugly")
        self.assertEqual(prompt["12"]["inputs"]["cfg"], 5.0)
        self.assertEqual(prompt["13"]["inputs"]["noise_seed"], 42011)
        self.assertEqual(prompt["15"]["inputs"]["steps"], 20)
        self.assertEqual(prompt["15"]["inputs"]["width"], 640)
        self.assertEqual(prompt["16"]["inputs"]["height"], 480)
        self.assertIn(b'filename="source.png"', RuntimeHandler.comfy_uploads[0])

    def test_nucleus_image_uses_slopperly_comfy_node_plugin_path(self):
        module = load_plugin_module("image", "nucleus_moe")
        plugin = module.NucleusMoEPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(
                prompt="local Nucleus Image render",
                neg_prompt="text, watermark",
                width=1024,
                height=1024,
                steps=20,
                guidance=8.0,
                seed=530101,
                frames=1,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace())
                output = plugin.generate(pipe, inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.png_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["1"]["class_type"], "SlopperlyDiffusersImageGenerate")
        self.assertEqual(prompt["1"]["inputs"]["model_id"], "NucleusAI/Nucleus-Image")
        self.assertTrue(prompt["1"]["inputs"]["model_path"].endswith("models/diffusers/nucleus_image_base"))
        self.assertTrue(prompt["1"]["inputs"]["fp8_patch_path"].endswith("moe_fp8_patch.py"))
        self.assertTrue(prompt["1"]["inputs"]["fp8_weights_path"].endswith("Nucleus-Image-FP8.safetensors"))
        self.assertEqual(prompt["1"]["inputs"]["prompt"], "local Nucleus Image render")
        self.assertEqual(prompt["1"]["inputs"]["negative_prompt"], "text, watermark")
        self.assertEqual(prompt["1"]["inputs"]["width"], 1024)
        self.assertEqual(prompt["1"]["inputs"]["height"], 1024)
        self.assertEqual(prompt["1"]["inputs"]["steps"], 20)
        self.assertEqual(prompt["1"]["inputs"]["guidance"], 8.0)
        self.assertEqual(prompt["1"]["inputs"]["seed"], 530101)
        self.assertIs(prompt["1"]["inputs"]["local_files_only"], True)

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
        self.assertIn(b'name="image"; filename="clip.mp4"', RuntimeHandler.comfy_uploads[-1])

    def test_wan22_ti2v_5b_uses_local_comfy_plugin_path(self):
        module = load_plugin_module("video", "wan_ti2v_5b")
        plugin = module.WanTI2V5BPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            inputs = self.base.ModelInputs(
                prompt="local Wan TI2V motion",
                neg_prompt="text, watermark",
                width=1920,
                height=1080,
                frames=49,
                steps=25,
                guidance=5.0,
                seed=220502,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace())
                output = plugin.generate(pipe, inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.mp4_bytes)

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["1"]["inputs"]["unet_name"], "Wan2.2-TI2V-5B-Q5_K_M.gguf")
        self.assertEqual(prompt["3"]["inputs"]["clip_name"], "umt5_xxl_fp8_e4m3fn_scaled.safetensors")
        self.assertEqual(prompt["3"]["inputs"]["type"], "wan")
        self.assertEqual(prompt["4"]["inputs"]["vae_name"], "wan2.2_vae.safetensors")
        self.assertEqual(prompt["5"]["inputs"]["text"], "local Wan TI2V motion")
        self.assertEqual(prompt["6"]["inputs"]["text"], "text, watermark")
        self.assertEqual(prompt["7"]["inputs"]["width"], 1280)
        self.assertEqual(prompt["7"]["inputs"]["height"], 704)
        self.assertEqual(prompt["7"]["inputs"]["length"], 49)
        self.assertNotIn("start_image", prompt["7"]["inputs"])
        self.assertNotIn("8", prompt)
        self.assertEqual(prompt["9"]["inputs"]["seed"], 220502)
        self.assertEqual(prompt["9"]["inputs"]["steps"], 25)
        self.assertEqual(prompt["9"]["inputs"]["cfg"], 5.0)
        self.assertEqual(prompt["11"]["inputs"]["frame_rate"], 24.0)
        self.assertEqual(prompt["11"]["inputs"]["format"], "video/h264-mp4")

    def test_wan22_i2v_a14b_uses_local_comfy_gguf_plugin_path(self):
        module = load_plugin_module("video", "wan_i2v")
        plugin = module.WanI2VPlugin()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            source.write_bytes(b"local image fixture bytes")
            module.solve_path = lambda filename: str(Path(tmp) / filename)
            module._finalize_native_16fps_to_24fps = (
                lambda native_path, destination: Path(destination).write_bytes(Path(native_path).read_bytes())
            )
            inputs = self.base.ModelInputs(
                prompt="local Wan A14B image motion",
                neg_prompt="text, watermark",
                image=str(source),
                width=1920,
                height=1080,
                frames=25,
                steps=4,
                guidance=1.0,
                seed=220514,
            )
            prefs = SimpleNamespace(comfyui_url=self.base_url)

            with local_only_network():
                pipe = plugin.load(prefs, SimpleNamespace())
                output = plugin.generate(pipe, inputs, SimpleNamespace(), prefs)

            self.assertEqual(Path(output).read_bytes(), RuntimeHandler.mp4_bytes)
            self.assertTrue(output.endswith(".mp4"))

        prompt = RuntimeHandler.comfy_prompts[-1]
        self.assertEqual(prompt["7"]["inputs"]["unet_name"], "HighNoise/Wan2.2-I2V-A14B-HighNoise-Q5_K_M.gguf")
        self.assertEqual(prompt["8"]["inputs"]["unet_name"], "LowNoise/Wan2.2-I2V-A14B-LowNoise-Q5_K_M.gguf")
        self.assertEqual(prompt["7"]["inputs"]["compute_device"], "cuda:0")
        self.assertEqual(prompt["7"]["inputs"]["expert_mode_allocations"], "cuda:0,1gb;cpu,*")
        self.assertEqual(prompt["3"]["inputs"]["clip_name"], "umt5_xxl_wan_text_encoder.safetensors")
        self.assertEqual(prompt["3"]["inputs"]["type"], "wan")
        self.assertEqual(prompt["3"]["inputs"]["device"], "cpu")
        self.assertEqual(prompt["2"]["inputs"]["vae_name"], "wan_2.1_vae.safetensors")
        self.assertEqual(prompt["4"]["inputs"]["text"], "local Wan A14B image motion")
        self.assertEqual(prompt["5"]["inputs"]["text"], "text, watermark")
        self.assertEqual(prompt["6"]["inputs"]["width"], 1280)
        self.assertEqual(prompt["6"]["inputs"]["height"], 720)
        self.assertEqual(prompt["6"]["inputs"]["length"], 17)
        self.assertEqual(prompt["9"]["inputs"]["lora_name"], "wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors")
        self.assertEqual(prompt["10"]["inputs"]["lora_name"], "wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors")
        self.assertEqual(prompt["13"]["inputs"]["noise_seed"], 220514)
        self.assertEqual(prompt["13"]["inputs"]["steps"], 4)
        self.assertEqual(prompt["13"]["inputs"]["end_at_step"], 2)
        self.assertEqual(prompt["14"]["inputs"]["start_at_step"], 2)
        self.assertEqual(prompt["14"]["inputs"]["end_at_step"], 4)
        self.assertEqual(prompt["16"]["inputs"]["fps"], 16.0)
        self.assertEqual(prompt["17"]["inputs"]["format"], "mp4")
        self.assertEqual(prompt["17"]["inputs"]["codec"], "h264")
        self.assertIn(b'name="image"; filename="source.png"', RuntimeHandler.comfy_uploads[-1])
        self.assertIn("finalized the returned MP4 at 24fps", inputs.usage_note)

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
        self.assertTrue(
            prompt["5"]["inputs"]["filename_prefix"].startswith("slopperly_mmaudio_2468_")
        )
        self.assertIn(b'name="image"; filename="clip.mp4"', RuntimeHandler.comfy_uploads[-1])

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
        self.assertEqual(prompt["1"]["inputs"]["unet_name"], "acestep_v1.5_xl_turbo_bf16.safetensors")
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
        self.assertTrue(
            prompt["3"]["inputs"]["filename_prefix"].startswith("slopperly_foundation1_4242_")
        )

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
