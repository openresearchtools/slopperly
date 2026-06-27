# flux_kontext_edit

## Purpose

Local FLUX.1 Kontext instruction-based image editing for `models_plugins/image/flux_kontext.py`.

## Required Nodes

- ComfyUI core at `https://github.com/comfyanonymous/ComfyUI.git`, commit `603d891eaf045d726d9c23276b4428daf2977624`.
- Required `/object_info` classes: `LoadImage`, `UNETLoader`, `DualCLIPLoader`, `VAELoader`, `CLIPTextEncode`, `FluxGuidance`, `FluxKontextImageScale`, `VAEEncode`, `ReferenceLatent`, `ConditioningZeroOut`, `EmptySD3LatentImage`, `KSampler`, `VAEDecode`, and `SaveImage`.

## Model Files

- `models/diffusion_models/flux1-dev-kontext_fp8_scaled.safetensors` from `Comfy-Org/flux1-kontext-dev_ComfyUI`.
- `models/text_encoders/clip_l.safetensors` from `comfyanonymous/flux_text_encoders`.
- `models/text_encoders/t5xxl_fp8_e4m3fn_scaled.safetensors` from `comfyanonymous/flux_text_encoders`.
- `models/vae/ae.safetensors` from `black-forest-labs/FLUX.1-schnell`.

## UI Parameter Mapping

- `inputs.prompt` maps to `6.CLIPTextEncode.text`.
- `inputs.image` uploads to `142.LoadImage.image`.
- `inputs.width` maps to `188.EmptySD3LatentImage.width`.
- `inputs.height` maps to `188.EmptySD3LatentImage.height`.
- `inputs.steps` maps to `31.KSampler.steps`.
- `inputs.guidance` maps to `35.FluxGuidance.guidance`.
- `inputs.seed` maps to `31.KSampler.seed`.
- `inputs.strength`, `inputs.frames`, dynamic LoRA files, and inpaint masks are preserved in the Blender UI but are recorded as unmapped for this certified graph.
- Negative conditioning is created with `135.ConditioningZeroOut`, matching the official reference graph.

## Output Contract

Node `136.SaveImage` returns one PNG. The artifact validator must open it with PIL and confirm the dimensions match the requested width and height.

## Test Command

```bash
pytest tests/gpu/test_flux_kontext.py --device cuda
```

## Expected Validation

Source image upload succeeds, required node classes are present, Comfy queues the API graph, and the returned PNG is readable at the requested dimensions.
