# anima_t2i_i2i_img2img

Local ComfyUI img2img workflow pack for the existing `mrfatso/anima-preview3-diffusers` Anima plugin, using the Q5 GGUF Anima Preview 3 backbone through ComfyUI-GGUF.

## Existing Addon Function

- Current plugin/function: `models_plugins/image/anima.py`.
- Runtime: Slopperly-owned ComfyUI.
- API workflow: `workflow.api.json`.
- Editable workflow: `workflow.editable.json`.

## Required Nodes

- `UnetLoaderGGUF`
- `CLIPLoader`
- `VAELoader`
- `LoadImage`
- `ImageScale`
- `VAEEncode`
- `CLIPTextEncode`
- `KSampler`
- `VAEDecode`
- `SaveImage`

`UnetLoaderGGUF` comes from the pinned ComfyUI-GGUF node pack. The remaining nodes are ComfyUI core node classes from pinned ComfyUI commit `603d891eaf045d726d9c23276b4428daf2977624`.

## Model Files

- `models/diffusion_models/anima-preview3-base-Q5_K_M.gguf`
- `models/text_encoders/qwen_3_06b_base.safetensors`
- `models/vae/qwen_image_vae.safetensors`

The GGUF backbone is sourced from `Bedovyy/Anima-GGUF`. The text encoder and VAE are sourced from `circlestone-labs/Anima`, preserving the Anima Preview 3 family instead of replacing it with an unrelated model.

## UI Parameter Mapping

- `prompt` -> node `7`, input `text`
- `negative_prompt` -> node `8`, input `text`
- selected image strip -> upload to Comfy input storage, then patch node `4`, input `image`
- `width` -> node `5`, input `width`
- `height` -> node `5`, input `height`
- `steps` -> node `9`, input `steps`
- `guidance` -> node `9`, input `cfg`
- `strength` -> plugin-computed `anima_denoise = 1.0 - strength`, then node `9`, input `denoise`
- `seed` -> node `9`, input `seed`
- Anima model file -> node `1`, input `unet_name`
- Anima text encoder -> node `2`, input `clip_name`
- Anima VAE -> node `3`, input `vae_name`
- sampler/scheduler defaults -> node `9`, inputs `sampler_name` and `scheduler`

Selected project LoRAs are inserted dynamically before `KSampler` with one `LoraLoaderModelOnly` node per selected filename/weight.

## Output Contract

Node `11` saves a PNG image. The plugin path returns the resulting local PNG path and downstream Blender insertion continues to use the existing generated-file behavior.

## Test Command

```bash
pytest tests/gpu/test_anima.py --device cuda
```

## Expected Validation

- Comfy `/object_info` includes all required node classes.
- `workflow.api.json` validates as Comfy API format.
- The addon plugin path submits this workflow through `SlopperlyRuntimeGateway`.
- PIL can open the output PNG and dimensions match the requested size.
