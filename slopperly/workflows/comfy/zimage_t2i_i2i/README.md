# Z-Image Text-to-Image

Local ComfyUI workflow for `Tongyi-MAI/Z-Image` text-to-image generation using the official Z-Image template shape with a Q5 GGUF backbone.

## Required Nodes

- ComfyUI-GGUF from commit `fcf3c4c98baf3a6f78f5200b73d86436931c43fb`: `UnetLoaderGGUF`.
- ComfyUI core nodes from commit `603d891eaf045d726d9c23276b4428daf2977624`: `ModelSamplingAuraFlow`, `CLIPLoader`, `VAELoader`, `CLIPTextEncode`, `EmptySD3LatentImage`, `KSampler`, `VAEDecode`, and `SaveImage`.

The GGUF node pack must be installed in the owned Slopperly Comfy runtime.

## Model Files

The Slopperly model manager must place these files under the owned Comfy model directory before generation:

- `models/diffusion_models/z-image-Q5_K_M.gguf` from `unsloth/Z-Image-GGUF`
- `models/text_encoders/qwen_3_4b.safetensors` from `Comfy-Org/z_image_turbo`
- `models/vae/ae.safetensors` from `Comfy-Org/z_image_turbo`

Runtime generation is not allowed to download these artifacts. Use `python -m slopperly.models.download --model zimage_t2i_i2i --accept-licenses` before certification.

## UI Parameter Mapping

- prompt -> positive `CLIPTextEncode`, node `5`, input `text`
- negative prompt -> negative `CLIPTextEncode`, node `6`, input `text`
- width and height -> node `7` `EmptySD3LatentImage`
- steps, seed, CFG/guidance, sampler, scheduler, and denoise -> node `8` `KSampler`
- image input and strength are handled by the companion `zimage_t2i_i2i_img2img` workflow when the plugin receives `ModelInputs.mode == "img2img"`.
- model, text encoder, and VAE names are patchable profile inputs but default to the committed profile.

The surrounding image-plugin frame control remains visible for project compatibility. This workflow emits one PNG per run.

## Output Contract

Node `10` saves the decoded image as PNG with prefix `slopperly_zimage`. The plugin returns the first Comfy image artifact path to the existing output insertion path.

## Test Command

```bash
pytest tests/gpu/test_zimage.py --device cuda
```

## Expected Validation

- Comfy `/object_info` includes all listed GGUF and core node classes.
- `workflow.api.json` validates as Comfy API format and contains no external inference URLs.
- The addon plugin path calls `ZImagePlugin.load()` and `ZImagePlugin.generate()`.
- The smoke payload returns a readable 1024x1024 PNG file.
