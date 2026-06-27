# local_image_vsr_upscale

Local ComfyUI workflow pack for the former NVIDIA Maxine image super-resolution plugin.

## Existing Addon Function

- Current plugin/function: `models_plugins/image/maxine_vsr.py`
- Legacy model ID: `nvidia/maxine-vsr`
- Runtime: Slopperly-owned ComfyUI.
- API workflow: `workflow.api.json`.
- Editable workflow: `workflow.editable.json`.

The production dropdown label is `Image: Local Super Resolution`; no NVIDIA Maxine runtime is used.

## Required Nodes

- ComfyUI core `LoadImage`
- ComfyUI core `UpscaleModelLoader`
- ComfyUI core `ImageUpscaleWithModel`
- ComfyUI core `ImageScale`
- ComfyUI core `SaveImage`

The exact node classes and inputs were verified against pinned ComfyUI commit `603d891eaf045d726d9c23276b4428daf2977624`.

## Model Files

The workflow uses the local upscaler model below:

- Hugging Face artifact source: `ai-forever/Real-ESRGAN`
- File: `RealESRGAN_x4.pth`
- Comfy location: `models/upscale_models/RealESRGAN_x4.pth`

## UI Parameter Mapping

- selected image strip -> upload to Comfy input storage, then patch node `1`, input `image`
- `width` -> node `4`, input `width`
- `height` -> node `4`, input `height`
- optional scene field `local_vsr_model` -> node `2`, input `model_name`
- optional scene field `local_vsr_upscale_method` -> node `4`, input `upscale_method`
- optional scene field `local_vsr_crop` -> node `4`, input `crop`

The old Maxine-only quality selector is deliberately unmapped because this workflow does not use the NVIDIA Maxine runtime.

## Output Contract

Node `5` saves a PNG. The plugin path must return the local file path. The artifact must be readable and match the requested width and height.

## Test Command

```bash
pytest tests/gpu/test_local_image_vsr_upscale.py --device cuda
```

## Expected Validation

- Comfy `/object_info` includes all node classes listed above.
- `workflow.api.json` validates as Comfy API format.
- The addon plugin path calls `MaxineVSRPlugin.load()` and `MaxineVSRPlugin.generate()`.
- The returned PNG width and height match the requested resolution.
