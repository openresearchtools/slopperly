# flux1_canny_control

Local ComfyUI Canny-control workflow pack for the existing `fuliucansheng/FLUX.1-Canny-dev-diffusers-lora` plugin.

## Existing Addon Function

- Current plugin/function: `models_plugins/image/flux_canny.py`.
- Runtime: Slopperly-owned ComfyUI.
- API workflow: `workflow.api.json`.
- Editable workflow: `workflow.editable.json`.

## Required Nodes

- `LoadImage`
- `ImageScale`
- `CannyEdgePreprocessor`
- `UnetLoaderGGUF`
- `VAELoader`
- `DualCLIPLoader`
- `CLIPTextEncode`
- `FluxGuidance`
- `InstructPixToPixConditioning`
- `KSampler`
- `VAEDecode`
- `SaveImage`

`UnetLoaderGGUF` is from pinned `city96/ComfyUI-GGUF`. `CannyEdgePreprocessor` is from pinned `Fannovel16/comfyui_controlnet_aux` commit `e8b689a513c3e6b63edc44066560ca5919c0576e`. The other nodes are ComfyUI core node classes from pinned ComfyUI commit `603d891eaf045d726d9c23276b4428daf2977624`.

## Model Files

- `models/diffusion_models/flux1-canny-dev-fp16-Q5_0-GGUF.gguf`
- `models/text_encoders/clip_l.safetensors`
- `models/text_encoders/t5xxl_fp16.safetensors`
- `models/vae/ae.safetensors`

The workflow follows the official Comfy FLUX.1 Canny example graph with the diffusion backbone loaded through `UnetLoaderGGUF` from the Q5_0 GGUF artifact, while the text encoders and VAE match the Comfy documentation's manual installation list.

## UI Parameter Mapping

- `image` -> node `1`, input `image`
- `width` -> node `2`, input `width`
- `height` -> node `2`, input `height`
- Canny thresholds -> node `3`, inputs `low_threshold` and `high_threshold`
- Canny preprocessor resolution -> node `3`, input `resolution`
- FLUX Canny model -> node `4`, input `unet_name`
- FLUX VAE -> node `5`, input `vae_name`
- `clip_l` and `t5xxl` text encoders -> node `6`, inputs `clip_name1` and `clip_name2`
- `prompt` -> node `7`, input `text`
- empty negative prompt -> node `8`, input `text`
- `guidance` -> node `9`, input `guidance`
- `steps` -> node `11`, input `steps`
- `seed` -> node `11`, input `seed`
- sampler defaults -> node `11`, inputs `cfg`, `sampler_name`, `scheduler`, and `denoise`

The existing frame, image-strength, and LoRA controls remain visible. Selected project LoRAs are inserted by the plugin through `LoraLoaderModelOnly` nodes before the sampler model input. The official FLUX.1 Canny Comfy graph uses `InstructPixToPixConditioning` and does not expose an independent conditioning-strength input, so image strength is recorded as unmapped instead of silently applied.

## Output Contract

Node `13` saves a PNG image. The plugin path returns the resulting local PNG path and downstream Blender insertion continues to use the existing generated-file behavior.

## Test Command

```bash
pytest tests/gpu/test_flux1_control.py --device cuda -k canny
```

## Expected Validation

- Comfy `/object_info` includes all required node classes.
- `workflow.api.json` validates as Comfy API format.
- The addon plugin path submits this workflow through `SlopperlyRuntimeGateway`.
- PIL can open the output PNG and dimensions match the requested size.
