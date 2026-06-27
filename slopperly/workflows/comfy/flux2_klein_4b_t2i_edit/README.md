# FLUX.2 Klein 4B Text-to-Image

Routes the existing `Flux2Klein4BPlugin.generate()` text-to-image path through local ComfyUI.

## Required Nodes

- ComfyUI core at the pinned Slopperly commit.
- Node classes: `UNETLoader`, `CLIPLoader`, `VAELoader`, `CLIPTextEncode`, `ConditioningZeroOut`, `CFGGuider`, `RandomNoise`, `KSamplerSelect`, `Flux2Scheduler`, `EmptyFlux2LatentImage`, `SamplerCustomAdvanced`, `VAEDecode`, `SaveImage`.

## Model Files

- `models/diffusion_models/flux-2-klein-4b-fp8.safetensors` from `black-forest-labs/FLUX.2-klein-4b-fp8`.
- `models/text_encoders/qwen_3_4b.safetensors` from `Comfy-Org/vae-text-encorder-for-flux-klein-4b`.
- `models/vae/flux2-vae.safetensors` from `Comfy-Org/flux2-dev`.

The editable reference comes from the official Comfy template `image_flux2_klein_text_to_image.json`.

## UI Parameter Mapping

- `prompt` -> `CLIPTextEncode.text`
- `width`, `height` -> `Flux2Scheduler` and `EmptyFlux2LatentImage`
- `steps` -> `Flux2Scheduler.steps`
- `guidance` -> plugin field `flux2_klein_guidance` -> `CFGGuider.cfg`
- `seed` -> `RandomNoise.noise_seed`
- `LoRA` controls remain visible but are recorded as unmapped until dynamic Comfy LoRA injection is certified.

## Output Contract

The workflow returns one PNG image collected from `SaveImage`. The addon path returns the same local artifact path shape used by the previous plugin.

## Test Command

```bash
pytest tests/gpu/test_flux2_klein_4b.py --device cuda
```

## Expected Validation

- `/object_info` contains all required core node classes.
- The workflow queues through `/prompt` and returns one readable PNG.
- A 1024x1024 T2I artifact validates with PIL on the RTX 4090 certification run.
