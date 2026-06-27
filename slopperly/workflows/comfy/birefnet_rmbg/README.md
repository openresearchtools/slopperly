# birefnet_rmbg

Local ComfyUI workflow pack for the existing BiRefNet-HR background-removal plugin.

## Existing Addon Function

- Current plugin/function: `models_plugins/image/birefnet.py`
- Legacy model ID: `ZhengPeng7/BiRefNet_HR`
- Runtime: Slopperly-owned ComfyUI.
- API workflow: `workflow.api.json`.
- Editable workflow: `workflow.editable.json`.

## Required Nodes

- ComfyUI core `LoadImage`
- ComfyUI core `SaveImage`
- `BiRefNetRMBG` from `1038lab/ComfyUI-RMBG`, pinned at commit `d7402513f23f58db7d56754b02a4f51a148b4941`

The upstream node exposes `BiRefNetRMBG` with required inputs `image` and `model`, optional matte controls, and return types `IMAGE`, `MASK`, and `IMAGE`.

## Model Files

The committed workflow selects `model: BiRefNet-HR`. The pinned Comfy node expects the files below under the owned Comfy model directory:

- `models/RMBG/BiRefNet/birefnet.py`
- `models/RMBG/BiRefNet/BiRefNet_config.py`
- `models/RMBG/BiRefNet/BiRefNet-HR.safetensors`
- `models/RMBG/BiRefNet/config.json`

Slopperly records the old plugin ID as a legacy alias while using the node-compatible local artifact source `1038lab/BiRefNet`.

## UI Parameter Mapping

- selected image strip -> upload to Comfy input storage, then patch node `1`, input `image`
- optional scene field `birefnet_model` -> node `2`, input `model`
- optional scene field `birefnet_mask_blur` -> node `2`, input `mask_blur`
- optional scene field `birefnet_mask_offset` -> node `2`, input `mask_offset`
- optional scene field `birefnet_refine_foreground` -> node `2`, input `refine_foreground`

The existing frame control is preserved for UI compatibility but deliberately unmapped because BiRefNet is single-image segmentation.

## Output Contract

Node `3` saves the first `BiRefNetRMBG` image output as PNG. With `background: Alpha`, the output must preserve the input dimensions and include an alpha channel.

## Test Command

```bash
pytest tests/gpu/test_birefnet_rmbg.py --device cuda
```

## Expected Validation

- Comfy `/object_info` includes `LoadImage`, `BiRefNetRMBG`, and `SaveImage`.
- `workflow.api.json` validates as Comfy API format.
- The addon plugin path calls `BiRefNetPlugin.load()` and `BiRefNetPlugin.generate()`.
- The returned artifact is a PNG with alpha.
- Output width and height match the selected input image.
