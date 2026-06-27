# OmniGen v1 Multi-Image

Local ComfyUI workflow for `Shitao/OmniGen-v1-diffusers` through the pinned `1038lab/ComfyUI-OmniGen` custom node.

## Required Nodes

- `ailab_OmniGen` from `1038lab/ComfyUI-OmniGen` at commit `5890d3fdb7ac5b598d025a2a14fbd2d6c9d8104b`.
- `LoadImage` and `SaveImage` from ComfyUI core at commit `603d891eaf045d726d9c23276b4428daf2977624`.

## Model Files

The Slopperly model manager must place the `Shitao/OmniGen-v1` snapshot under `models/LLM/OmniGen-v1` before generation.

Required evidence files:

- `config.json`
- `model.safetensors`
- `tokenizer.json`
- `tokenizer_config.json`
- `special_tokens_map.json`
- `vae/config.json`
- `vae/diffusion_pytorch_model.safetensors`

The pinned OmniGen node can auto-download code and weights upstream; Slopperly production must not rely on that path. Certification runs under the local-only network guard so missing local artifacts become a blocking failure instead of a hidden download.

## UI Parameter Mapping

- `prompt`, `width`, `height`, `steps`, `guidance`, and `seed` come from the existing Blender UI/operator flow.
- The three existing OmniGen prompt/image pickers are preserved. Selected strips are uploaded to local ComfyUI `LoadImage` nodes and wired to `ailab_OmniGen` as `image_1`, `image_2`, and `image_3`.
- Empty image slots are disconnected and pruned before `/object_info`, so text-only and one/two/three-reference runs share this workflow pack.
- `img_guidance_scale` maps from the existing scene setting with the old default of `1.6`.
- `memory_management` defaults to `Memory Priority` for the 16 GB profile.
- `negative_prompt` and `frames` remain visible only because the surrounding image-plugin UI contract includes them; the pinned OmniGen node exposes no negative prompt and emits one image.

## Output Contract

The workflow returns one PNG image artifact through `SaveImage`. When reference images are present, the plugin preserves the previous behavior by enabling `use_input_image_size_as_output`.

## Test Command

```bash
pytest tests/gpu/test_omnigen.py --device cuda
```

## Expected Validation

The GPU test calls `OmniGenPlugin.generate()` with real strip-backed image paths, collects a PNG from local ComfyUI, and validates the image is readable. Dropdown certification remains blocked until this test writes a `PASS` artifact record.
