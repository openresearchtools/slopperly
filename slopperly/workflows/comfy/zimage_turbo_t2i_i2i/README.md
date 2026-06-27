# Z-Image Turbo Text-to-Image

Local ComfyUI workflow for `Tongyi-MAI/Z-Image-Turbo` text-to-image generation using the official Comfy-Org Z-Image Turbo template shape.

## Required Nodes

- ComfyUI core nodes from commit `603d891eaf045d726d9c23276b4428daf2977624`: `UNETLoader`, `ModelSamplingAuraFlow`, `CLIPLoader`, `VAELoader`, `CLIPTextEncode`, `ConditioningZeroOut`, `EmptySD3LatentImage`, `KSampler`, `VAEDecode`, and `SaveImage`.

No custom Comfy node pack is required for this workflow.

## Model Files

The Slopperly model manager must place these files under the owned Comfy model directory before generation:

- `models/diffusion_models/z_image_turbo_bf16.safetensors` from `Comfy-Org/z_image_turbo`
- `models/text_encoders/qwen_3_4b.safetensors` from `Comfy-Org/z_image_turbo`
- `models/vae/ae.safetensors` from `Comfy-Org/z_image_turbo`

Runtime generation is not allowed to download these artifacts. Use `python -m slopperly.models.download --model zimage_turbo_t2i_i2i --accept-licenses` before certification.

## UI Parameter Mapping

- prompt -> `CLIPTextEncode`, node `5`, input `text`
- width and height -> node `7` `EmptySD3LatentImage`
- steps, seed, sampler, scheduler, denoise, and no-CFG value -> node `8` `KSampler`
- image input and strength are handled by the companion `zimage_turbo_t2i_i2i_img2img` workflow when the plugin receives `ModelInputs.mode == "img2img"`.
- model, text encoder, and VAE names are patchable profile inputs but default to the committed profile.

The official Turbo template uses `ConditioningZeroOut` for the negative path rather than a negative prompt. The negative prompt UI remains visible for compatibility, and the wrapper records a usage note if the user supplies one. This workflow emits one PNG per run.

## Output Contract

Node `10` saves the decoded image as PNG with prefix `slopperly_zimage_turbo`. The plugin returns the first Comfy image artifact path to the existing output insertion path.

## Test Command

```bash
pytest tests/gpu/test_zimage.py --device cuda
```

## Expected Validation

- Comfy `/object_info` includes all listed core node classes.
- `workflow.api.json` validates as Comfy API format and contains no external inference URLs.
- The addon plugin path calls `ZImageTurboPlugin.load()` and `ZImageTurboPlugin.generate()`.
- The smoke payload returns a readable 1024x1024 PNG file.
