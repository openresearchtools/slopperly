# FLUX.2 Klein 9B Schematic LoRA

Routes the existing `Flux2Klein9BSchematicPlugin.generate()` image-conditioned schematic map path through local ComfyUI.

## Required Nodes

- ComfyUI core at the pinned Slopperly commit.
- Node classes: `LoadImage`, `ImageScale`, `UNETLoader`, `LoraLoaderModelOnly`, `CLIPLoader`, `VAELoader`, `CLIPTextEncode`, `VAEEncode`, `ReferenceLatent`, `CFGGuider`, `RandomNoise`, `KSamplerSelect`, `Flux2Scheduler`, `EmptyFlux2LatentImage`, `SamplerCustomAdvanced`, `VAEDecode`, `SaveImage`.

## Model Files

- `models/diffusion_models/flux-2-klein-base-9b-fp8.safetensors` from the public `wissxi/FLUX.2-klein-base-9b-fp8` mirror; the original BFL FP8 source is gated and requires a Hugging Face token.
- `models/text_encoders/qwen_3_8b.safetensors` from `Comfy-Org/vae-text-encorder-for-flux-klein-9b`.
- `models/vae/flux2-vae.safetensors` from `Comfy-Org/flux2-dev`.
- Six schematic LoRAs from `nomadoor/flux-2-klein-9B-schematic-lora`, installed under `models/loras/`.

The upstream README states these LoRAs were trained on FLUX.2 Klein 9B base and may not behave correctly on distilled Klein models. This workflow therefore uses the base 9B FP8 file rather than the distilled 9B workflow used by `flux2_klein_9b_t2i_edit`.

## UI Parameter Mapping

- selected image strip -> `LoadImage.image` -> `ImageScale` -> `VAEEncode` -> `ReferenceLatent`
- `klein_schematic_mode` -> plugin field `flux2_klein_schematic_lora` -> `LoraLoaderModelOnly.lora_name`
- `prompt` -> `CLIPTextEncode.text`
- source image width/height -> `ImageScale`, `Flux2Scheduler`, and `EmptyFlux2LatentImage`
- `steps` -> `Flux2Scheduler.steps`
- `guidance` -> `CFGGuider.cfg`
- `seed` -> `RandomNoise.noise_seed`

The workflow keeps the current schematic UI. It does not add a negative prompt control; instead it applies the fixed negative prompt from the upstream Comfy workflow: `text, worst quality, blurry, ugly`.

## Output Contract

The workflow returns one PNG image collected from `SaveImage`. The addon path returns the same local artifact path shape used by the previous plugin.

## Test Command

```bash
pytest tests/gpu/test_flux2_klein_schematic.py --device cuda
```

## Expected Validation

- `/object_info` contains all required core node classes.
- The selected schematic LoRA filename is patched before queueing.
- The workflow queues through `/prompt` and returns one readable PNG matching the source image dimensions.
