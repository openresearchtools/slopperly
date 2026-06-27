# kontext_relight

## Purpose

Local FLUX Kontext relighting for `models_plugins/image/kontext_relight.py`.

## Required Nodes

- ComfyUI core at `https://github.com/comfyanonymous/ComfyUI.git`, commit `603d891eaf045d726d9c23276b4428daf2977624`.
- Required `/object_info` classes: `LoadImage`, `UNETLoader`, `LoraLoaderModelOnly`, `DualCLIPLoader`, `VAELoader`, `CLIPTextEncode`, `FluxGuidance`, `FluxKontextImageScale`, `VAEEncode`, `ReferenceLatent`, `ConditioningZeroOut`, `EmptySD3LatentImage`, `KSampler`, `VAEDecode`, and `SaveImage`.

## Model Files

- `models/diffusion_models/flux1-dev-kontext_fp8_scaled.safetensors` from `Comfy-Org/flux1-kontext-dev_ComfyUI`.
- `models/loras/relighting-kontext-dev-lora-v3.safetensors` from `kontext-community/relighting-kontext-dev-lora-v3`.
- `models/text_encoders/clip_l.safetensors` from `comfyanonymous/flux_text_encoders`.
- `models/text_encoders/t5xxl_fp8_e4m3fn_scaled.safetensors` from `comfyanonymous/flux_text_encoders`.
- `models/vae/ae.safetensors` from `black-forest-labs/FLUX.1-schnell`.

## UI Parameter Mapping

- `inputs.image` uploads to `142.LoadImage.image`.
- `inputs.prompt`, `scene.illumination_style`, and `scene.light_direction` are combined by `KontextRelightPlugin._build_relight_prompt()` and patched to `6.CLIPTextEncode.text` as `inputs.kontext_relight_prompt`.
- `inputs.width` maps to `188.EmptySD3LatentImage.width`.
- `inputs.height` maps to `188.EmptySD3LatentImage.height`.
- `inputs.steps` maps to `31.KSampler.steps`.
- `inputs.guidance` maps to `35.FluxGuidance.guidance`.
- `inputs.seed` maps to `31.KSampler.seed`.
- The Relight LoRA is pinned at node `50.LoraLoaderModelOnly` with default strength `0.75`, matching the legacy plugin behavior.
- `frames` is preserved by the existing image UI but the workflow emits one PNG per generate call.
- Negative conditioning is created with `135.ConditioningZeroOut`, matching the official FLUX Kontext reference graph.

## Output Contract

Node `136.SaveImage` returns one PNG. The artifact validator must open it with PIL and confirm the dimensions match the requested width and height.

## Test Command

```bash
pytest tests/gpu/test_kontext_relight.py --device cuda
```

## Expected Validation

Source image upload succeeds, required node classes are present, the Relight LoRA filename and strength are patched, Comfy queues the API graph, and the returned PNG is readable at the requested dimensions.
