# lumina2_t2i

Local ComfyUI text-to-image workflow pack for the existing `Alpha-VLLM/Lumina-Image-2.0` plugin.

## Existing Addon Function

- Current plugin/function: `models_plugins/image/lumina2.py`.
- Runtime: Slopperly-owned ComfyUI.
- API workflow: `workflow.api.json`.
- Editable workflow: `workflow.editable.json`.

## Required Nodes

- `CheckpointLoaderSimple`
- `ModelSamplingAuraFlow`
- `CLIPTextEncodeLumina2`
- `CLIPTextEncode`
- `EmptySD3LatentImage`
- `KSampler`
- `VAEDecode`
- `SaveImage`

These are ComfyUI core node classes from pinned ComfyUI commit `603d891eaf045d726d9c23276b4428daf2977624`. `CLIPTextEncodeLumina2` is defined by Comfy core `comfy_extras/nodes_lumina2.py`; the basic graph follows the official Lumina Image 2.0 Comfy example.

## Model Files

- `models/checkpoints/lumina_2.safetensors`

The file is sourced from `Comfy-Org/Lumina_Image_2.0_Repackaged` at `all_in_one/lumina_2.safetensors`. Hugging Face is used only as a local artifact source.

## UI Parameter Mapping

- `prompt` -> node `3`, input `user_prompt`
- `negative_prompt` -> node `4`, input `text`
- `width` -> node `5`, input `width`
- `height` -> node `5`, input `height`
- `steps` -> node `6`, input `steps`
- `guidance` -> node `6`, input `cfg`
- `seed` -> node `6`, input `seed`
- Lumina checkpoint -> node `1`, input `ckpt_name`
- Lumina system prompt selector -> node `3`, input `system_prompt`
- AuraFlow shift -> node `2`, input `shift`
- sampler/scheduler defaults -> node `6`, inputs `sampler_name` and `scheduler`

## Output Contract

Node `8` saves a PNG image. The plugin path returns the resulting local PNG path and downstream Blender insertion continues to use the existing generated-file behavior.

## Test Command

```bash
pytest tests/gpu/test_lumina2.py --device cuda
```

## Expected Validation

- Comfy `/object_info` includes all required node classes.
- `workflow.api.json` validates as Comfy API format.
- The addon plugin path submits this workflow through `SlopperlyRuntimeGateway`.
- PIL can open the output PNG and dimensions match the requested size.
