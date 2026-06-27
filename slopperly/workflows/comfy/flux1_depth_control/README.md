# flux1_depth_control

Local ComfyUI Depth-control workflow pack for the existing `romanfratric234/FLUX.1-Depth-dev-lora` plugin.

## Existing Addon Function

- Current plugin/function: `models_plugins/image/flux_depth.py`.
- Runtime: Slopperly-owned ComfyUI.
- API workflow: `workflow.api.json`.
- Editable workflow: `workflow.editable.json`.

## Required Nodes

- `LoadImage`
- `ImageScale`
- `DepthAnythingV2Preprocessor`
- `UNETLoader`
- `LoraLoaderModelOnly`
- `VAELoader`
- `DualCLIPLoader`
- `CLIPTextEncode`
- `FluxGuidance`
- `InstructPixToPixConditioning`
- `KSampler`
- `VAEDecode`
- `SaveImage`

`DepthAnythingV2Preprocessor` is from pinned `Fannovel16/comfyui_controlnet_aux` commit `e8b689a513c3e6b63edc44066560ca5919c0576e`. The other nodes are ComfyUI core node classes from pinned ComfyUI commit `603d891eaf045d726d9c23276b4428daf2977624`.

## Model Files

- `models/diffusion_models/flux1-dev.safetensors`
- `models/loras/flux1-depth-dev-lora.safetensors`
- `models/text_encoders/clip_l.safetensors`
- `models/text_encoders/t5xxl_fp16.safetensors`
- `models/vae/ae.safetensors`
- `custom_nodes/comfyui_controlnet_aux/ckpts/depth-anything/Depth-Anything-V2-Large/depth_anything_v2_vitl.pth`

The workflow follows the official Comfy FLUX.1 Depth LoRA example graph. The depth adapter is recorded from `Comfy-Org/flux1-dev` split files while preserving the legacy `romanfratric234/FLUX.1-Depth-dev-lora` saved-project alias.

## UI Parameter Mapping

- `image` -> node `1`, input `image`
- `width` -> node `2`, input `width`
- `height` -> node `2`, input `height`
- DepthAnything checkpoint -> node `3`, input `ckpt_name`
- Depth preprocessor resolution -> node `3`, input `resolution`
- FLUX.1 base model -> node `4`, input `unet_name`
- FLUX.1 Depth LoRA -> node `5`, input `lora_name`
- FLUX VAE -> node `6`, input `vae_name`
- `clip_l` and `t5xxl` text encoders -> node `7`, inputs `clip_name1` and `clip_name2`
- `prompt` -> node `8`, input `text`
- empty negative prompt -> node `9`, input `text`
- `guidance` -> node `10`, input `guidance`
- `steps` -> node `12`, input `steps`
- `seed` -> node `12`, input `seed`
- sampler defaults -> node `12`, inputs `cfg`, `sampler_name`, `scheduler`, and `denoise`

The existing frame, image-strength, and LoRA controls remain visible. The official FLUX.1 Depth LoRA Comfy graph uses `InstructPixToPixConditioning` and does not expose an independent conditioning-strength input, so image strength is recorded as unmapped instead of silently applied.

## Output Contract

Node `14` saves a PNG image. The plugin path returns the resulting local PNG path and downstream Blender insertion continues to use the existing generated-file behavior.

## Test Command

```bash
pytest tests/gpu/test_flux1_control.py --device cuda -k depth
```

## Expected Validation

- Comfy `/object_info` includes all required node classes.
- `workflow.api.json` validates as Comfy API format.
- The addon plugin path submits this workflow through `SlopperlyRuntimeGateway`.
- PIL can open the output PNG and dimensions match the requested size.
