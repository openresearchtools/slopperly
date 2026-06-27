# FLUX.2 Klein 9B Reference Edit

Routes the existing `Flux2Klein9BPlugin.generate()` image edit path through local ComfyUI.

## Required Nodes

- ComfyUI core at the pinned Slopperly commit.
- Node classes: `LoadImage`, `ImageScale`, `UNETLoader`, `CLIPLoader`, `VAELoader`, `CLIPTextEncode`, `ConditioningZeroOut`, `VAEEncode`, `ReferenceLatent`, `CFGGuider`, `RandomNoise`, `KSamplerSelect`, `Flux2Scheduler`, `EmptyFlux2LatentImage`, `SamplerCustomAdvanced`, `VAEDecode`, `SaveImage`.

## Model Files

- `models/diffusion_models/flux-2-klein-9b-fp8.safetensors` from `black-forest-labs/FLUX.2-klein-9b-fp8`.
- `models/text_encoders/qwen_3_8b_fp8mixed.safetensors` from `Comfy-Org/vae-text-encorder-for-flux-klein-9b`.
- `models/vae/full_encoder_small_decoder.safetensors` from `black-forest-labs/FLUX.2-small-decoder`.

The editable reference comes from the official Comfy template `image_flux2_klein_image_edit_9b_distilled.json`.

## UI Parameter Mapping

- `prompt` -> `CLIPTextEncode.text`
- selected image strip -> `LoadImage.image` -> `VAEEncode` -> `ReferenceLatent`
- `klein_strip_1`, `klein_strip_2`, `klein_strip_3` rendered paths -> optional `ReferenceLatent` slots
- `width`, `height` -> source/reference `ImageScale`, `Flux2Scheduler`, and `EmptyFlux2LatentImage`
- `steps` -> `Flux2Scheduler.steps`
- `guidance` -> plugin field `flux2_klein_guidance` -> `CFGGuider.cfg`
- `seed` -> `RandomNoise.noise_seed`
- `image_strength` remains visible but is recorded as unmapped because the official ReferenceLatent graph does not expose a denoise value.

## Output Contract

The workflow returns one PNG image collected from `SaveImage`. The addon path returns the same local artifact path shape used by the previous plugin.

## Test Command

```bash
pytest tests/gpu/test_flux2_klein_9b.py --device cuda
```

## Expected Validation

- `/object_info` contains all required core node classes.
- Optional second and third reference slots are disconnected when no strip is selected.
- The workflow queues through `/prompt` and returns one readable PNG.
- A 1024x1024 edit artifact validates with PIL on the RTX 4090 certification run.
