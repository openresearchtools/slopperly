# Qwen Image Edit 2511 Multi-Reference GGUF

Local ComfyUI workflow for `Qwen/Qwen-Image-Edit-2511` through ComfyUI-GGUF and Comfy core Qwen image-edit nodes.

## Required Nodes

- `UnetLoaderGGUF` from `city96/ComfyUI-GGUF` at commit `6ea2651e7df66d7585f6ffee804b20e92fb38b8a`.
- ComfyUI core nodes from commit `603d891eaf045d726d9c23276b4428daf2977624`: `LoadImage`, `ImageScale`, `ModelSamplingAuraFlow`, `LoraLoaderModelOnly`, `CLIPLoader`, `VAELoader`, `TextEncodeQwenImageEditPlus`, `FluxKontextImageScale`, `FluxKontextMultiReferenceLatentMethod`, `VAEEncode`, `KSampler`, `VAEDecode`, and `SaveImage`.

The node names and auxiliary files are taken from Comfy-Org's `image_qwen_image_edit_2511` workflow template. The production Slopperly profile swaps the BF16 diffusion model for Unsloth's Q5_K_M GGUF artifact.

## Model Files

The Slopperly model manager must place these files under the owned Comfy model directory before generation:

- `models/diffusion_models/qwen-image-edit-2511-Q5_K_M.gguf` from `unsloth/Qwen-Image-Edit-2511-GGUF`
- `models/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors` from `Comfy-Org/HunyuanVideo_1.5_repackaged`
- `models/vae/qwen_image_vae.safetensors` from `Comfy-Org/Qwen-Image_ComfyUI`
- `models/loras/Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors` from `lightx2v/Qwen-Image-Edit-2511-Lightning`

Runtime generation is not allowed to download these artifacts. Use `python -m slopperly.models.download --model qwen_image_edit_2511_multi_gguf --accept-licenses` before certification.

## UI Parameter Mapping

- prompt -> positive `TextEncodeQwenImageEditPlus`, input `prompt`
- negative prompt -> negative `TextEncodeQwenImageEditPlus`, input `prompt`
- selected input strip / first reference -> upload to node `6`, input `image`
- optional second reference -> upload to node `9`, input `image`
- optional third reference -> upload to node `10`, input `image`
- empty second and third references are disconnected from both Qwen text-encode nodes and their `LoadImage` nodes are pruned before queueing.
- width and height -> node `7` `ImageScale`; the first reference image is resized before the Qwen/Kontext edit latent is encoded.
- steps, seed, sampler, scheduler, denoise, and local CFG -> node `16` `KSampler`
- model, text encoder, VAE, Lightning LoRA name, and Lightning LoRA strength are patchable profile inputs but default to the committed 16 GB profile.

The surrounding image-plugin frame and LoRA UI controls remain visible for project compatibility. This workflow emits one PNG per run. It applies the committed Lightning adapter; dynamic user LoRA injection is recorded as a follow-up because Comfy API workflows require concrete local LoRA filenames in committed graph nodes.

## Output Contract

Node `18` saves the decoded image as PNG with prefix `slopperly_qwen_image_edit`. The plugin returns the first Comfy image artifact path to the existing output insertion path.

For certification, one-reference and three-reference runs must produce readable PNG artifacts at the requested certified dimensions.

## Test Command

```bash
pytest tests/gpu/test_qwen_image_edit_2511.py --device cuda
```

## Expected Validation

- Comfy `/object_info` includes `UnetLoaderGGUF` and the required Comfy core Qwen/Kontext nodes.
- `workflow.api.json` validates as Comfy API format and contains no external inference URLs.
- The addon plugin path calls `QwenImageEditPlugin.load()` and `QwenImageEditPlugin.generate()`.
- One-reference and three-reference smoke payloads upload local image artifacts and return readable PNG files.
