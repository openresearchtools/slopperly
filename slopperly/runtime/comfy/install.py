"""Installer entry point for the Slopperly-owned ComfyUI runtime."""

from __future__ import annotations

import argparse
import shutil
import urllib.request
from pathlib import Path

from slopperly.config.registry import load_yaml
from slopperly.runtime.install_utils import (
    InstallStep,
    create_venv,
    git_checkout,
    has_blockers,
    pip_install,
    print_steps,
    venv_pip,
    write_manifest,
)


OMNIGEN_CODE_COMMIT = "d4752019ae16741dc3801fd4989432aad4c81a4f"
OMNIGEN_CODE_FILES = (
    "__init__.py",
    "model.py",
    "pipeline.py",
    "processor.py",
    "scheduler.py",
    "transformer.py",
    "utils.py",
)
OMNIGEN_LOCAL_ONLY_MARKER = "Slopperly local-only OmniGen dependency guard"
OMNIGEN_MEMORY_PRIORITY_MARKER = "Slopperly memory-priority OmniGen load guard"
OMNIGEN_VAE_LOCAL_ONLY_MARKER = "Slopperly local-only OmniGen VAE guard"
OMNIGEN_PHI3_API_MARKER = "Slopperly Phi3 decoder API compatibility guard"
OMNIGEN_CACHE_API_MARKER = "Slopperly OmniGen cache API compatibility guard"
OMNIGEN_CACHE_RETURN_MARKER = "Slopperly OmniGen first-pass cache return guard"


def install_comfy(
    *,
    runtime_root: Path,
    pin: Path,
    profile: str,
    dry_run: bool = False,
    skip_pip: bool = False,
    force: bool = False,
) -> list[InstallStep]:
    lock = load_yaml(pin)
    comfy = lock.get("comfyui") if isinstance(lock, dict) else None
    nodes = lock.get("custom_nodes") if isinstance(lock, dict) else None
    if not isinstance(comfy, dict) or not isinstance(nodes, list):
        return [InstallStep("BLOCKED", "nodes.lock", f"invalid lock file: {pin}")]

    runtime_root = runtime_root.resolve()
    comfy_path = runtime_root / "ComfyUI"
    venv_dir = runtime_root / "comfy-venv"
    pip = venv_pip(venv_dir)
    steps: list[InstallStep] = [
        InstallStep("PLAN" if dry_run else "PASS", "profile", f"ComfyUI install profile {profile}")
    ]
    steps.extend(
        git_checkout(
            repo=str(comfy.get("repo", "")),
            commit=str(comfy.get("commit", "")),
            destination=comfy_path,
            dry_run=dry_run,
            force=force,
        )
    )
    steps.append(create_venv(venv_dir, dry_run=dry_run))
    if not skip_pip:
        steps.extend(install_python_requirements(comfy_path, comfy, pip, dry_run=dry_run))

    custom_nodes_dir = comfy_path / "custom_nodes"
    for node in nodes:
        if not isinstance(node, dict):
            steps.append(InstallStep("BLOCKED", "custom_nodes", f"invalid node entry: {node!r}"))
            continue
        node_id = str(node.get("id", "")).strip()
        if not node_id:
            steps.append(InstallStep("BLOCKED", "custom_nodes", "node id is required"))
            continue
        node_path = custom_nodes_dir / node_id
        if str(node.get("source") or "git").strip().lower() == "local":
            steps.extend(
                install_local_custom_node(
                    node=node,
                    destination=node_path,
                    pin=pin,
                    dry_run=dry_run,
                    force=force,
                )
            )
        else:
            steps.extend(
                git_checkout(
                    repo=str(node.get("repo", "")),
                    commit=str(node.get("commit", "")),
                    destination=node_path,
                    dry_run=dry_run,
                    force=force,
                )
            )
        if not skip_pip:
            steps.extend(install_python_requirements(node_path, node, pip, dry_run=dry_run))

    steps.extend(apply_slopperly_post_install_patches(comfy_path, dry_run=dry_run))

    steps.append(
        write_manifest(
            runtime_root / "install-manifest.json",
            {
                "runtime": "comfyui",
                "profile": profile,
                "pin": str(pin),
                "comfyui": comfy,
                "custom_nodes": nodes,
                "runtime_path": str(comfy_path),
                "venv": str(venv_dir),
            },
            dry_run=dry_run,
        )
    )
    return steps


def apply_slopperly_post_install_patches(comfy_path: Path, *, dry_run: bool) -> list[InstallStep]:
    """Patch third-party nodes that perform network work during object_info."""

    return [
        disable_foundation1_object_info_autodownload(
            comfy_path / "custom_nodes" / "foundation_1" / "nodes" / "loader_node.py",
            dry_run=dry_run,
        ),
        *prepare_omnigen_local_only(
            comfy_path / "custom_nodes" / "omnigen",
            dry_run=dry_run,
        ),
        patch_comfyui_gguf_ideogram4_arch(
            comfy_path / "custom_nodes" / "comfyui_gguf",
            dry_run=dry_run,
        ),
    ]


def disable_foundation1_object_info_autodownload(path: Path, *, dry_run: bool) -> InstallStep:
    marker = "Slopperly disables upstream auto-download"
    if dry_run:
        return InstallStep(
            "PLAN",
            "foundation_1",
            f"patch {path} to keep /object_info local-only",
        )
    if not path.is_file():
        return InstallStep(
            "PASS",
            "foundation_1",
            f"Foundation-1 loader not present at {path}; no local-only patch needed",
        )
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return InstallStep(
            "PASS",
            "foundation_1",
            f"Foundation-1 object_info auto-download patch already present in {path}",
        )
    old = """        else:
            logger.info(
                "No Foundation-1 models found in models/stable_audio/. "
                "Attempting auto-download from HuggingFace..."
            )
            _download_foundation1()
            results = _do_scan()
"""
    new = """        else:
            logger.warning(
                "No Foundation-1 models found in models/stable_audio/. "
                "Slopperly disables upstream auto-download during /object_info "
                "and generation. Run python -m slopperly.models.download "
                "--model foundation1_music_loop --accept-licenses before "
                "certifying this workflow."
            )
"""
    if old not in text:
        return InstallStep(
            "BLOCKED",
            "foundation_1",
            f"could not find Foundation-1 auto-download block to patch in {path}",
        )
    path.write_text(text.replace(old, new), encoding="utf-8")
    return InstallStep(
        "PASS",
        "foundation_1",
        f"patched {path} to keep /object_info local-only",
    )


def patch_comfyui_gguf_ideogram4_arch(node_path: Path, *, dry_run: bool) -> InstallStep:
    """Teach the pinned ComfyUI-GGUF loader to detect Comfy core Ideogram 4 keys."""

    loader_path = node_path / "loader.py"
    convert_path = node_path / "tools" / "convert.py"
    marker = "class ModelIdeogram4(ModelTemplate):"
    if dry_run:
        return InstallStep(
            "PLAN",
            "comfyui_gguf-ideogram4",
            f"patch {node_path} to detect Ideogram 4 GGUF backbones",
        )
    if not loader_path.is_file() or not convert_path.is_file():
        return InstallStep(
            "PASS",
            "comfyui_gguf-ideogram4",
            f"ComfyUI-GGUF not present at {node_path}; no Ideogram 4 patch needed",
        )

    loader = loader_path.read_text(encoding="utf-8")
    convert = convert_path.read_text(encoding="utf-8")
    changed = False

    old_loader = (
        'IMG_ARCH_LIST = {"flux", "sd1", "sdxl", "sd3", "aura", "hidream", '
        '"cosmos", "ltxv", "hyvid", "wan", "lumina2", "qwen_image"}'
    )
    new_loader = (
        'IMG_ARCH_LIST = {"flux", "sd1", "sdxl", "sd3", "aura", "hidream", '
        '"cosmos", "ltxv", "hyvid", "wan", "lumina2", "qwen_image", "ideogram4"}'
    )
    if old_loader in loader:
        loader = loader.replace(old_loader, new_loader, 1)
        changed = True
    elif '"ideogram4"' not in loader:
        return InstallStep(
            "BLOCKED",
            "comfyui_gguf-ideogram4",
            f"could not find ComfyUI-GGUF IMG_ARCH_LIST to patch in {loader_path}",
        )

    if marker not in convert:
        old_convert = (
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
        new_convert = """class ModelLumina2(ModelTemplate):
    arch = "lumina2"
    keys_detect = [
        ("cap_embedder.1.weight", "context_refiner.0.attention.qkv.weight")
    ]

class ModelIdeogram4(ModelTemplate):
    arch = "ideogram4"
    keys_detect = [
        (
            "embed_image_indicator.weight",
            "layers.0.attention.qkv.weight",
            "final_layer.adaln_modulation.weight",
        )
    ]

arch_list = [ModelFlux, ModelSD3, ModelAura, ModelHiDream, CosmosPredict2,
             ModelLTXV, ModelHyVid, ModelWan, ModelSDXL, ModelSD1, ModelLumina2,
             ModelIdeogram4]
"""
        if old_convert not in convert:
            return InstallStep(
                "BLOCKED",
                "comfyui_gguf-ideogram4",
                f"could not find ComfyUI-GGUF arch list to patch in {convert_path}",
            )
        convert = convert.replace(old_convert, new_convert, 1)
        changed = True

    if changed:
        loader_path.write_text(loader, encoding="utf-8")
        convert_path.write_text(convert, encoding="utf-8")
        return InstallStep(
            "PASS",
            "comfyui_gguf-ideogram4",
            f"patched {node_path} to detect Ideogram 4 GGUF backbones",
        )
    return InstallStep(
        "PASS",
        "comfyui_gguf-ideogram4",
        f"Ideogram 4 GGUF detection patch already present in {node_path}",
    )


def prepare_omnigen_local_only(node_path: Path, *, dry_run: bool) -> list[InstallStep]:
    """Install pinned OmniGen code and disable the node's first-run downloads."""

    if dry_run:
        return [
            InstallStep(
                "PLAN",
                "omnigen-local-code",
                f"install VectorSpaceLab/OmniGen code {OMNIGEN_CODE_COMMIT} into {node_path / 'OmniGen'}",
            ),
            InstallStep(
                "PLAN",
                "omnigen-local-only",
                f"patch {node_path / 'AILab_OmniGen.py'} to reject generation-time downloads",
            ),
            InstallStep(
                "PLAN",
                "omnigen-memory-priority",
                f"patch {node_path / 'AILab_OmniGen.py'} to defer CUDA loads in Memory Priority mode",
            ),
            InstallStep(
                "PLAN",
                "omnigen-local-vae",
                f"patch {node_path / 'OmniGen' / 'pipeline.py'} to reject generation-time VAE downloads",
            ),
            InstallStep(
                "PLAN",
                "omnigen-phi3-api",
                f"patch {node_path / 'OmniGen' / 'transformer.py'} for current transformers Phi3 layers",
            ),
        ]
    if not node_path.is_dir():
        return [
            InstallStep(
                "PASS",
                "omnigen-local-code",
                f"OmniGen node not present at {node_path}; no local-only patch needed",
            )
        ]

    steps: list[InstallStep] = []
    code_dir = node_path / "OmniGen"
    missing = [name for name in OMNIGEN_CODE_FILES if not (code_dir / name).is_file()]
    manifest = code_dir / ".slopperly_code_commit"
    if missing or not manifest.is_file() or manifest.read_text(encoding="utf-8").strip() != OMNIGEN_CODE_COMMIT:
        code_dir.mkdir(parents=True, exist_ok=True)
        base_url = (
            "https://raw.githubusercontent.com/VectorSpaceLab/OmniGen/"
            f"{OMNIGEN_CODE_COMMIT}/OmniGen"
        )
        try:
            for filename in OMNIGEN_CODE_FILES:
                url = f"{base_url}/{filename}"
                with urllib.request.urlopen(url, timeout=60) as response:
                    (code_dir / filename).write_bytes(response.read())
            manifest.write_text(OMNIGEN_CODE_COMMIT + "\n", encoding="utf-8")
        except Exception as exc:
            steps.append(
                InstallStep(
                    "BLOCKED",
                    "omnigen-local-code",
                    f"could not install pinned OmniGen code into {code_dir}: {exc}",
                )
            )
        else:
            steps.append(
                InstallStep(
                    "PASS",
                    "omnigen-local-code",
                    f"installed VectorSpaceLab/OmniGen code {OMNIGEN_CODE_COMMIT} into {code_dir}",
                )
            )
    else:
        steps.append(
            InstallStep(
                "PASS",
                "omnigen-local-code",
                f"pinned OmniGen code already present in {code_dir}",
            )
        )

    steps.append(patch_omnigen_node_local_only(node_path / "AILab_OmniGen.py", dry_run=False))
    steps.append(patch_omnigen_transformers_cache_import(code_dir / "scheduler.py", dry_run=False))
    steps.append(patch_omnigen_cache_api(code_dir / "scheduler.py", dry_run=False))
    steps.append(patch_omnigen_cache_first_pass_return(code_dir / "scheduler.py", dry_run=False))
    steps.append(patch_omnigen_phi3_transformer_api(code_dir / "transformer.py", dry_run=False))
    steps.append(patch_omnigen_memory_priority_load(node_path / "AILab_OmniGen.py", dry_run=False))
    steps.append(patch_omnigen_pipeline_local_vae(code_dir / "pipeline.py", dry_run=False))
    return steps


def patch_omnigen_transformers_cache_import(path: Path, *, dry_run: bool) -> InstallStep:
    marker = "Slopperly removed stale OffloadedCache import"
    if dry_run:
        return InstallStep(
            "PLAN",
            "omnigen-transformers-cache",
            f"patch {path} for current transformers cache_utils",
        )
    if not path.is_file():
        return InstallStep(
            "BLOCKED",
            "omnigen-transformers-cache",
            f"OmniGen scheduler is missing: {path}",
        )
    source = path.read_text(encoding="utf-8")
    if marker in source:
        return InstallStep("PASS", "omnigen-transformers-cache", f"already patched {path}")
    old = "from transformers.cache_utils import Cache, DynamicCache, OffloadedCache"
    new = (
        "from transformers.cache_utils import Cache, DynamicCache\n"
        f"# {marker}; the pinned code provides OmniGenCache directly."
    )
    if old not in source:
        return InstallStep(
            "BLOCKED",
            "omnigen-transformers-cache",
            f"could not find stale OffloadedCache import in {path}",
        )
    path.write_text(source.replace(old, new, 1), encoding="utf-8")
    return InstallStep("PASS", "omnigen-transformers-cache", f"patched {path}")


def patch_omnigen_cache_api(path: Path, *, dry_run: bool) -> InstallStep:
    if dry_run:
        return InstallStep(
            "PLAN",
            "omnigen-cache-api",
            f"patch {path} for current transformers DynamicCache storage",
        )
    if not path.is_file():
        return InstallStep(
            "BLOCKED",
            "omnigen-cache-api",
            f"OmniGen scheduler is missing: {path}",
        )
    source = path.read_text(encoding="utf-8")
    if OMNIGEN_CACHE_API_MARKER in source:
        return InstallStep("PASS", "omnigen-cache-api", f"already patched {path}")

    old_init = """        self.num_tokens_for_img = num_tokens_for_img
        self.offload_kv_cache = offload_kv_cache

    def prefetch_layer(self, layer_idx: int):
"""
    new_init = f"""        self.num_tokens_for_img = num_tokens_for_img
        self.offload_kv_cache = offload_kv_cache
        # {OMNIGEN_CACHE_API_MARKER}: transformers>=5 stores DynamicCache data in layers,
        # while the pinned OmniGen scheduler still manages legacy key/value lists.
        self.key_cache = []
        self.value_cache = []
        self._seen_tokens = 0

    def __len__(self):
        return len(self.key_cache)

    def prefetch_layer(self, layer_idx: int):
"""
    if old_init not in source:
        return InstallStep(
            "BLOCKED",
            "omnigen-cache-api",
            f"could not find OmniGenCache initialization block in {path}",
        )
    path.write_text(source.replace(old_init, new_init, 1), encoding="utf-8")
    return InstallStep("PASS", "omnigen-cache-api", f"patched {path}")


def patch_omnigen_cache_first_pass_return(path: Path, *, dry_run: bool) -> InstallStep:
    if dry_run:
        return InstallStep(
            "PLAN",
            "omnigen-cache-first-pass",
            f"patch {path} to return full first-pass attention keys",
        )
    if not path.is_file():
        return InstallStep(
            "BLOCKED",
            "omnigen-cache-first-pass",
            f"OmniGen scheduler is missing: {path}",
        )
    source = path.read_text(encoding="utf-8")
    if OMNIGEN_CACHE_RETURN_MARKER in source:
        return InstallStep("PASS", "omnigen-cache-first-pass", f"already patched {path}")

    old = '''        elif len(self.key_cache) == layer_idx:
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
'''
    new = f'''        elif len(self.key_cache) == layer_idx:
            # {OMNIGEN_CACHE_RETURN_MARKER}: keep full first-pass K/V for SDPA,
            # but store only condition-token K/V for later image-token cache reuse.
            cache_key_states = key_states[..., :-(self.num_tokens_for_img+1), :]
            cache_value_states = value_states[..., :-(self.num_tokens_for_img+1), :]

             # Update the number of seen tokens
            if layer_idx == 0:
                self._seen_tokens += cache_key_states.shape[-2]

            self.key_cache.append(cache_key_states)
            self.value_cache.append(cache_value_states)
            self.original_device.append(cache_key_states.device)
            if self.offload_kv_cache:
                self.evict_previous_layer(layer_idx)
            return key_states, value_states
'''
    if old not in source:
        return InstallStep(
            "BLOCKED",
            "omnigen-cache-first-pass",
            f"could not find OmniGenCache first-pass update block in {path}",
        )
    path.write_text(source.replace(old, new, 1), encoding="utf-8")
    return InstallStep("PASS", "omnigen-cache-first-pass", f"patched {path}")


def patch_omnigen_memory_priority_load(path: Path, *, dry_run: bool) -> InstallStep:
    if dry_run:
        return InstallStep(
            "PLAN",
            "omnigen-memory-priority",
            f"patch {path} to defer CUDA loads in Memory Priority mode",
        )
    if not path.is_file():
        return InstallStep(
            "BLOCKED",
            "omnigen-memory-priority",
            f"OmniGen node script is missing: {path}",
        )
    source = path.read_text(encoding="utf-8")
    if OMNIGEN_MEMORY_PRIORITY_MARKER in source:
        return InstallStep("PASS", "omnigen-memory-priority", f"already patched {path}")

    signature = "    def _get_pipeline(self, model_precision, keep_in_vram):"
    if signature not in source:
        return InstallStep(
            "BLOCKED",
            "omnigen-memory-priority",
            f"could not find _get_pipeline signature in {path}",
        )
    source = source.replace(
        signature,
        (
            "    def _get_pipeline(self, model_precision, keep_in_vram, initial_device_move=True):\n"
            f"        # {OMNIGEN_MEMORY_PRIORITY_MARKER}"
        ),
        1,
    )

    old_block = '''                # Move to device safely
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
'''
    new_block = '''                # Move to device safely
                if initial_device_move:
                    try:
                        original_pipe = pipe
                        moved_pipe = pipe.to(device)
                        if moved_pipe is not None:
                            pipe = moved_pipe
                    except Exception as device_error:
                        print(f"Warning: Error moving pipeline to device: {device_error}")
                        pipe = original_pipe
                else:
                    pipe.device = torch.device(device)
                    if hasattr(pipe, "model"):
                        pipe.model.to("cpu")
                    if hasattr(pipe, "vae"):
                        pipe.vae.to("cpu")
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    print("Memory Priority mode: deferred OmniGen CUDA load until offloaded generation")
'''
    if old_block not in source:
        return InstallStep(
            "BLOCKED",
            "omnigen-memory-priority",
            f"could not find OmniGen device-move block in {path}",
        )
    source = source.replace(old_block, new_block, 1)

    old_call = "self._get_pipeline(model_precision, keep_in_vram)"
    new_call = "self._get_pipeline(model_precision, keep_in_vram, initial_device_move=not offload_model)"
    if old_call not in source:
        return InstallStep(
            "BLOCKED",
            "omnigen-memory-priority",
            f"could not find OmniGen pipeline call in {path}",
        )
    source = source.replace(old_call, new_call, 1)
    path.write_text(source, encoding="utf-8")
    return InstallStep("PASS", "omnigen-memory-priority", f"patched {path}")


def patch_omnigen_pipeline_local_vae(path: Path, *, dry_run: bool) -> InstallStep:
    if dry_run:
        return InstallStep(
            "PLAN",
            "omnigen-local-vae",
            f"patch {path} to reject generation-time VAE downloads",
        )
    if not path.is_file():
        return InstallStep(
            "BLOCKED",
            "omnigen-local-vae",
            f"OmniGen pipeline is missing: {path}",
        )
    source = path.read_text(encoding="utf-8")
    if OMNIGEN_VAE_LOCAL_ONLY_MARKER in source:
        return InstallStep("PASS", "omnigen-local-vae", f"already patched {path}")
    old = '''        else:
            logger.info(f"No VAE found in {model_name}, downloading stabilityai/sdxl-vae from HF")
            vae = AutoencoderKL.from_pretrained("stabilityai/sdxl-vae").to(device)
'''
    new = f'''        else:
            raise RuntimeError(
                "{OMNIGEN_VAE_LOCAL_ONLY_MARKER}: OmniGen VAE files are missing from the owned cache. "
                "Run python -m slopperly.models.download --model omnigen_v1_multi_image "
                "--cache-root .slopperly/runtimes/ComfyUI --accept-licenses before generation."
            )
'''
    if old not in source:
        return InstallStep(
            "BLOCKED",
            "omnigen-local-vae",
            f"could not find OmniGen VAE fallback in {path}",
        )
    path.write_text(source.replace(old, new, 1), encoding="utf-8")
    return InstallStep("PASS", "omnigen-local-vae", f"patched {path}")


def patch_omnigen_phi3_transformer_api(path: Path, *, dry_run: bool) -> InstallStep:
    if dry_run:
        return InstallStep(
            "PLAN",
            "omnigen-phi3-api",
            f"patch {path} for current transformers Phi3 layers",
        )
    if not path.is_file():
        return InstallStep(
            "BLOCKED",
            "omnigen-phi3-api",
            f"OmniGen transformer is missing: {path}",
        )
    source = path.read_text(encoding="utf-8")
    if OMNIGEN_PHI3_API_MARKER in source:
        return InstallStep("PASS", "omnigen-phi3-api", f"already patched {path}")

    old_hidden = "        hidden_states = inputs_embeds\n\n        # decoder layers"
    new_hidden = (
        "        hidden_states = inputs_embeds\n"
        f"        # {OMNIGEN_PHI3_API_MARKER}: transformers>=5 precomputes rotary embeddings.\n"
        "        position_embeddings = self.rotary_emb(hidden_states, position_ids=position_ids)\n\n"
        "        # decoder layers"
    )
    if old_hidden not in source:
        return InstallStep(
            "BLOCKED",
            "omnigen-phi3-api",
            f"could not find Phi3 hidden-state setup in {path}",
        )

    old_decoder = '''                layer_outputs = decoder_layer(
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
'''
    new_decoder = '''                layer_outputs = decoder_layer(
                    hidden_states,
                    attention_mask=attention_mask,
                    position_ids=position_ids,
                    past_key_values=past_key_values,
                    output_attentions=output_attentions,
                    use_cache=use_cache,
                    cache_position=cache_position,
                    position_embeddings=position_embeddings,
                )

            if isinstance(layer_outputs, tuple):
                hidden_states = layer_outputs[0]
                if use_cache and len(layer_outputs) > (2 if output_attentions else 1):
                    next_decoder_cache = layer_outputs[2 if output_attentions else 1]
                if output_attentions and len(layer_outputs) > 1:
                    all_self_attns += (layer_outputs[1],)
            else:
                hidden_states = layer_outputs
                if use_cache:
                    next_decoder_cache = past_key_values
'''
    if old_decoder not in source:
        return InstallStep(
            "BLOCKED",
            "omnigen-phi3-api",
            f"could not find Phi3 decoder-layer block in {path}",
        )
    source = source.replace(old_hidden, new_hidden, 1).replace(old_decoder, new_decoder, 1)
    path.write_text(source, encoding="utf-8")
    return InstallStep("PASS", "omnigen-phi3-api", f"patched {path}")


def patch_omnigen_node_local_only(path: Path, *, dry_run: bool) -> InstallStep:
    if dry_run:
        return InstallStep(
            "PLAN",
            "omnigen-local-only",
            f"patch {path} to reject generation-time downloads",
        )
    if not path.is_file():
        return InstallStep(
            "PASS",
            "omnigen-local-only",
            f"OmniGen node script not present at {path}; no local-only patch needed",
        )

    source = path.read_text(encoding="utf-8")
    if OMNIGEN_LOCAL_ONLY_MARKER in source:
        return InstallStep("PASS", "omnigen-local-only", f"already patched {path}")

    code_method = f'''    def _ensure_code_exists(self):
        """{OMNIGEN_LOCAL_ONLY_MARKER}: verify preinstalled code only."""
        required_files = {list(OMNIGEN_CODE_FILES)!r}
        missing = [
            name for name in required_files
            if not osp.exists(osp.join(Paths.OMNIGEN_CODE_DIR, name))
        ]
        if missing:
            raise RuntimeError(
                "OmniGen code is missing from the owned Comfy node install: "
                + ", ".join(missing)
                + ". Run python -m slopperly.runtime.comfy.install before certification."
            )
        if Paths.OMNIGEN_CODE_DIR not in sys.path:
            sys.path.append(Paths.OMNIGEN_CODE_DIR)
        print("OmniGen code verified from local Slopperly install")

'''
    model_method = f'''    def _ensure_model_exists(self, model_precision=None):
        """{OMNIGEN_LOCAL_ONLY_MARKER}: verify pre-downloaded model files only."""
        os.makedirs(Paths.OMNIGEN_DIR, exist_ok=True)
        if model_precision == "FP8" and not osp.exists(Paths.MODEL_FILE_FP8):
            raise RuntimeError(
                "OmniGen FP8 model is not installed in the owned Comfy cache. "
                "Run python -m slopperly.models.download --model omnigen_v1_multi_image "
                "--cache-root .slopperly/runtimes/ComfyUI --accept-licenses before certification."
            )
        if not osp.exists(Paths.MODEL_FILE_FP16):
            raise RuntimeError(
                "OmniGen FP16 model is not installed in the owned Comfy cache. "
                "Run python -m slopperly.models.download --model omnigen_v1_multi_image "
                "--cache-root .slopperly/runtimes/ComfyUI --accept-licenses before certification."
            )
        print("OmniGen models verified from local Slopperly cache")

'''
    try:
        source = _replace_python_method(
            source,
            method_name="_ensure_code_exists",
            next_method="_ensure_model_exists",
            replacement=code_method,
        )
        source = _replace_python_method(
            source,
            method_name="_ensure_model_exists",
            next_method="_setup_temp_dir",
            replacement=model_method,
        )
    except ValueError as exc:
        return InstallStep("BLOCKED", "omnigen-local-only", f"{path}: {exc}")

    path.write_text(source, encoding="utf-8")
    return InstallStep("PASS", "omnigen-local-only", f"patched {path}")


def _replace_python_method(
    source: str,
    *,
    method_name: str,
    next_method: str,
    replacement: str,
) -> str:
    start = source.find(f"    def {method_name}(")
    if start < 0:
        raise ValueError(f"could not find {method_name} method")
    end = source.find(f"\n    def {next_method}(", start)
    if end < 0:
        raise ValueError(f"could not find next method {next_method}")
    return source[:start] + replacement + source[end + 1 :]


def install_local_custom_node(
    *,
    node: dict,
    destination: Path,
    pin: Path,
    dry_run: bool,
    force: bool,
) -> list[InstallStep]:
    source = resolve_local_node_path(str(node.get("path") or ""), pin=pin)
    if source is None:
        return [InstallStep("BLOCKED", destination.name, "local node path is required")]
    if not source.is_dir():
        return [InstallStep("BLOCKED", destination.name, f"local node path does not exist: {source}")]
    if destination.exists():
        if not force:
            return [InstallStep("PASS", destination.name, f"local node already installed at {destination}")]
        if dry_run:
            return [
                InstallStep("PLAN", destination.name, f"remove {destination}"),
                InstallStep("PLAN", destination.name, f"copy {source} -> {destination}"),
            ]
        shutil.rmtree(destination)
    if dry_run:
        return [InstallStep("PLAN", destination.name, f"copy {source} -> {destination}")]
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
    return [InstallStep("PASS", destination.name, f"copied {source} -> {destination}")]


def resolve_local_node_path(raw_path: str, *, pin: Path) -> Path | None:
    text = raw_path.strip()
    if not text:
        return None
    path = Path(text)
    if path.is_absolute():
        return path.resolve()

    candidates = [Path.cwd() / path, pin.resolve().parent / path]
    try:
        candidates.append(pin.resolve().parents[3] / path)
    except IndexError:
        pass
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return (Path.cwd() / path).resolve()


def install_python_requirements(
    checkout: Path,
    recipe: dict,
    pip: Path,
    *,
    dry_run: bool,
) -> list[InstallStep]:
    steps: list[InstallStep] = []
    install_command = str(recipe.get("install_command") or "").strip()
    extras = recipe.get("python_extras") or []
    if install_command == "pip install -r requirements.txt":
        requirements = checkout / "requirements.txt"
        if dry_run or requirements.exists():
            steps.append(pip_install(pip, ["-r", str(requirements)], dry_run=dry_run))
        else:
            steps.append(
                InstallStep(
                    "PASS",
                    checkout.name,
                    f"no requirements.txt present at {requirements}; nothing to install",
                )
            )
    elif install_command:
        steps.append(
            InstallStep(
                "BLOCKED",
                checkout.name,
                f"unsupported install_command {install_command!r}; only pip requirements are allowed",
            )
        )
    if not isinstance(extras, list):
        steps.append(InstallStep("BLOCKED", checkout.name, "python_extras must be a list"))
    else:
        for package in extras:
            steps.append(pip_install(pip, [str(package)], dry_run=dry_run))
    return steps


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install Slopperly-owned ComfyUI")
    parser.add_argument("--runtime-root", default=".slopperly/runtimes")
    parser.add_argument("--pin", default="slopperly/runtime/comfy/nodes.lock.yaml")
    parser.add_argument("--profile", default="cuda13")
    parser.add_argument("--skip-pip", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    steps = install_comfy(
        runtime_root=Path(args.runtime_root),
        pin=Path(args.pin),
        profile=args.profile,
        dry_run=args.dry_run or args.report_only,
        skip_pip=args.skip_pip,
        force=args.force,
    )
    print_steps(steps, title="ComfyUI install")
    if has_blockers(steps) and not args.report_only:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
