# nucleus_image_t2i

Local ComfyUI text-to-image workflow pack for the existing `NucleusAI/Nucleus-Image` plugin.

## Existing Addon Function

- Current plugin/function: `models_plugins/image/nucleus_moe.py`.
- Runtime: Slopperly-owned ComfyUI.
- API workflow: `workflow.api.json`.
- Editable workflow: `workflow.editable.json`.

## Required Nodes

- `SlopperlyDiffusersImageGenerate`
- `SaveImage`

`SlopperlyDiffusersImageGenerate` is provided by the repo-local `slopperly_nodes` custom node package installed into owned ComfyUI. It wraps the existing Nucleus diffusers pipeline and the pinned FP8 transformer patch instead of replacing the model family.

## Model Files

- `models/diffusers/nucleus_image_base/model_index.json` and the rest of the local snapshot for `NucleusAI/Nucleus-Image`
- `models/diffusers/nucleus_image_fp8/moe_fp8_patch.py`
- `models/diffusers/nucleus_image_fp8/Nucleus-Image-FP8.safetensors`
- `models/diffusers/nucleus_image_fp8/config.json`

Hugging Face is used only as a model artifact source. The workflow sets `local_files_only` to true during generation.

## UI Parameter Mapping

- `prompt` -> node `1`, input `prompt`
- `negative_prompt` -> node `1`, input `negative_prompt`
- `width` -> node `1`, input `width`
- `height` -> node `1`, input `height`
- `steps` -> node `1`, input `steps`
- `guidance` -> node `1`, input `guidance`
- `seed` -> node `1`, input `seed`
- Nucleus base snapshot path -> node `1`, input `model_path`
- Nucleus FP8 patch and weights -> node `1`, inputs `fp8_patch_path` and `fp8_weights_path`

## Output Contract

Node `2` saves a PNG image. The plugin path returns the resulting local PNG path and downstream Blender insertion continues to use the existing generated-file behavior.

## Test Command

```bash
pytest tests/gpu/test_nucleus_image.py --device cuda
```

## Expected Validation

- Comfy `/object_info` includes `SlopperlyDiffusersImageGenerate` and `SaveImage`.
- `workflow.api.json` validates as Comfy API format.
- The addon plugin path submits this workflow through `SlopperlyRuntimeGateway`.
- PIL can open the output PNG and dimensions match the requested size.
