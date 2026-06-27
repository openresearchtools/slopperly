# Qwen Image 2512 Text-to-Image GGUF

Local ComfyUI workflow for `Qwen/Qwen-Image-2512` text-to-image generation through ComfyUI-GGUF and Comfy core Qwen image nodes.

## Required Nodes

- `UnetLoaderGGUF` from `city96/ComfyUI-GGUF` at commit `6ea2651e7df66d7585f6ffee804b20e92fb38b8a`.
- ComfyUI core nodes from commit `603d891eaf045d726d9c23276b4428daf2977624`: `EmptySD3LatentImage`, `ModelSamplingAuraFlow`, `LoraLoaderModelOnly`, `CLIPLoader`, `VAELoader`, `CLIPTextEncode`, `KSampler`, `VAEDecode`, and `SaveImage`.

The graph follows Comfy-Org's Qwen Image 2512 template and replaces the upstream diffusion loader with Unsloth's Q5_K_M GGUF artifact for the 16 GB local profile.

## Model Files

The Slopperly model manager must place these files under the owned Comfy model directory before generation:

- `models/diffusion_models/qwen-image-2512-Q5_K_M.gguf` from `unsloth/Qwen-Image-2512-GGUF`
- `models/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors` from `Comfy-Org/Qwen-Image_ComfyUI`
- `models/vae/qwen_image_vae.safetensors` from `Comfy-Org/Qwen-Image_ComfyUI`
- `models/loras/Qwen-Image-2512-Lightning-4steps-V1.0-bf16.safetensors` from `lightx2v/Qwen-Image-2512-Lightning`

Runtime generation is not allowed to download these artifacts. Use `python -m slopperly.models.download --model qwen_image_2512_t2i_gguf --accept-licenses` before certification.

## UI Parameter Mapping

- prompt -> positive `CLIPTextEncode`, node `6`, input `text`
- negative prompt -> negative `CLIPTextEncode`, node `7`, input `text`
- width and height -> node `8` `EmptySD3LatentImage`
- steps, seed, sampler, scheduler, denoise, and local CFG -> node `9` `KSampler`
- model, text encoder, VAE, Lightning LoRA name, and Lightning LoRA strength are patchable profile inputs but default to the committed 16 GB profile.
- image input and strength are handled by the companion `qwen_image_2512_i2i_gguf` workflow when the plugin receives `ModelInputs.mode == "img2img"`.

The surrounding image-plugin frame and LoRA UI controls remain visible for project compatibility. This workflow emits one PNG per run. It applies the committed Lightning adapter; dynamic user LoRA injection is recorded as a follow-up because Comfy API workflows require concrete local LoRA filenames in committed graph nodes.

## Output Contract

Node `11` saves the decoded image as PNG with prefix `slopperly_qwen_image_2512`. The plugin returns the first Comfy image artifact path to the existing output insertion path.

For certification, the text-to-image run must produce a readable PNG artifact at the requested certified dimensions.

## Test Command

```bash
pytest tests/gpu/test_qwen_image_2512.py --device cuda
```

## Expected Validation

- Comfy `/object_info` includes `UnetLoaderGGUF` and the required Comfy core Qwen image nodes.
- `workflow.api.json` validates as Comfy API format and contains no external inference URLs.
- The addon plugin path calls `QwenImagePlugin.load()` and `QwenImagePlugin.generate()`.
- The smoke payload returns a readable 1024x1024 PNG file.
