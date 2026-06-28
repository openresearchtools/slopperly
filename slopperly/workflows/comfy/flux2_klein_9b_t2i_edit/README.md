# FLUX.2 Klein 9B Text-to-Image

Routes the existing `Flux2Klein9BPlugin.generate()` text-to-image path through local ComfyUI.

## Required Nodes

- ComfyUI core at the pinned Slopperly commit.
- Node classes: `UNETLoader`, `CLIPLoader`, `VAELoader`, `CLIPTextEncode`, `ConditioningZeroOut`, `CFGGuider`, `RandomNoise`, `KSamplerSelect`, `Flux2Scheduler`, `EmptyFlux2LatentImage`, `SamplerCustomAdvanced`, `VAEDecode`, `SaveImage`.

## Model Files

- `models/diffusion_models/flux-2-klein-9b-fp8.safetensors` from `titomatus0203/flux-2-klein-9b-fp8`.
- `models/text_encoders/qwen_3_8b_fp8mixed.safetensors` from `Comfy-Org/vae-text-encorder-for-flux-klein-9b`.
- `models/vae/full_encoder_small_decoder.safetensors` from `black-forest-labs/FLUX.2-small-decoder`.

The editable reference comes from the official Comfy 9B template family. The production API graph uses the distilled `flux-2-klein-9b-fp8.safetensors` file so the existing plugin's 4-step, guidance-1 behavior is preserved; the separate base 9B 20-step profile is not exposed here until separately certified.

## UI Parameter Mapping

- `prompt` -> `CLIPTextEncode.text`
- `width`, `height` -> `Flux2Scheduler` and `EmptyFlux2LatentImage`
- `steps` -> `Flux2Scheduler.steps`
- `guidance` -> plugin field `flux2_klein_guidance` -> `CFGGuider.cfg`
- `seed` -> `RandomNoise.noise_seed`
- `LoRA` controls -> dynamic `LoraLoaderModelOnly` insertion before `CFGGuider.model`.

## Output Contract

The workflow returns one PNG image collected from `SaveImage`. The addon path returns the same local artifact path shape used by the previous plugin.

## Test Command

```bash
pytest tests/gpu/test_flux2_klein_9b.py --device cuda
```

## Expected Validation

- `/object_info` contains all required core node classes.
- The workflow queues through `/prompt` and returns one readable PNG.
- A 1024x1024 T2I artifact validates with PIL on the RTX 4090 certification run.
