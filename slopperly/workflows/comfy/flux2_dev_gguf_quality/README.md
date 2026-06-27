# FLUX.2 Dev Q5 GGUF Text-to-Image

Routes the existing `Flux2DevPlugin.generate()` no-reference path through local ComfyUI.

## Required Nodes

- `UnetLoaderGGUF` from `city96/ComfyUI-GGUF` at commit `6ea2651e7df66d7585f6ffee804b20e92fb38b8a`.
- ComfyUI core nodes from commit `603d891eaf045d726d9c23276b4428daf2977624`: `CLIPLoader`, `VAELoader`, `CLIPTextEncode`, `ConditioningZeroOut`, `CFGGuider`, `RandomNoise`, `KSamplerSelect`, `Flux2Scheduler`, `EmptyFlux2LatentImage`, `SamplerCustomAdvanced`, `VAEDecode`, and `SaveImage`.

## Model Files

- `models/diffusion_models/flux2-dev-Q5_K_M.gguf` from `city96/FLUX.2-dev-gguf`.
- `models/text_encoders/mistral_3_small_flux2_fp8.safetensors` from `Comfy-Org/flux2-dev`.
- `models/vae/flux2-vae.safetensors` from `Comfy-Org/flux2-dev`.

Runtime generation is not allowed to download these artifacts. Use `python -m slopperly.models.download --model flux2_dev_gguf_quality --accept-licenses` before certification.

## UI Parameter Mapping

- `prompt` -> `CLIPTextEncode.text`
- `width`, `height` -> `Flux2Scheduler` and `EmptyFlux2LatentImage`
- `steps` -> `Flux2Scheduler.steps`
- `guidance` -> plugin field `flux2_dev_guidance` -> `CFGGuider.cfg`
- `seed` -> `RandomNoise.noise_seed`
- multi-image references are handled by the companion `flux2_dev_gguf_quality_refs` workflow when selected.

## Output Contract

The workflow returns one PNG image collected from `SaveImage`. The addon path returns the same local artifact path shape used by the previous plugin.

## Test Command

```bash
pytest tests/gpu/test_flux2_dev.py --device cuda
```

## Expected Validation

- `/object_info` contains `UnetLoaderGGUF` and all required core FLUX.2 node classes.
- The workflow queues through `/prompt` and returns one readable PNG.
- A 1024x1024 T2I artifact validates with PIL on the RTX 4090 certification run.
