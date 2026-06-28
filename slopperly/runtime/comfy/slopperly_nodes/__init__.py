"""Slopperly-owned ComfyUI custom nodes for local model migrations."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


class SlopperlyDiffusersImageGenerate:
    """Run a local diffusers text-to-image pipeline inside owned ComfyUI."""

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "generate"
    CATEGORY = "Slopperly/local"

    _pipeline_cache: dict[tuple[str, str, str, bool], Any] = {}

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_id": ("STRING", {"default": "NucleusAI/Nucleus-Image"}),
                "model_path": ("STRING", {"default": ""}),
                "fp8_patch_path": ("STRING", {"default": "models/diffusers/nucleus_image_fp8/moe_fp8_patch.py"}),
                "fp8_weights_path": ("STRING", {"default": "models/diffusers/nucleus_image_fp8/Nucleus-Image-FP8.safetensors"}),
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "negative_prompt": ("STRING", {"multiline": True, "default": ""}),
                "width": ("INT", {"default": 1024, "min": 64, "max": 4096, "step": 8}),
                "height": ("INT", {"default": 1024, "min": 64, "max": 4096, "step": 8}),
                "steps": ("INT", {"default": 20, "min": 1, "max": 150}),
                "guidance": ("FLOAT", {"default": 8.0, "min": 0.0, "max": 30.0, "step": 0.1}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2**63 - 1}),
                "local_files_only": ("BOOLEAN", {"default": True}),
            }
        }

    def generate(
        self,
        *,
        model_id: str,
        model_path: str,
        fp8_patch_path: str,
        fp8_weights_path: str,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        steps: int,
        guidance: float,
        seed: int,
        local_files_only: bool,
    ):
        import numpy as np
        import torch

        pipe = self._load_pipeline(
            model_id=model_id,
            model_path=model_path,
            fp8_patch_path=fp8_patch_path,
            fp8_weights_path=fp8_weights_path,
            local_files_only=bool(local_files_only),
        )
        generator = None
        if int(seed or 0) != 0:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            generator = torch.Generator(device=device).manual_seed(int(seed))

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        try:
            result = pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=int(steps),
                guidance_scale=float(guidance),
                height=int(height),
                width=int(width),
                generator=generator,
            ).images[0]
        finally:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        image = result.convert("RGB")
        array = np.asarray(image, dtype=np.float32) / 255.0
        tensor = torch.from_numpy(array)[None,]
        return (tensor,)

    @classmethod
    def _load_pipeline(
        cls,
        *,
        model_id: str,
        model_path: str,
        fp8_patch_path: str,
        fp8_weights_path: str,
        local_files_only: bool,
    ):
        import torch
        from diffusers import DiffusionPipeline

        source = _resolve_optional_path(model_path) or str(model_id)
        patch_path = _require_local_file(fp8_patch_path, "Nucleus FP8 patch")
        weights_path = _require_local_file(fp8_weights_path, "Nucleus FP8 weights")
        key = (source, str(patch_path), str(weights_path), bool(local_files_only))
        if key in cls._pipeline_cache:
            return cls._pipeline_cache[key]

        patch = _import_patch_module(patch_path)
        if hasattr(patch, "apply_patch"):
            patch.apply_patch()
        if not hasattr(patch, "load_fp8_safetensors_transformer"):
            raise RuntimeError(
                f"{patch_path} does not expose load_fp8_safetensors_transformer(); "
                "download the pinned Nucleus FP8 patch artifact with slopperly.models.download."
            )

        transformer = patch.load_fp8_safetensors_transformer(str(weights_path))
        pipe = DiffusionPipeline.from_pretrained(
            source,
            transformer=transformer,
            torch_dtype=torch.bfloat16,
            local_files_only=bool(local_files_only),
        )
        if torch.cuda.is_available():
            _enable_low_vram_offload(pipe)
            print(
                "SlopperlyDiffusersImageGenerate: "
                f"enabled {getattr(pipe, '_slopperly_offload_mode', 'unknown')} offload"
            )
        else:
            pipe.to("cpu")
        cls._pipeline_cache[key] = pipe
        return pipe


def _enable_low_vram_offload(pipe: Any) -> None:
    """Prefer leaf-level offload for Nucleus' large Qwen3-VL text encoder."""
    try:
        pipe.enable_sequential_cpu_offload()
        pipe._slopperly_offload_mode = "sequential_cpu"
        return
    except Exception as sequential_error:
        try:
            pipe.enable_model_cpu_offload()
            pipe._slopperly_offload_mode = "model_cpu"
            return
        except Exception as model_error:
            pipe._slopperly_offload_mode = (
                f"cuda_fallback_after_offload_errors: "
                f"{type(sequential_error).__name__}; {type(model_error).__name__}"
            )
            pipe.to("cuda")


def _import_patch_module(path: Path):
    module_name = "slopperly_nucleus_fp8_patch_" + str(abs(hash(str(path))))
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import Nucleus FP8 patch from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _require_local_file(value: str, description: str) -> Path:
    path = _resolve_optional_path(value)
    if path is None or not path.is_file():
        raise FileNotFoundError(
            f"{description} is missing at {value!r}. Run "
            "`python -m slopperly.models.download --model nucleus_image_t2i --accept-licenses` "
            "and keep generation in local-files-only mode."
        )
    return path


def _resolve_optional_path(value: str) -> Path | None:
    text = str(value or "").strip()
    if not text:
        return None
    raw = Path(text)
    candidates = [raw] if raw.is_absolute() else [Path.cwd() / raw]
    try:
        import folder_paths

        for attr in ("models_dir", "base_path"):
            base = getattr(folder_paths, attr, None)
            if base:
                candidates.append(Path(base) / raw)
    except Exception:
        pass
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return raw.resolve() if raw.is_absolute() else None


NODE_CLASS_MAPPINGS = {
    "SlopperlyDiffusersImageGenerate": SlopperlyDiffusersImageGenerate,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SlopperlyDiffusersImageGenerate": "Slopperly Diffusers Image Generate",
}
