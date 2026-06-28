# FLUX.2 Klein 4B Reference Edit

Routes the existing `Flux2Klein4BPlugin.generate()` image edit path through local ComfyUI.

## Required Nodes

- ComfyUI core at the pinned Slopperly commit.
- ComfyUI-GGUF with `UnetLoaderGGUF`.
- Node classes: `LoadImage`, `ImageScale`, `UnetLoaderGGUF`, `CLIPLoader`, `VAELoader`, `CLIPTextEncode`, `ConditioningZeroOut`, `VAEEncode`, `ReferenceLatent`, `CFGGuider`, `RandomNoise`, `KSamplerSelect`, `Flux2Scheduler`, `EmptyFlux2LatentImage`, `SamplerCustomAdvanced`, `VAEDecode`, `SaveImage`.

## Model Files

- `models/diffusion_models/flux-2-klein-4b-Q5_K_M.gguf` from `unsloth/FLUX.2-klein-4B-GGUF`.
- `models/text_encoders/qwen_3_4b.safetensors` from `Comfy-Org/vae-text-encorder-for-flux-klein-4b`.
- `models/vae/flux2-vae.safetensors` from `Comfy-Org/flux2-dev`.

The editable reference comes from the official Comfy template `image_flux2_klein_image_edit_4b_distilled.json`.

## UI Parameter Mapping

- `prompt` -> `CLIPTextEncode.text`
- selected image strip -> `LoadImage.image` -> `VAEEncode` -> `ReferenceLatent`
- `klein_strip_1`, `klein_strip_2`, `klein_strip_3` rendered paths -> optional `ReferenceLatent` slots
- `width`, `height` -> source/reference `ImageScale`, `Flux2Scheduler`, and `EmptyFlux2LatentImage`
- `steps` -> `Flux2Scheduler.steps`
- `guidance` -> plugin field `flux2_klein_guidance` -> `CFGGuider.cfg`
- `seed` -> `RandomNoise.noise_seed`
- selected `LoRA` controls -> plugin-inserted `LoraLoaderModelOnly` chain before `CFGGuider.model`
- `image_strength` remains visible but is recorded as unmapped because the official ReferenceLatent graph does not expose a denoise value.

## Output Contract

The workflow returns one PNG image collected from `SaveImage`. The addon path returns the same local artifact path shape used by the previous plugin.

## Test Command

```bash
pytest tests/gpu/test_flux2_klein_4b.py --device cuda
```

## Expected Validation

- `/object_info` contains all required core node classes.
- Optional second and third reference slots are disconnected when no strip is selected.
- The workflow queues through `/prompt` and returns one readable PNG.
- A 1024x1024 edit artifact validates with PIL on the RTX 4090 certification run.
