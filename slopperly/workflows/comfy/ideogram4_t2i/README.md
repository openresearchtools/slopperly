# ideogram4_t2i

Local ComfyUI text-to-image workflow pack for the existing Ideogram 4 plugin, using paired Q5 GGUF conditional and unconditional backbones.

## Existing Addon Function

- Current plugin/function: `models_plugins/image/ideogram4.py`.
- Runtime: Slopperly-owned ComfyUI.
- API workflow: `workflow.api.json`.
- Editable workflow: `workflow.editable.json`.

## Required Nodes

- `UnetLoaderGGUF`
- `CLIPLoader`
- `CLIPTextEncode`
- `ConditioningZeroOut`
- `CFGOverride`
- `DualModelGuider`
- `EmptyFlux2LatentImage`
- `RandomNoise`
- `KSamplerSelect`
- `Ideogram4Scheduler`
- `SamplerCustomAdvanced`
- `VAELoader`
- `VAEDecode`
- `SaveImage`

`UnetLoaderGGUF` is from pinned `city96/ComfyUI-GGUF`. The remaining nodes are ComfyUI core node classes from pinned ComfyUI commit `603d891eaf045d726d9c23276b4428daf2977624`. `Ideogram4Scheduler` is defined by Comfy core `comfy_extras/nodes_ideogram4.py`; `DualModelGuider`, `CFGOverride`, `KSamplerSelect`, `RandomNoise`, and `SamplerCustomAdvanced` are defined by Comfy core `comfy_extras/nodes_custom_sampler.py`.

## Model Files

- `models/diffusion_models/ideogram4-transformer-q5_0.gguf`
- `models/diffusion_models/ideogram4-unconditional_transformer-q5_0.gguf`
- `models/text_encoders/qwen3vl_8b_fp8_scaled.safetensors`
- `models/vae/flux2-vae.safetensors`

The GGUF files are sourced from `molbal/ideogram-4-gguf`; the text encoder and VAE remain sourced from `Comfy-Org/Ideogram-4`. Hugging Face is used only as a local artifact source.

## UI Parameter Mapping

- `prompt` -> node `4`, input `text`
- `width` -> nodes `8` and `11`, input `width`
- `height` -> nodes `8` and `11`, input `height`
- `steps` -> node `11`, input `steps` through `ideogram_steps`
- `guidance` -> node `7`, input `cfg` through `ideogram_guidance`
- `seed` -> node `9`, input `noise_seed`
- Ideogram Q5 GGUF conditional model -> node `1`, input `unet_name`
- Ideogram Q5 GGUF unconditional model -> node `2`, input `unet_name`
- Qwen3-VL text encoder -> node `3`, input `clip_name`
- Ideogram VAE -> node `13`, input `vae_name`
- sampler -> node `10`, input `sampler_name`
- scheduler parameters -> node `11`, inputs `mu` and `std`

The existing plugin has no negative prompt field because Ideogram 4 uses an unconditional model pass instead of a user negative prompt. The LoRA UI and prompt upsampling toggle remain visible; active use is recorded as unmapped until a certified local Comfy LoRA/prompt-builder graph is added.

## Output Contract

Node `15` saves a PNG image. The plugin path returns the resulting local PNG path and downstream Blender insertion continues to use the existing generated-file behavior.

## Test Command

```bash
pytest tests/gpu/test_ideogram4.py --device cuda
```

## Expected Validation

- Comfy `/object_info` includes all required node classes, including `UnetLoaderGGUF`.
- `workflow.api.json` validates as Comfy API format.
- The addon plugin path submits this workflow through `SlopperlyRuntimeGateway`.
- PIL can open the output PNG and dimensions match the requested size.
