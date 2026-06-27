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
            if "stem_" in parsed.query:
                return self._binary(self.audio_bytes, "audio/flac")
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
