# Wan2.2 TI2V-5B Q5 GGUF

Local default text/image-to-video workflow for Slopperly production video generation.

## Required Nodes

- `UnetLoaderGGUF` from `city96/ComfyUI-GGUF` at commit `6ea2651e7df66d7585f6ffee804b20e92fb38b8a`.
- `VHS_VideoCombine` from `Kosinkadink/ComfyUI-VideoHelperSuite` at commit `4ee72c065db22c9d96c2427954dc69e7b908444b`.
- ComfyUI core nodes from commit `603d891eaf045d726d9c23276b4428daf2977624`: `ModelSamplingSD3`, `CLIPLoader`, `CLIPTextEncode`, `VAELoader`, `Wan22ImageToVideoLatent`, `KSampler`, `VAEDecodeTiled`, and `LoadImage`.

The graph is intentionally local-only: GGUF diffusion model, local UMT5 text encoder, local Wan VAE, local sampler/decode, and local VideoHelperSuite MP4 output.

## Model Files

The Slopperly model manager must place these files under the owned Comfy model directory before generation:

- `models/diffusion_models/Wan2.2-TI2V-5B-Q5_K_M.gguf` from `QuantStack/Wan2.2-TI2V-5B-GGUF`
- `models/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors` from `Comfy-Org/Wan_2.2_ComfyUI_Repackaged`
- `models/vae/wan2.2_vae.safetensors` from `Comfy-Org/Wan_2.2_ComfyUI_Repackaged`
- `models/vae/wan_2.1_vae.safetensors` from `Comfy-Org/Wan_2.2_ComfyUI_Repackaged` for compatibility with existing Wan templates

Runtime generation is not allowed to download these artifacts. Use `python -m slopperly.models.download --model wan22_ti2v_5b_720p24_gguf --accept-licenses` before certification once the downloader supports this entry.

## UI Parameter Mapping

- prompt -> positive `CLIPTextEncode`, node `5`, input `text`
- negative prompt -> negative `CLIPTextEncode`, node `6`, input `text`
- width and height -> `Wan22ImageToVideoLatent`, node `7`; the plugin maps UI choices to `1280x704` or `704x1280`
- frames -> `Wan22ImageToVideoLatent.length`, node `7`
- seed, steps, guidance, sampler, scheduler, and denoise -> `KSampler`, node `9`
- fps -> `VHS_VideoCombine.frame_rate`, node `11`; production default is fixed to `24`
- image strip -> optional `/upload/image` into `LoadImage`, node `8`, then `Wan22ImageToVideoLatent.start_image`; in T2V mode node `8` is pruned and `start_image` is disconnected
- model, text encoder, VAE, clip type, sampling shift, video format, and output prefix are patchable profile inputs with committed local defaults

The surrounding video UI keeps prompt, negative prompt, optional image strip, resolution, frame count, steps, guidance, and seed controls. User LoRA wiring is deferred until a pinned Wan LoRA workflow is certified.

## Output Contract

Node `11` writes an H.264 MP4 through VideoHelperSuite with prefix `slopperly_wan22_ti2v_5b`. The plugin returns the first Comfy video artifact path to the existing output insertion path.

For certification, T2V and I2V runs must produce readable MP4 artifacts at `1280x704` or `704x1280`, 24fps, with duration matching the requested Wan frame count.

## Test Command

```bash
pytest tests/gpu/test_wan22_ti2v_5b.py --device cuda
```

## Expected Validation

- Comfy `/object_info` includes `UnetLoaderGGUF`, `Wan22ImageToVideoLatent`, `VAEDecodeTiled`, `VHS_VideoCombine`, and the required core text/sampling nodes.
- `workflow.api.json` validates as Comfy API format and contains no external inference URLs.
- The local dropdown path calls `WanTI2V5BPlugin.load()` and `WanTI2V5BPlugin.generate()`.
- The saved-project alias path calls `MiniMaxImg2VidPlugin.load()` and `MiniMaxImg2VidPlugin.generate()`.
- The smoke payload returns a readable 24fps MP4 file at the certified 720P-family dimensions.
