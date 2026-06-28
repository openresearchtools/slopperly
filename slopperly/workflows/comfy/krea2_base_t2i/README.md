# krea2_base_t2i

Local ComfyUI text-to-image workflow pack for the existing `ethanfel/Krea-2-Base-Diffusers` Krea 2 plugin.

## Existing Addon Function

- Current plugin/function: `models_plugins/image/_krea2_base.py`.
- Runtime: Slopperly-owned ComfyUI.
- API workflow: `workflow.api.json`.
- Editable workflow: `workflow.editable.json`.

## Required Nodes

- `UnetLoaderGGUF`
- `CLIPLoader`
- `VAELoader`
- `TextGenerate`
- `CLIPTextEncode`
- `EmptyLatentImage`
- `KSampler`
- `VAEDecode`
- `SaveImage`

The workflow follows the official Krea-2 local Comfy template shape while loading the RAW/base Q5 GGUF diffusion backbone through pinned ComfyUI-GGUF.

## Model Files

- `models/diffusion_models/krea2_raw-Q5_K_M.gguf`
- `models/text_encoders/qwen3vl_4b_fp8_scaled.safetensors`
- `models/vae/qwen_image_vae.safetensors`

The GGUF diffusion backbone is sourced from `vantagewithai/Krea-2-Raw-GGUF`; shared text encoder and VAE files are sourced from `Comfy-Org/Krea-2`. Hugging Face is used only as a local artifact source.

## UI Parameter Mapping

- `prompt` -> local `TextGenerate` prompt request at node `4`, input `prompt`
- `negative_prompt` -> node `6`, input `text`
- `width` -> node `7`, input `width`
- `height` -> node `7`, input `height`
- `steps` -> node `8`, input `steps`
- `guidance` -> node `8`, input `cfg`
- `seed` -> node `8`, input `seed`
- Krea RAW Q5 GGUF model file -> node `1`, input `unet_name`
- Krea text encoder -> node `2`, input `clip_name`
- Krea VAE -> node `3`, input `vae_name`
- sampler/scheduler defaults -> node `8`, inputs `sampler_name` and `scheduler`

When the user selects LoRAs in the existing UI, the plugin inserts `LoraLoaderModelOnly` nodes between node `1` and node `8` before queueing the workflow. Comfy resolves those filenames from its local `models/loras` folder.

## Output Contract

Node `10` saves a PNG image. The plugin path returns the resulting local PNG path and downstream Blender insertion continues to use the existing generated-file behavior.

## Test Command

```bash
pytest tests/gpu/test_krea2.py --device cuda
```

## Expected Validation

- Comfy `/object_info` includes all required node classes.
- `workflow.api.json` validates as Comfy API format.
- The addon plugin path submits this workflow through `SlopperlyRuntimeGateway`.
- PIL can open the output PNG and dimensions match the requested size.
