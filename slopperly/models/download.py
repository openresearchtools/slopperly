"""Download/cache local model artifacts declared in Slopperly's registry."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from slopperly.config.registry import model_entries


GENERIC_FILE_MARKERS = (
    "model artifacts",
    "configured by",
    "downloaded by",
)
MOSS_TTS_NANO_LOGICAL_NAME = "moss_tts_nano_vllm_omni"
MOSS_AUDIO_TOKENIZER_AUX_ID = "moss_audio_tokenizer_nano"
MOSS_AUDIO_TOKENIZER_CONFIG_KEY = "audio_tokenizer_pretrained_name_or_path"
KONTEXT_RELIGHT_LOGICAL_NAME = "kontext_relight"
KONTEXT_RELIGHT_LORA_AUX_ID = "kontext_relight_lora"
KONTEXT_RELIGHT_RAW_LORA = "relighting-kontext-dev-lora-v3.safetensors"
KONTEXT_RELIGHT_COMFY_LORA = "relighting-kontext-dev-lora-v3-comfy.safetensors"
KONTEXT_RELIGHT_LORA_PREFIX = "base_model.model."
LUMINA2_LOGICAL_NAME = "lumina2_t2i"
LUMINA2_SOURCE_BF16 = "models/diffusion_models/lumina_2_model_bf16.safetensors"
LUMINA2_INTERMEDIATE_GGUF = "models/diffusion_models/lumina_2_model-BF16.gguf"
LUMINA2_Q5_GGUF = "models/diffusion_models/lumina_2_model-Q5_K_M.gguf"
LUMINA2_LLAMA_CPP_TAG = "b3962"
LUMINA2_LLAMA_CPP_REPO = "https://github.com/ggerganov/llama.cpp"
OMNIGEN_LOGICAL_NAME = "omnigen_v1_multi_image"


@dataclass
class DownloadResult:
    status: str
    model: str
    detail: str
    path: str = ""


def huggingface_repo_id(model_source: str) -> str | None:
    parsed = urlparse(str(model_source))
    if parsed.netloc.lower() not in {"huggingface.co", "www.huggingface.co"}:
        return None
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2:
        return None
    return "/".join(parts[:2])


def is_exact_file(value: str) -> bool:
    text = str(value).strip()
    if not text:
        return False
    lowered = text.lower()
    if any(marker in lowered for marker in GENERIC_FILE_MARKERS):
        return False
    return "/" not in text and "\\" not in text


def is_safe_relative_file(value: str) -> bool:
    text = str(value).strip()
    if not text:
        return False
    lowered = text.lower()
    if any(marker in lowered for marker in GENERIC_FILE_MARKERS):
        return False
    path = Path(text)
    if path.is_absolute() or ".." in path.parts:
        return False
    return True


def hf_file_source_and_target(value) -> tuple[str, str] | None:
    if isinstance(value, str):
        filename = value.strip()
        return (filename, filename) if filename else None
    if not isinstance(value, dict):
        return None
    source = str(value.get("path") or value.get("source") or "").strip()
    target = str(value.get("target") or Path(source).name).strip()
    if not source or not target:
        return None
    return source, target


def target_path(cache_root: Path, entry: dict, filename: str) -> Path:
    local_cache = Path(str(entry.get("local_cache_path") or entry.get("logical_name")))
    base = cache_root / local_cache
    if base.name == filename:
        return base
    return base / filename


def snapshot_path(cache_root: Path, entry: dict) -> Path:
    return cache_root / Path(str(entry.get("local_cache_path") or entry.get("logical_name")))


def has_gguf_header(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(4) == b"GGUF"
    except OSError:
        return False


def torchaudio_asset_key(entry: dict) -> str:
    params = entry.get("default_parameters") or {}
    if not isinstance(params, dict):
        return ""
    key = str(params.get("torchaudio_asset_key") or "").strip()
    return key if is_safe_relative_file(key) else ""


def torch_hub_dir() -> Path:
    try:
        import torch

        return Path(torch.hub.get_dir())
    except Exception:
        torch_home = Path(os.environ.get("TORCH_HOME", Path.home() / ".cache" / "torch"))
        return torch_home / "hub"


def torchaudio_cache_path(asset_key: str) -> Path:
    return torch_hub_dir() / "torchaudio" / Path(asset_key)


def mirror_torchaudio_asset(
    *,
    entry: dict,
    name: str,
    source_path: Path,
    dry_run: bool,
) -> DownloadResult | None:
    asset_key = torchaudio_asset_key(entry)
    if not asset_key:
        return None
    dest = torchaudio_cache_path(asset_key)
    if dry_run:
        return DownloadResult(
            "PLAN",
            name,
            f"would mirror Torchaudio asset key {asset_key}",
            str(dest),
        )
    if not source_path.is_file() or source_path.stat().st_size <= 0:
        return DownloadResult(
            "BLOCKED",
            name,
            f"Torchaudio source artifact is missing: {source_path}",
            str(dest),
        )
    if dest.is_file() and dest.stat().st_size == source_path.stat().st_size:
        return DownloadResult("PASS", name, "Torchaudio asset already mirrored", str(dest))
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, dest)
    return DownloadResult("PASS", name, "Torchaudio asset mirrored", str(dest))


def selected_entries(root: Path, names: list[str] | None = None) -> list[dict]:
    entries = model_entries(root)
    if not names:
        return entries
    wanted = set(names)
    return [entry for entry in entries if entry.get("logical_name") in wanted]


def auxiliary_entries(entry: dict) -> list[dict]:
    sources = entry.get("auxiliary_sources") or []
    return sources if isinstance(sources, list) else []


def artifact_entry_name(parent_name: str, entry: dict) -> str:
    artifact_id = str(entry.get("id") or entry.get("logical_name") or "auxiliary")
    return artifact_id if artifact_id == parent_name else f"{parent_name}:{artifact_id}"


def moss_audio_tokenizer_entry(entry: dict) -> dict | None:
    for auxiliary in auxiliary_entries(entry):
        if str(auxiliary.get("id") or "") == MOSS_AUDIO_TOKENIZER_AUX_ID:
            return auxiliary
    return None


def kontext_relight_lora_entry(entry: dict) -> dict | None:
    for auxiliary in auxiliary_entries(entry):
        if str(auxiliary.get("id") or "") == KONTEXT_RELIGHT_LORA_AUX_ID:
            return auxiliary
    return None


def rewrite_moss_tts_nano_config(
    *,
    entry: dict,
    name: str,
    cache_root: Path,
    dry_run: bool,
) -> DownloadResult | None:
    if str(entry.get("logical_name") or "") != MOSS_TTS_NANO_LOGICAL_NAME:
        return None
    tokenizer_entry = moss_audio_tokenizer_entry(entry)
    if tokenizer_entry is None:
        return DownloadResult("BLOCKED", name, "MOSS audio tokenizer auxiliary source is missing")

    model_config = snapshot_path(cache_root, entry) / "config.json"
    tokenizer_dir = snapshot_path(cache_root, tokenizer_entry)
    if dry_run:
        return DownloadResult(
            "PLAN",
            f"{name}:moss_local_tokenizer_config",
            f"would point MOSS config at local audio tokenizer {tokenizer_dir}",
            str(model_config),
        )
    if not model_config.is_file():
        return DownloadResult("BLOCKED", name, f"MOSS config is missing: {model_config}", str(model_config))
    if not (tokenizer_dir / "config.json").is_file():
        return DownloadResult(
            "BLOCKED",
            name,
            f"MOSS audio tokenizer snapshot is missing: {tokenizer_dir}",
            str(tokenizer_dir),
        )

    data = json.loads(model_config.read_text(encoding="utf-8"))
    desired = str(tokenizer_dir.resolve())
    if data.get(MOSS_AUDIO_TOKENIZER_CONFIG_KEY) == desired:
        return DownloadResult("PASS", name, "MOSS config already points at local audio tokenizer", str(model_config))
    data[MOSS_AUDIO_TOKENIZER_CONFIG_KEY] = desired
    model_config.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return DownloadResult("PASS", name, "MOSS config updated to local audio tokenizer", str(model_config))


def patch_omnigen_phi3_config(
    *,
    entry: dict,
    name: str,
    cache_root: Path,
    dry_run: bool,
) -> DownloadResult | None:
    if str(entry.get("logical_name") or "") != OMNIGEN_LOGICAL_NAME:
        return None

    postprocess_name = f"{name}:omnigen_phi3_rope_config"
    config_path = snapshot_path(cache_root, entry) / "config.json"
    if dry_run:
        return DownloadResult(
            "PLAN",
            postprocess_name,
            "would mirror top-level original_max_position_embeddings into OmniGen rope_scaling",
            str(config_path),
        )
    if not config_path.is_file():
        return DownloadResult(
            "BLOCKED",
            postprocess_name,
            f"OmniGen config is missing: {config_path}",
            str(config_path),
        )
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return DownloadResult(
            "BLOCKED",
            postprocess_name,
            f"could not read OmniGen config: {exc}",
            str(config_path),
        )

    rope_scaling = data.get("rope_scaling")
    original = data.get("original_max_position_embeddings")
    if not isinstance(rope_scaling, dict):
        return DownloadResult(
            "BLOCKED",
            postprocess_name,
            "OmniGen config rope_scaling is missing or invalid",
            str(config_path),
        )
    if not isinstance(original, int) or original <= 0:
        return DownloadResult(
            "BLOCKED",
            postprocess_name,
            "OmniGen config top-level original_max_position_embeddings is missing or invalid",
            str(config_path),
        )
    if rope_scaling.get("original_max_position_embeddings") == original:
        return DownloadResult(
            "PASS",
            postprocess_name,
            "OmniGen Phi3 rope config already compatible with current transformers",
            str(config_path),
        )

    rope_scaling["original_max_position_embeddings"] = original
    config_path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return DownloadResult(
        "PASS",
        postprocess_name,
        "OmniGen Phi3 rope config updated for current transformers",
        str(config_path),
    )


def normalize_kontext_relight_lora(
    *,
    entry: dict,
    name: str,
    cache_root: Path,
    dry_run: bool,
) -> DownloadResult | None:
    if str(entry.get("logical_name") or "") != KONTEXT_RELIGHT_LOGICAL_NAME:
        return None
    lora_entry = kontext_relight_lora_entry(entry)
    if lora_entry is None:
        return DownloadResult("BLOCKED", name, "Kontext Relight LoRA auxiliary source is missing")

    source_path = target_path(cache_root, lora_entry, KONTEXT_RELIGHT_RAW_LORA)
    dest_path = source_path.with_name(KONTEXT_RELIGHT_COMFY_LORA)
    postprocess_name = f"{name}:kontext_relight_lora_comfy"
    if dry_run:
        return DownloadResult(
            "PLAN",
            postprocess_name,
            f"would normalize Relight LoRA keys from {source_path.name}",
            str(dest_path),
        )
    if not source_path.is_file() or source_path.stat().st_size <= 0:
        return DownloadResult(
            "BLOCKED",
            postprocess_name,
            f"raw Relight LoRA is missing: {source_path}",
            str(source_path),
        )

    try:
        from safetensors import safe_open
        from safetensors.torch import save_file
    except Exception as exc:
        return DownloadResult(
            "BLOCKED",
            postprocess_name,
            f"safetensors with torch support is required to normalize Relight LoRA: {exc}",
            str(dest_path),
        )

    if dest_path.is_file() and dest_path.stat().st_size > 0:
        try:
            dest_is_fresh = dest_path.stat().st_mtime >= source_path.stat().st_mtime
            with safe_open(str(dest_path), framework="pt", device="cpu") as existing:
                existing_keys = list(existing.keys())
            if (
                dest_is_fresh
                and existing_keys
                and all(key.startswith("transformer.") for key in existing_keys)
                and not any(key.startswith("transformer.final_layer.linear.") for key in existing_keys)
                and not any(key.startswith(KONTEXT_RELIGHT_LORA_PREFIX) for key in existing_keys)
            ):
                return DownloadResult(
                    "PASS",
                    postprocess_name,
                    "Comfy-compatible Relight LoRA already exists",
                    str(dest_path),
                )
        except Exception:
            pass

    raw_tensors = {}
    try:
        with safe_open(str(source_path), framework="pt", device="cpu") as source:
            metadata = source.metadata() or {}
            for key in source.keys():
                normalized = key.removeprefix(KONTEXT_RELIGHT_LORA_PREFIX)
                if normalized in raw_tensors:
                    return DownloadResult(
                        "BLOCKED",
                        postprocess_name,
                        f"duplicate Relight LoRA key after normalization: {normalized}",
                        str(dest_path),
                    )
                raw_tensors[normalized] = source.get_tensor(key)
    except Exception as exc:
        return DownloadResult(
            "BLOCKED",
            postprocess_name,
            f"failed to read raw Relight LoRA: {exc}",
            str(source_path),
        )
    if not raw_tensors:
        return DownloadResult(
            "BLOCKED",
            postprocess_name,
            "raw Relight LoRA contains no tensors",
            str(source_path),
        )

    tensors: dict[str, object] = {}
    handled_bases: set[str] = set()

    def add_pair(source_base: str, target_base: str) -> DownloadResult | None:
        a_key = f"{source_base}.lora_A.weight"
        b_key = f"{source_base}.lora_B.weight"
        if a_key not in raw_tensors or b_key not in raw_tensors:
            return DownloadResult(
                "BLOCKED",
                postprocess_name,
                f"Relight LoRA pair is incomplete for {source_base}",
                str(source_path),
            )
        tensors[f"transformer.{target_base}.lora_A.weight"] = raw_tensors[a_key]
        tensors[f"transformer.{target_base}.lora_B.weight"] = raw_tensors[b_key]
        handled_bases.add(source_base)
        return None

    def add_split(source_base: str, targets: list[tuple[str, int]]) -> DownloadResult | None:
        a_key = f"{source_base}.lora_A.weight"
        b_key = f"{source_base}.lora_B.weight"
        if a_key not in raw_tensors or b_key not in raw_tensors:
            return DownloadResult(
                "BLOCKED",
                postprocess_name,
                f"Relight LoRA split pair is incomplete for {source_base}",
                str(source_path),
            )
        a_tensor = raw_tensors[a_key]
        b_tensor = raw_tensors[b_key]
        total = sum(size for _, size in targets)
        if getattr(b_tensor, "shape", (0,))[0] != total:
            return DownloadResult(
                "BLOCKED",
                postprocess_name,
                f"Relight LoRA split shape mismatch for {source_base}: expected {total}, got {getattr(b_tensor, 'shape', None)}",
                str(source_path),
            )
        offset = 0
        for target_base, size in targets:
            tensors[f"transformer.{target_base}.lora_A.weight"] = a_tensor.clone().contiguous()
            tensors[f"transformer.{target_base}.lora_B.weight"] = b_tensor[offset : offset + size, :].clone().contiguous()
            offset += size
        handled_bases.add(source_base)
        return None

    double_map = {
        "img_attn.proj": "attn.to_out.0",
        "img_mlp.0": "ff.net.0.proj",
        "img_mlp.2": "ff.net.2",
        "img_mod.lin": "norm1.linear",
        "txt_attn.proj": "attn.to_add_out",
        "txt_mlp.0": "ff_context.net.0.proj",
        "txt_mlp.2": "ff_context.net.2",
        "txt_mod.lin": "norm1_context.linear",
    }
    single_map = {
        "linear2": "proj_out",
        "modulation.lin": "norm.linear",
    }

    for source_base in sorted(
        key.removesuffix(".lora_A.weight") for key in raw_tensors if key.endswith(".lora_A.weight")
    ):
        parts = source_base.split(".")
        result: DownloadResult | None = None
        if len(parts) >= 3 and parts[0] == "double_blocks":
            index = parts[1]
            suffix = ".".join(parts[2:])
            if suffix == "img_attn.qkv":
                hidden = raw_tensors[f"{source_base}.lora_A.weight"].shape[1]
                result = add_split(
                    source_base,
                    [
                        (f"transformer_blocks.{index}.attn.to_q", hidden),
                        (f"transformer_blocks.{index}.attn.to_k", hidden),
                        (f"transformer_blocks.{index}.attn.to_v", hidden),
                    ],
                )
            elif suffix == "txt_attn.qkv":
                hidden = raw_tensors[f"{source_base}.lora_A.weight"].shape[1]
                result = add_split(
                    source_base,
                    [
                        (f"transformer_blocks.{index}.attn.add_q_proj", hidden),
                        (f"transformer_blocks.{index}.attn.add_k_proj", hidden),
                        (f"transformer_blocks.{index}.attn.add_v_proj", hidden),
                    ],
                )
            elif suffix in double_map:
                result = add_pair(source_base, f"transformer_blocks.{index}.{double_map[suffix]}")
        elif len(parts) >= 3 and parts[0] == "single_blocks":
            index = parts[1]
            suffix = ".".join(parts[2:])
            if suffix == "linear1":
                hidden = raw_tensors[f"{source_base}.lora_A.weight"].shape[1]
                result = add_split(
                    source_base,
                    [
                        (f"single_transformer_blocks.{index}.attn.to_q", hidden),
                        (f"single_transformer_blocks.{index}.attn.to_k", hidden),
                        (f"single_transformer_blocks.{index}.attn.to_v", hidden),
                        (f"single_transformer_blocks.{index}.proj_mlp", hidden * 4),
                    ],
                )
            elif suffix in single_map:
                result = add_pair(source_base, f"single_transformer_blocks.{index}.{single_map[suffix]}")
        elif source_base == "final_layer.linear":
            result = add_pair(source_base, "proj_out")

        if result is not None:
            return result

    expected_bases = {
        key.removesuffix(".lora_A.weight")
        for key in raw_tensors
        if key.endswith(".lora_A.weight")
    }
    unknown = sorted(expected_bases - handled_bases)
    if unknown:
        return DownloadResult(
            "BLOCKED",
            postprocess_name,
            f"unsupported Relight LoRA key pattern(s): {unknown[:5]}",
            str(source_path),
        )

    try:
        save_file(tensors, str(dest_path), metadata=metadata)
    except Exception as exc:
        return DownloadResult(
            "BLOCKED",
            postprocess_name,
            f"failed to write Comfy-compatible Relight LoRA: {exc}",
            str(dest_path),
        )
    return DownloadResult(
        "PASS",
        postprocess_name,
        f"normalized {len(tensors)} Relight LoRA keys for Comfy",
        str(dest_path),
    )


def build_lumina2_q5_gguf(
    *,
    entry: dict,
    name: str,
    cache_root: Path,
    root: Path,
    dry_run: bool,
) -> DownloadResult | None:
    if str(entry.get("logical_name") or "") != LUMINA2_LOGICAL_NAME:
        return None

    source_path = cache_root / LUMINA2_SOURCE_BF16
    intermediate_path = cache_root / LUMINA2_INTERMEDIATE_GGUF
    dest_path = cache_root / LUMINA2_Q5_GGUF
    postprocess_name = f"{name}:lumina2_q5_gguf"

    if dest_path.is_file() and has_gguf_header(dest_path):
        return DownloadResult("PASS", postprocess_name, "Lumina2 Q5 GGUF already exists", str(dest_path))

    if dry_run:
        if not source_path.is_file():
            return DownloadResult(
                "PLAN",
                postprocess_name,
                "would derive Lumina2 Q5 GGUF after downloading the original split BF16 diffusion file",
                str(dest_path),
            )
        return DownloadResult(
            "PLAN",
            postprocess_name,
            "would convert original Lumina2 BF16 diffusion weights to GGUF and quantize Q5_K_M",
            str(dest_path),
        )

    if not source_path.is_file() or source_path.stat().st_size <= 0:
        return DownloadResult(
            "BLOCKED",
            postprocess_name,
            f"original Lumina2 BF16 diffusion file is missing: {source_path}",
            str(source_path),
        )

    comfy_python = root / ".slopperly" / "runtimes" / "comfy-venv" / "bin" / "python"
    convert_script = (
        root
        / ".slopperly"
        / "runtimes"
        / "ComfyUI"
        / "custom_nodes"
        / "comfyui_gguf"
        / "tools"
        / "convert.py"
    )
    quantizer_status = ensure_lumina2_image_quantizer(
        root=root,
        name=postprocess_name,
        dry_run=dry_run,
    )
    if quantizer_status is not None:
        return quantizer_status
    quantize_bin = lumina2_image_quantizer_bin(root)
    for required in (comfy_python, convert_script, quantize_bin):
        if not required.exists():
            return DownloadResult(
                "BLOCKED",
                postprocess_name,
                f"required Lumina2 GGUF conversion tool is missing: {required}",
                str(dest_path),
            )

    intermediate_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if not intermediate_path.is_file() or not has_gguf_header(intermediate_path):
        try:
            subprocess.run(
                [
                    str(comfy_python),
                    str(convert_script),
                    "--src",
                    str(source_path),
                    "--dst",
                    str(intermediate_path),
                ],
                cwd=str(root),
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        except subprocess.CalledProcessError as exc:
            return DownloadResult(
                "BLOCKED",
                postprocess_name,
                f"Lumina2 BF16 GGUF conversion failed: {str(exc.stdout or exc)[:500]}",
                str(intermediate_path),
            )

    tmp_dest = dest_path.with_suffix(dest_path.suffix + ".tmp")
    try:
        subprocess.run(
            [
                str(quantize_bin),
                str(intermediate_path),
                str(tmp_dest),
                "Q5_K_M",
            ],
            cwd=str(root),
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as exc:
        return DownloadResult(
            "BLOCKED",
            postprocess_name,
            f"Lumina2 Q5_K_M quantization failed: {str(exc.stdout or exc)[:500]}",
            str(tmp_dest),
        )
    if not has_gguf_header(tmp_dest):
        return DownloadResult(
            "BLOCKED",
            postprocess_name,
            f"Lumina2 Q5_K_M quantization did not write a GGUF file: {tmp_dest}",
            str(tmp_dest),
        )
    os.replace(tmp_dest, dest_path)
    return DownloadResult(
        "PASS",
        postprocess_name,
        "derived Lumina2 Q5_K_M GGUF from original Comfy-Org split diffusion weights",
        str(dest_path),
    )


def lumina2_image_quantizer_source(root: Path) -> Path:
    return root / ".slopperly" / "runtimes" / "llama.cpp-image-quantize-src"


def lumina2_image_quantizer_bin(root: Path) -> Path:
    return lumina2_image_quantizer_source(root) / "build" / "bin" / "llama-quantize"


def ensure_lumina2_image_quantizer(
    *,
    root: Path,
    name: str,
    dry_run: bool,
) -> DownloadResult | None:
    quantize_bin = lumina2_image_quantizer_bin(root)
    if quantize_bin.is_file():
        return None
    if dry_run:
        return DownloadResult(
            "PLAN",
            name,
            f"would build patched ComfyUI-GGUF image quantizer from llama.cpp tag {LUMINA2_LLAMA_CPP_TAG}",
            str(quantize_bin),
        )

    git_bin = shutil.which("git")
    cmake_bin = shutil.which("cmake")
    if not git_bin or not cmake_bin:
        missing = "git" if not git_bin else "cmake"
        return DownloadResult("BLOCKED", name, f"{missing} is required to build the Lumina2 image quantizer", str(quantize_bin))

    source_dir = lumina2_image_quantizer_source(root)
    patch_path = (
        root
        / ".slopperly"
        / "runtimes"
        / "ComfyUI"
        / "custom_nodes"
        / "comfyui_gguf"
        / "tools"
        / "lcpp.patch"
    )
    if not patch_path.is_file():
        return DownloadResult("BLOCKED", name, f"ComfyUI-GGUF llama.cpp patch is missing: {patch_path}", str(patch_path))

    try:
        if not (source_dir / ".git").is_dir():
            source_dir.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                [
                    git_bin,
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    LUMINA2_LLAMA_CPP_TAG,
                    LUMINA2_LLAMA_CPP_REPO,
                    str(source_dir),
                ],
                cwd=str(root),
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )

        llama_cpp_source = source_dir / "src" / "llama.cpp"
        patch_needed = "LLM_ARCH_LUMINA2" not in llama_cpp_source.read_text(encoding="utf-8", errors="ignore")
        if patch_needed:
            subprocess.run(
                [git_bin, "apply", str(patch_path)],
                cwd=str(source_dir),
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        subprocess.run(
            [cmake_bin, "-B", "build", "-DLLAMA_CURL=OFF", "-DGGML_CUDA=OFF"],
            cwd=str(source_dir),
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        subprocess.run(
            [
                cmake_bin,
                "--build",
                "build",
                f"-j{os.cpu_count() or 2}",
                "--target",
                "llama-quantize",
            ],
            cwd=str(source_dir),
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        output = getattr(exc, "stdout", None) or str(exc)
        return DownloadResult(
            "BLOCKED",
            name,
            f"failed to build patched Lumina2 image quantizer: {str(output)[:500]}",
            str(quantize_bin),
        )
    if not quantize_bin.is_file():
        return DownloadResult("BLOCKED", name, f"patched Lumina2 image quantizer was not built: {quantize_bin}", str(quantize_bin))
    return None


def download_models(
    *,
    root: Path,
    profile: str,
    cache_root: Path,
    names: list[str] | None = None,
    accept_licenses: bool = False,
    dry_run: bool = False,
) -> list[DownloadResult]:
    results: list[DownloadResult] = []
    entries = selected_entries(root, names)
    seen = {entry.get("logical_name") for entry in entries}
    for missing in sorted(set(names or []) - seen):
        results.append(DownloadResult("BLOCKED", missing, "model not found in slopperly/config/models.yaml"))

    for entry in entries:
        name = entry.get("logical_name", "<unnamed>")
        results.extend(
            download_artifact_entry(
                entry=entry,
                name=name,
                cache_root=cache_root,
                profile=profile,
                accept_licenses=accept_licenses,
                dry_run=dry_run,
            )
        )
        for auxiliary in auxiliary_entries(entry):
            results.extend(
                download_artifact_entry(
                    entry=auxiliary,
                    name=artifact_entry_name(str(name), auxiliary),
                    cache_root=cache_root,
                    profile=profile,
                    accept_licenses=accept_licenses,
                    dry_run=dry_run,
                )
            )
        postprocess = rewrite_moss_tts_nano_config(
            entry=entry,
            name=str(name),
            cache_root=cache_root,
            dry_run=dry_run,
        )
        if postprocess:
            results.append(postprocess)
        postprocess = patch_omnigen_phi3_config(
            entry=entry,
            name=str(name),
            cache_root=cache_root,
            dry_run=dry_run,
        )
        if postprocess:
            results.append(postprocess)
        postprocess = normalize_kontext_relight_lora(
            entry=entry,
            name=str(name),
            cache_root=cache_root,
            dry_run=dry_run,
        )
        if postprocess:
            results.append(postprocess)
        postprocess = build_lumina2_q5_gguf(
            entry=entry,
            name=str(name),
            cache_root=cache_root,
            root=root,
            dry_run=dry_run,
        )
        if postprocess:
            results.append(postprocess)
    return results


def download_artifact_entry(
    *,
    entry: dict,
    name: str,
    cache_root: Path,
    profile: str,
    accept_licenses: bool,
    dry_run: bool,
) -> list[DownloadResult]:
    source = str(entry.get("model_source") or "")
    repo_id = huggingface_repo_id(source)
    download_mode = str(entry.get("download_mode") or "hf_file")
    required_files = entry.get("required_files") or []
    if not isinstance(required_files, list) or not required_files:
        return [DownloadResult("BLOCKED", name, "required_files is empty or invalid")]
    if not repo_id:
        return [
            DownloadResult(
                "BLOCKED",
                name,
                f"model_source is not a Hugging Face artifact URL: {source!r}",
            )
        ]

    if download_mode == "local_derived":
        return validate_local_derived_artifact(
            entry=entry,
            name=name,
            cache_root=cache_root,
            dry_run=dry_run,
        )
    if download_mode == "hf_snapshot":
        return download_snapshot(
            entry=entry,
            name=name,
            repo_id=repo_id,
            required_files=required_files,
            cache_root=cache_root,
            profile=profile,
            accept_licenses=accept_licenses,
            dry_run=dry_run,
        )
    if download_mode != "hf_file":
        return [
            DownloadResult(
                "BLOCKED",
                name,
                f"unsupported download_mode {download_mode!r}",
            )
        ]

    results: list[DownloadResult] = []
    for raw_file in required_files:
        file_spec = hf_file_source_and_target(raw_file)
        if file_spec is None:
            results.append(
                DownloadResult(
                    "BLOCKED",
                    name,
                    f"required file is not exact: {raw_file!r}",
                )
            )
            continue
        source_file, filename = file_spec
        dest = target_path(cache_root, entry, filename)
        if not is_safe_relative_file(source_file) or not is_exact_file(filename):
            results.append(
                DownloadResult(
                    "BLOCKED",
                    name,
                    f"required file is not exact: {raw_file!r}",
                    str(dest),
                )
            )
            continue
        if dest.is_file() and dest.stat().st_size > 0:
            results.append(DownloadResult("PASS", name, "artifact already cached", str(dest)))
            mirror = mirror_torchaudio_asset(
                entry=entry,
                name=name,
                source_path=dest,
                dry_run=False,
            )
            if mirror:
                results.append(mirror)
            continue
        if dry_run:
            results.append(
                DownloadResult(
                    "PLAN",
                    name,
                    f"would download {repo_id}/{source_file} for profile {profile}",
                    str(dest),
                )
            )
            mirror = mirror_torchaudio_asset(
                entry=entry,
                name=name,
                source_path=dest,
                dry_run=True,
            )
            if mirror:
                results.append(mirror)
            continue
        if not accept_licenses:
            results.append(
                DownloadResult(
                    "BLOCKED",
                    name,
                    "download requires --accept-licenses",
                    str(dest),
                )
            )
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            from huggingface_hub import hf_hub_download
        except Exception as exc:
            results.append(
                DownloadResult(
                    "BLOCKED",
                    name,
                    f"huggingface_hub is required for downloads: {exc}",
                    str(dest),
                )
            )
            continue
        try:
            downloaded = hf_hub_download(
                repo_id=repo_id,
                filename=source_file,
                local_dir=str(dest.parent),
                local_dir_use_symlinks=False,
            )
        except Exception as exc:
            results.append(
                DownloadResult(
                    "BLOCKED",
                    name,
                    f"download failed for {repo_id}/{filename}: {exc}",
                    str(dest),
                )
            )
            continue
        final_path = Path(downloaded)
        if final_path != dest and final_path.is_file() and not dest.exists():
            final_path.replace(dest)
        results.append(DownloadResult("PASS", name, "artifact downloaded", str(dest)))
        mirror = mirror_torchaudio_asset(
            entry=entry,
            name=name,
            source_path=dest,
            dry_run=False,
        )
        if mirror:
            results.append(mirror)
    return results


def validate_local_derived_artifact(
    *,
    entry: dict,
    name: str,
    cache_root: Path,
    dry_run: bool,
) -> list[DownloadResult]:
    results: list[DownloadResult] = []
    required_files = entry.get("required_files") or []
    for raw_file in required_files:
        filename = str(raw_file).strip()
        if not is_exact_file(filename):
            results.append(
                DownloadResult("BLOCKED", name, f"local derived file is not exact: {raw_file!r}")
            )
            continue
        dest = target_path(cache_root, entry, filename)
        if dest.is_file() and dest.stat().st_size > 0:
            if filename.lower().endswith(".gguf") and not has_gguf_header(dest):
                results.append(DownloadResult("BLOCKED", name, "derived GGUF has invalid header", str(dest)))
                continue
            results.append(DownloadResult("PASS", name, "derived artifact already cached", str(dest)))
            continue
        if dry_run:
            results.append(
                DownloadResult(
                    "PLAN",
                    name,
                    "derived artifact will be built from auxiliary local sources",
                    str(dest),
                )
            )
    return results


def download_snapshot(
    *,
    entry: dict,
    name: str,
    repo_id: str,
    required_files: list,
    cache_root: Path,
    profile: str,
    accept_licenses: bool,
    dry_run: bool,
) -> list[DownloadResult]:
    results: list[DownloadResult] = []
    dest = snapshot_path(cache_root, entry)
    invalid = [str(filename) for filename in required_files if not is_safe_relative_file(str(filename))]
    if invalid:
        return [
            DownloadResult(
                "BLOCKED",
                name,
                f"snapshot required_files contain unsafe or generic entries: {invalid!r}",
                str(dest),
            )
        ]
    missing = [
        str(filename)
        for filename in required_files
        if not (dest / str(filename)).is_file() or (dest / str(filename)).stat().st_size <= 0
    ]
    if not missing:
        return [DownloadResult("PASS", name, "snapshot already cached", str(dest))]
    if dry_run:
        return [
            DownloadResult(
                "PLAN",
                name,
                f"would snapshot_download {repo_id} for profile {profile}; missing evidence files: {missing}",
                str(dest),
            )
        ]
    if not accept_licenses:
        return [
            DownloadResult(
                "BLOCKED",
                name,
                "snapshot download requires --accept-licenses",
                str(dest),
            )
        ]
    try:
        from huggingface_hub import snapshot_download
    except Exception as exc:
        return [
            DownloadResult(
                "BLOCKED",
                name,
                f"huggingface_hub is required for snapshot downloads: {exc}",
                str(dest),
            )
        ]
    try:
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(dest),
            local_dir_use_symlinks=False,
            allow_patterns=entry.get("allow_patterns"),
            ignore_patterns=entry.get("ignore_patterns"),
        )
    except Exception as exc:
        return [
            DownloadResult(
                "BLOCKED",
                name,
                f"snapshot download failed for {repo_id}: {exc}",
                str(dest),
            )
        ]
    remaining = [
        str(filename)
        for filename in required_files
        if not (dest / str(filename)).is_file() or (dest / str(filename)).stat().st_size <= 0
    ]
    if remaining:
        return [
            DownloadResult(
                "BLOCKED",
                name,
                f"snapshot downloaded but required evidence files are missing: {remaining}",
                str(dest),
            )
        ]
    results.append(DownloadResult("PASS", name, "snapshot downloaded", str(dest)))
    return results


def print_results(results: list[DownloadResult]) -> None:
    for result in results:
        suffix = f" -> {result.path}" if result.path else ""
        print(f"{result.status} {result.model}: {result.detail}{suffix}")
    counts = {status: sum(1 for r in results if r.status == status) for status in {"PASS", "PLAN", "BLOCKED"}}
    print(
        "Model artifact records: "
        f"{counts['PASS']} cached/downloaded, {counts['PLAN']} planned, {counts['BLOCKED']} blocked."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download local model artifacts declared by Slopperly")
    parser.add_argument("--root", default=".")
    parser.add_argument("--profile", default="smoke_16gb")
    parser.add_argument("--cache-root", default=".slopperly/model-cache")
    parser.add_argument("--model", action="append", dest="models", help="logical model name; may be repeated")
    parser.add_argument("--accept-licenses", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    cache_root = (root / args.cache_root).resolve()
    results = download_models(
        root=root,
        profile=args.profile,
        cache_root=cache_root,
        names=args.models,
        accept_licenses=args.accept_licenses,
        dry_run=args.dry_run or args.report_only,
    )
    print_results(results)
    blocked = any(result.status == "BLOCKED" for result in results)
    return 0 if args.report_only or not blocked else 1


if __name__ == "__main__":
    raise SystemExit(main())
