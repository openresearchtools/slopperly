import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from slopperly.runtime.comfy import install as comfy_install_module
from slopperly.runtime.comfy.install import (
    disable_foundation1_object_info_autodownload,
    install_comfy,
    patch_omnigen_cache_api,
    patch_omnigen_cache_first_pass_return,
    patch_omnigen_memory_priority_load,
    patch_omnigen_pipeline_local_vae,
    patch_omnigen_phi3_transformer_api,
    patch_omnigen_transformers_cache_import,
    prepare_omnigen_local_only,
    patch_comfyui_gguf_ideogram4_arch,
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
        self.assertIn("OmniGen code", details)
        self.assertIn("install-manifest.json", details)

    def test_comfy_install_report_only_does_not_mutate_runtime(self):
        with patch.object(comfy_install_module, "install_comfy", return_value=[]) as mocked:
            result = comfy_install_module.main(["--report-only"])
        self.assertEqual(result, 0)
        self.assertTrue(mocked.call_args.kwargs["dry_run"])

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

    def test_comfyui_gguf_patch_detects_ideogram4_arch(self):
        loader_source = (
            'IMG_ARCH_LIST = {"flux", "sd1", "sdxl", "sd3", "aura", "hidream", '
            '"cosmos", "ltxv", "hyvid", "wan", "lumina2", "qwen_image"}\n'
        )
        convert_source = (
            "class ModelLumina2(ModelTemplate):\n"
            '    arch = "lumina2"\n'
            "    keys_detect = [\n"
            '        ("cap_embedder.1.weight", "context_refiner.0.attention.qkv.weight")\n'
            "    ]\n"
            "\n"
            "arch_list = [ModelFlux, ModelSD3, ModelAura, ModelHiDream, CosmosPredict2, "
            "\n"
            "             ModelLTXV, ModelHyVid, ModelWan, ModelSDXL, ModelSD1, ModelLumina2]\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            node_path = Path(tmp) / "comfyui_gguf"
            tools = node_path / "tools"
            tools.mkdir(parents=True)
            loader = node_path / "loader.py"
            convert = tools / "convert.py"
            loader.write_text(loader_source, encoding="utf-8")
            convert.write_text(convert_source, encoding="utf-8")

            step = patch_comfyui_gguf_ideogram4_arch(node_path, dry_run=False)
            patched_loader = loader.read_text(encoding="utf-8")
            patched_convert = convert.read_text(encoding="utf-8")

        self.assertEqual(step.status, "PASS")
        self.assertIn('"ideogram4"', patched_loader)
        self.assertIn("class ModelIdeogram4(ModelTemplate):", patched_convert)
        self.assertIn("embed_image_indicator.weight", patched_convert)
        self.assertIn("ModelIdeogram4", patched_convert)

    def test_omnigen_patch_installs_code_and_disables_first_run_downloads(self):
        source = '''class ailab_OmniGen:
    def _ensure_code_exists(self):
        """Ensure OmniGen code exists, download from GitHub if not"""
        try:
            if not osp.exists(Paths.OMNIGEN_CODE_DIR):
                print("Downloading OmniGen code from GitHub...")
                base_url = "https://raw.githubusercontent.com/VectorSpaceLab/OmniGen/main/OmniGen/"
                requests.get(base_url + "model.py")
        except Exception as e:
            raise RuntimeError(f"Failed to download OmniGen code: {str(e)}")

    def _ensure_model_exists(self, model_precision=None):
        """Ensure model file exists, download if not"""
        if not osp.exists(Paths.MODEL_FILE_FP16):
            snapshot_download(repo_id="silveroxides/OmniGen-V1")

    def _setup_temp_dir(self):
        pass

    def _get_pipeline(self, model_precision, keep_in_vram):
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            try:
                pipe = self.OmniGenPipeline.from_pretrained(Paths.OMNIGEN_DIR)
                # Move to device safely
                try:
                    original_pipe = pipe
                    pipe = pipe.to(device)
                    if pipe is None:
                        print("Warning: Pipeline.to(device) returned None, using original pipeline")
                        pipe = original_pipe
                        if hasattr(pipe, 'text_encoder'):
                            pipe.text_encoder = pipe.text_encoder.to(device)
                        if hasattr(pipe, 'unet'):
                            pipe.unet = pipe.unet.to(device)
                        if hasattr(pipe, 'vae'):
                            pipe.vae = pipe.vae.to(device)
                except Exception as device_error:
                    print(f"Warning: Error moving pipeline to device: {device_error}")
                    pipe = original_pipe
                return pipe
            except Exception:
                raise
        except Exception:
            raise

    def generation(self, preset_prompt, model_precision, prompt, memory_management, num_inference_steps, guidance_scale,
            img_guidance_scale, max_input_image_size, separate_cfg_infer,
            use_input_image_size_as_output, width, height, seed,
            image_1=None, image_2=None, image_3=None):
        keep_in_vram = (memory_management == "Speed Priority")
        offload_model = (memory_management == "Memory Priority")
        pipe = self._get_pipeline(model_precision, keep_in_vram)
        return pipe
'''

        class FakeResponse:
            def __init__(self, body: bytes):
                self.body = body

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return self.body

        def fake_urlopen(url, timeout=60):
            if str(url).endswith("/transformer.py"):
                return FakeResponse(
                    b'''class Phi3Transformer:
    def forward(self, inputs_embeds=None, attention_mask=None, position_ids=None, past_key_values=None,
        output_attentions=False, use_cache=True, cache_position=None, offload_model=False):
        hidden_states = inputs_embeds

        # decoder layers
        all_hidden_states = () if output_hidden_states else None
        all_self_attns = () if output_attentions else None
        next_decoder_cache = None

        for decoder_layer in self.layers:
            if self.gradient_checkpointing and self.training:
                pass
            else:
                if offload_model and not self.training:
                    self.get_offlaod_layer(layer_idx, device=inputs_embeds.device)
                layer_outputs = decoder_layer(
                    hidden_states,
                    attention_mask=attention_mask,
                    position_ids=position_ids,
                    past_key_value=past_key_values,
                    output_attentions=output_attentions,
                    use_cache=use_cache,
                    cache_position=cache_position,
                )

            hidden_states = layer_outputs[0]

            if use_cache:
                next_decoder_cache = layer_outputs[2 if output_attentions else 1]

            if output_attentions:
                all_self_attns += (layer_outputs[1],)
        return hidden_states
'''
                )
            if str(url).endswith("/pipeline.py"):
                return FakeResponse(
                    b'''class OmniGenPipeline:
    @classmethod
    def from_pretrained(cls, model_name, vae_path: str=None):
        if os.path.exists(os.path.join(model_name, "vae")):
            vae = AutoencoderKL.from_pretrained(os.path.join(model_name, "vae"))
        elif vae_path is not None:
            vae = AutoencoderKL.from_pretrained(vae_path).to(device)
        else:
            logger.info(f"No VAE found in {model_name}, downloading stabilityai/sdxl-vae from HF")
            vae = AutoencoderKL.from_pretrained("stabilityai/sdxl-vae").to(device)
        return cls(vae)
'''
                )
            if str(url).endswith("/scheduler.py"):
                return FakeResponse(
                    b'''from transformers.cache_utils import Cache, DynamicCache, OffloadedCache

class OmniGenCache(DynamicCache):
    def __init__(self, num_tokens_for_img: int, offload_kv_cache: bool=False) -> None:
        super().__init__()
        self.original_device = []
        self.prefetch_stream = torch.cuda.Stream()
        self.num_tokens_for_img = num_tokens_for_img
        self.offload_kv_cache = offload_kv_cache

    def prefetch_layer(self, layer_idx: int):
        pass

    def update(self, key_states, value_states, layer_idx, cache_kwargs=None):
        if len(self.key_cache) < layer_idx:
            raise ValueError("OffloadedCache does not support model usage where layers are skipped. Use DynamicCache.")
        elif len(self.key_cache) == layer_idx:
            # only cache the states for condition tokens
            key_states = key_states[..., :-(self.num_tokens_for_img+1), :]
            value_states = value_states[..., :-(self.num_tokens_for_img+1), :]

             # Update the number of seen tokens
            if layer_idx == 0:
                self._seen_tokens += key_states.shape[-2]

            self.key_cache.append(key_states)
            self.value_cache.append(value_states)
            self.original_device.append(key_states.device)
            if self.offload_kv_cache:
                self.evict_previous_layer(layer_idx)
            return self.key_cache[layer_idx], self.value_cache[layer_idx]
        else:
            return key_states, value_states
'''
                )
            return FakeResponse(b"# pinned omnigen code\n")

        with tempfile.TemporaryDirectory() as tmp:
            node_path = Path(tmp) / "omnigen"
            node_path.mkdir()
            script = node_path / "AILab_OmniGen.py"
            script.write_text(source, encoding="utf-8")
            with patch("slopperly.runtime.comfy.install.urllib.request.urlopen", side_effect=fake_urlopen) as mocked:
                steps = prepare_omnigen_local_only(node_path, dry_run=False)
            patched = script.read_text(encoding="utf-8")
            code_dir = node_path / "OmniGen"
            model_code_exists = (code_dir / "model.py").is_file()
            manifest_exists = (code_dir / ".slopperly_code_commit").is_file()

        self.assertFalse([step for step in steps if step.status == "BLOCKED"])
        self.assertGreaterEqual(mocked.call_count, 1)
        self.assertTrue(model_code_exists)
        self.assertTrue(manifest_exists)
        self.assertIn("Slopperly local-only OmniGen dependency guard", patched)
        self.assertIn("OmniGen FP16 model is not installed", patched)
        self.assertNotIn("requests.get(base_url", patched)
        self.assertNotIn('repo_id="silveroxides/OmniGen-V1"', patched)

    def test_omnigen_transformers_cache_patch_removes_stale_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            scheduler = Path(tmp) / "scheduler.py"
            scheduler.write_text(
                "from transformers.cache_utils import Cache, DynamicCache, OffloadedCache\n",
                encoding="utf-8",
            )
            step = patch_omnigen_transformers_cache_import(scheduler, dry_run=False)
            patched = scheduler.read_text(encoding="utf-8")

        self.assertEqual(step.status, "PASS")
        self.assertIn("from transformers.cache_utils import Cache, DynamicCache", patched)
        self.assertIn("Slopperly removed stale OffloadedCache import", patched)
        self.assertNotIn("OffloadedCache", patched.splitlines()[0])

    def test_omnigen_cache_api_patch_restores_legacy_storage(self):
        source = '''class OmniGenCache(DynamicCache):
    def __init__(self, num_tokens_for_img: int, offload_kv_cache: bool=False) -> None:
        super().__init__()
        self.original_device = []
        self.prefetch_stream = torch.cuda.Stream()
        self.num_tokens_for_img = num_tokens_for_img
        self.offload_kv_cache = offload_kv_cache

    def prefetch_layer(self, layer_idx: int):
        pass
'''
        with tempfile.TemporaryDirectory() as tmp:
            scheduler = Path(tmp) / "scheduler.py"
            scheduler.write_text(source, encoding="utf-8")
            step = patch_omnigen_cache_api(scheduler, dry_run=False)
            patched = scheduler.read_text(encoding="utf-8")

        self.assertEqual(step.status, "PASS")
        self.assertIn("Slopperly OmniGen cache API compatibility guard", patched)
        self.assertIn("self.key_cache = []", patched)
        self.assertIn("self.value_cache = []", patched)
        self.assertIn("self._seen_tokens = 0", patched)
        self.assertIn("def __len__(self):", patched)
        self.assertIn("return len(self.key_cache)", patched)

    def test_omnigen_cache_first_pass_patch_returns_full_states(self):
        source = '''class OmniGenCache(DynamicCache):
    def update(self, key_states, value_states, layer_idx, cache_kwargs=None):
        if len(self.key_cache) < layer_idx:
            raise ValueError("OffloadedCache does not support model usage where layers are skipped. Use DynamicCache.")
        elif len(self.key_cache) == layer_idx:
            # only cache the states for condition tokens
            key_states = key_states[..., :-(self.num_tokens_for_img+1), :]
            value_states = value_states[..., :-(self.num_tokens_for_img+1), :]

             # Update the number of seen tokens
            if layer_idx == 0:
                self._seen_tokens += key_states.shape[-2]

            self.key_cache.append(key_states)
            self.value_cache.append(value_states)
            self.original_device.append(key_states.device)
            if self.offload_kv_cache:
                self.evict_previous_layer(layer_idx)
            return self.key_cache[layer_idx], self.value_cache[layer_idx]
        else:
            return key_states, value_states
'''
        with tempfile.TemporaryDirectory() as tmp:
            scheduler = Path(tmp) / "scheduler.py"
            scheduler.write_text(source, encoding="utf-8")
            step = patch_omnigen_cache_first_pass_return(scheduler, dry_run=False)
            patched = scheduler.read_text(encoding="utf-8")

        self.assertEqual(step.status, "PASS")
        self.assertIn("Slopperly OmniGen first-pass cache return guard", patched)
        self.assertIn("cache_key_states = key_states", patched)
        self.assertIn("self.key_cache.append(cache_key_states)", patched)
        self.assertIn("return key_states, value_states", patched)

    def test_omnigen_memory_priority_patch_defers_initial_cuda_move(self):
        source = '''class ailab_OmniGen:
    def _get_pipeline(self, model_precision, keep_in_vram):
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            try:
                pipe = self.OmniGenPipeline.from_pretrained(Paths.OMNIGEN_DIR)
                # Move to device safely
                try:
                    original_pipe = pipe
                    pipe = pipe.to(device)
                    if pipe is None:
                        print("Warning: Pipeline.to(device) returned None, using original pipeline")
                        pipe = original_pipe
                        if hasattr(pipe, 'text_encoder'):
                            pipe.text_encoder = pipe.text_encoder.to(device)
                        if hasattr(pipe, 'unet'):
                            pipe.unet = pipe.unet.to(device)
                        if hasattr(pipe, 'vae'):
                            pipe.vae = pipe.vae.to(device)
                except Exception as device_error:
                    print(f"Warning: Error moving pipeline to device: {device_error}")
                    pipe = original_pipe
                return pipe
            except Exception:
                raise
        except Exception:
            raise

    def generation(self, preset_prompt, model_precision, prompt, memory_management, num_inference_steps, guidance_scale,
            img_guidance_scale, max_input_image_size, separate_cfg_infer,
            use_input_image_size_as_output, width, height, seed,
            image_1=None, image_2=None, image_3=None):
        keep_in_vram = (memory_management == "Speed Priority")
        offload_model = (memory_management == "Memory Priority")
        pipe = self._get_pipeline(model_precision, keep_in_vram)
        return pipe
'''
        with tempfile.TemporaryDirectory() as tmp:
            node = Path(tmp) / "AILab_OmniGen.py"
            node.write_text(source, encoding="utf-8")
            step = patch_omnigen_memory_priority_load(node, dry_run=False)
            patched = node.read_text(encoding="utf-8")

        self.assertEqual(step.status, "PASS")
        self.assertIn("Slopperly memory-priority OmniGen load guard", patched)
        self.assertIn("initial_device_move=not offload_model", patched)
        self.assertIn("deferred OmniGen CUDA load", patched)

    def test_omnigen_pipeline_vae_patch_rejects_download_fallback(self):
        source = '''class OmniGenPipeline:
    @classmethod
    def from_pretrained(cls, model_name, vae_path: str=None):
        if os.path.exists(os.path.join(model_name, "vae")):
            vae = AutoencoderKL.from_pretrained(os.path.join(model_name, "vae"))
        elif vae_path is not None:
            vae = AutoencoderKL.from_pretrained(vae_path).to(device)
        else:
            logger.info(f"No VAE found in {model_name}, downloading stabilityai/sdxl-vae from HF")
            vae = AutoencoderKL.from_pretrained("stabilityai/sdxl-vae").to(device)
        return cls(vae)
'''
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = Path(tmp) / "pipeline.py"
            pipeline.write_text(source, encoding="utf-8")
            step = patch_omnigen_pipeline_local_vae(pipeline, dry_run=False)
            patched = pipeline.read_text(encoding="utf-8")

        self.assertEqual(step.status, "PASS")
        self.assertIn("Slopperly local-only OmniGen VAE guard", patched)
        self.assertNotIn("stabilityai/sdxl-vae", patched.split("raise RuntimeError", 1)[0])

    def test_omnigen_phi3_transformer_patch_adds_position_embeddings(self):
        source = '''class Phi3Transformer:
    def forward(self, inputs_embeds=None, attention_mask=None, position_ids=None, past_key_values=None,
        output_attentions=False, use_cache=True, cache_position=None, offload_model=False):
        hidden_states = inputs_embeds

        # decoder layers
        all_hidden_states = () if output_hidden_states else None
        all_self_attns = () if output_attentions else None
        next_decoder_cache = None

        for decoder_layer in self.layers:
            if self.gradient_checkpointing and self.training:
                pass
            else:
                if offload_model and not self.training:
                    self.get_offlaod_layer(layer_idx, device=inputs_embeds.device)
                layer_outputs = decoder_layer(
                    hidden_states,
                    attention_mask=attention_mask,
                    position_ids=position_ids,
                    past_key_value=past_key_values,
                    output_attentions=output_attentions,
                    use_cache=use_cache,
                    cache_position=cache_position,
                )

            hidden_states = layer_outputs[0]

            if use_cache:
                next_decoder_cache = layer_outputs[2 if output_attentions else 1]

            if output_attentions:
                all_self_attns += (layer_outputs[1],)
        return hidden_states
'''
        with tempfile.TemporaryDirectory() as tmp:
            transformer = Path(tmp) / "transformer.py"
            transformer.write_text(source, encoding="utf-8")
            step = patch_omnigen_phi3_transformer_api(transformer, dry_run=False)
            patched = transformer.read_text(encoding="utf-8")

        self.assertEqual(step.status, "PASS")
        self.assertIn("Slopperly Phi3 decoder API compatibility guard", patched)
        self.assertIn("position_embeddings = self.rotary_emb", patched)
        self.assertIn("past_key_values=past_key_values", patched)
        self.assertIn("position_embeddings=position_embeddings", patched)
        self.assertIn("isinstance(layer_outputs, tuple)", patched)

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
