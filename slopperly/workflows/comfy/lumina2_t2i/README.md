# lumina2_t2i

Local ComfyUI text-to-image workflow pack for the existing `Alpha-VLLM/Lumina-Image-2.0` plugin.

## Existing Addon Function

- Current plugin/function: `models_plugins/image/lumina2.py`.
- Runtime: Slopperly-owned ComfyUI.
- API workflow: `workflow.api.json`.
- Editable workflow: `workflow.editable.json`.

## Required Nodes

- `UnetLoaderGGUF`
- `ModelSamplingAuraFlow`
- `CLIPLoader`
- `CLIPTextEncodeLumina2`
- `CLIPTextEncode`
- `EmptySD3LatentImage`
- `KSampler`
- `VAELoader`
- `VAEDecode`
- `SaveImage`

The GGUF loader comes from pinned `ComfyUI-GGUF`; the other nodes are ComfyUI core node classes from pinned ComfyUI commit `603d891eaf045d726d9c23276b4428daf2977624`. `CLIPTextEncodeLumina2` is defined by Comfy core `comfy_extras/nodes_lumina2.py`; the basic graph follows the official Lumina Image 2.0 Comfy example but replaces the all-in-one checkpoint loader with split local model loaders.

## Model Files

- `models/diffusion_models/lumina_2_model-Q5_K_M.gguf`
- `models/diffusion_models/lumina_2_model_bf16.safetensors`
- `models/text_encoders/gemma_2_2b_fp16.safetensors`
- `models/vae/lumina2_ae.safetensors`

The BF16 diffusion source, text encoder, and VAE are sourced from `Comfy-Org/Lumina_Image_2.0_Repackaged` split files. `lumina_2_model-Q5_K_M.gguf` is derived locally by Slopperly from the original BF16 diffusion file using ComfyUI-GGUF conversion plus llama.cpp `llama-quantize Q5_K_M`. Hugging Face is used only as a local artifact source.

## UI Parameter Mapping

- `prompt` -> node `4`, input `user_prompt`
- `negative_prompt` -> node `5`, input `text`
- `width` -> node `6`, input `width`
- `height` -> node `6`, input `height`
- `steps` -> node `7`, input `steps`
- `guidance` -> node `7`, input `cfg`
- `seed` -> node `7`, input `seed`
- Lumina GGUF model -> node `1`, input `unet_name`
- Lumina text encoder -> node `3`, input `clip_name`
- Lumina system prompt selector -> node `4`, input `system_prompt`
- Lumina VAE -> node `8`, input `vae_name`
- AuraFlow shift -> node `2`, input `shift`
- sampler/scheduler defaults -> node `7`, inputs `sampler_name` and `scheduler`

## Output Contract

Node `10` saves a PNG image. The plugin path returns the resulting local PNG path and downstream Blender insertion continues to use the existing generated-file behavior.

## Test Command

```bash
pytest tests/gpu/test_lumina2.py --device cuda
```

## Expected Validation

- Comfy `/object_info` includes all required node classes.
- `workflow.api.json` validates as Comfy API format.
- The addon plugin path submits this workflow through `SlopperlyRuntimeGateway`.
- PIL can open the output PNG and dimensions match the requested size.
