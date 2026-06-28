# flux_redux_restyle

## Purpose

Local FLUX Redux image restyling for `models_plugins/image/flux_redux.py`.

## Required Nodes

- ComfyUI core at `https://github.com/comfyanonymous/ComfyUI.git`, commit `603d891eaf045d726d9c23276b4428daf2977624`.
- Required `/object_info` classes: `LoadImage`, `UnetLoaderGGUF`, `VAELoader`, `DualCLIPLoader`, `CLIPTextEncode`, `FluxGuidance`, `CLIPVisionLoader`, `CLIPVisionEncode`, `StyleModelLoader`, `StyleModelApply`, `BasicGuider`, `BasicScheduler`, `ModelSamplingFlux`, `EmptySD3LatentImage`, `KSamplerSelect`, `RandomNoise`, `SamplerCustomAdvanced`, `VAEDecode`, and `SaveImage`.

## Model Files

- `models/diffusion_models/flux1-dev-Q5_K_M.gguf` from `unsloth/FLUX.1-dev-GGUF`.
- `models/style_models/flux1-redux-dev.safetensors` from `Runware/FLUX.1-Redux-dev`.
- `models/clip_vision/sigclip_vision_patch14_384.safetensors` from `Comfy-Org/sigclip_vision_384`.
- `models/text_encoders/clip_l.safetensors` from `comfyanonymous/flux_text_encoders`.
- `models/text_encoders/t5xxl_fp16.safetensors` from `comfyanonymous/flux_text_encoders`.
- `models/vae/ae.safetensors` from `black-forest-labs/FLUX.1-schnell`.

## UI Parameter Mapping

- `inputs.image` uploads to node `40.LoadImage.image`.
- `inputs.width` maps to `27.EmptySD3LatentImage.width` and `30.ModelSamplingFlux.width`.
- `inputs.height` maps to `27.EmptySD3LatentImage.height` and `30.ModelSamplingFlux.height`.
- `inputs.steps` maps to `17.BasicScheduler.steps`.
- `inputs.guidance` maps to `26.FluxGuidance.guidance`.
- `inputs.seed` maps to `25.RandomNoise.noise_seed`.
- The reference image is encoded with `39.CLIPVisionEncode.crop = center`.
- Redux style conditioning uses `41.StyleModelApply.strength = 1.0` and `strength_type = multiply`, matching Comfy's current core node contract.
- The current Redux UI has no text prompt field, so node `6.CLIPTextEncode.text` is patched to an empty string and the reference image drives the Redux style conditioning.
- `frames` is preserved by the existing image UI but the workflow emits one PNG per generate call.

## Output Contract

Node `9.SaveImage` returns one PNG. The artifact validator must open it with PIL and confirm the dimensions match the requested width and height.

## Test Command

```bash
pytest tests/gpu/test_flux_redux.py --device cuda
```

## Expected Validation

Source image upload succeeds, required node classes are present, Comfy queues the API graph, and the returned PNG is readable at the requested dimensions.
