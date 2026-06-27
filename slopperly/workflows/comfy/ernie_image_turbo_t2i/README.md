# ERNIE-Image Turbo T2I

Local ComfyUI text-to-image workflow pack for the existing `baidu/ERNIE-Image-Turbo` plugin.

## Required Nodes

- `UNETLoader`
- `CLIPLoader`
- `VAELoader`
- `TextGenerate`
- `CLIPTextEncode`
- `ConditioningZeroOut`
- `EmptyFlux2LatentImage`
- `KSampler`
- `VAEDecode`
- `SaveImage`

## Model Files

Download from `Comfy-Org/ERNIE-Image`:

- `diffusion_models/ernie-image-turbo.safetensors` -> `models/diffusion_models/ernie-image-turbo.safetensors`
- `text_encoders/ministral-3-3b.safetensors` -> `models/text_encoders/ministral-3-3b.safetensors`
- `text_encoders/ernie-image-prompt-enhancer.safetensors` -> `models/text_encoders/ernie-image-prompt-enhancer.safetensors`
- `vae/flux2-vae.safetensors` -> `models/vae/flux2-vae.safetensors`

## UI Parameter Mapping

- prompt -> local `TextGenerate` prompt request -> positive `CLIPTextEncode`
- width and height -> `EmptyFlux2LatentImage.width` and `.height`
- steps, guidance, seed -> `KSampler.steps`, `.cfg`, `.seed`
- sampler, scheduler, denoise -> fixed local ERNIE Turbo defaults from the wrapper
- negative prompt -> preserved in the UI and recorded as unmapped because the official Turbo graph uses `ConditioningZeroOut`

## Output Contract

The workflow writes one PNG through `SaveImage`. The add-on wrapper returns that file path in the existing image result shape.

## Test Command

```bash
pytest tests/gpu/test_ernie.py --device cuda
```

## Expected Validation

- `/object_info` contains all required core node classes.
- Plugin `generate()` queues this API workflow through `SlopperlyRuntimeGateway`.
- The returned PNG is readable and matches the requested dimensions.
