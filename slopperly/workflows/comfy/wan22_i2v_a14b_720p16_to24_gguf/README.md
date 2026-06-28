# Wan2.2 I2V A14B Q5 GGUF

Local image-to-video workflow for the original Wan A14B I2V plugin path.

## Required Nodes

- `UnetLoaderGGUFDisTorch2MultiGPU` from pinned `ComfyUI-GGUF` / `ComfyUI-MultiGPU`.
- `VAELoaderMultiGPU` and `CLIPLoaderMultiGPU` from pinned `ComfyUI-MultiGPU`.
- ComfyUI core nodes: `LoadImage`, `CLIPTextEncode`, `WanImageToVideo`, `ModelSamplingSD3`, `KSamplerAdvanced`, `LoraLoaderModelOnly`, `VAEDecode`, `CreateVideo`, and `SaveVideo`.

The graph is local-only. The high-noise and low-noise Wan A14B diffusion backbones are Q5 GGUF files, text encoding runs from the local UMT5 safetensors encoder on CPU, and the output is saved locally by Comfy.

## Model Files

The Slopperly model manager must place these files under the owned Comfy model directory before generation:

- `models/unet/HighNoise/Wan2.2-I2V-A14B-HighNoise-Q5_K_M.gguf` from `QuantStack/Wan2.2-I2V-A14B-GGUF`
- `models/unet/LowNoise/Wan2.2-I2V-A14B-LowNoise-Q5_K_M.gguf` from `QuantStack/Wan2.2-I2V-A14B-GGUF`
- `models/text_encoders/umt5_xxl_wan_text_encoder.safetensors` from `Comfy-Org/Wan_2.2_ComfyUI_Repackaged`
- `models/vae/wan_2.1_vae.safetensors` from `Comfy-Org/Wan_2.2_ComfyUI_Repackaged`
- `models/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors` from `Comfy-Org/Wan_2.2_ComfyUI_Repackaged`
- `models/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors` from `Comfy-Org/Wan_2.2_ComfyUI_Repackaged`

Runtime generation must not download these files. Install or copy them into the owned cache before certification.

## UI Parameter Mapping

- prompt -> positive `CLIPTextEncode`, node `4`, input `text`
- negative prompt -> negative `CLIPTextEncode`, node `5`, input `text`
- selected image/video strip -> `/upload/image` into `LoadImage`, node `1`; video strips are converted to a first-frame image by the production plugin
- width and height -> `WanImageToVideo`, node `6`; the plugin maps UI choices to `1280x720` or `720x1280`
- frames -> plugin computes native 16fps frame count from the requested 24fps target frame count, then patches `WanImageToVideo.length`, node `6`
- seed -> both high-noise and low-noise `KSamplerAdvanced.noise_seed`
- steps -> both samplers plus the low-noise `end_at_step`; the plugin splits high/low stages at half the requested step count
- guidance -> both sampler `cfg` inputs
- sampler and scheduler -> both sampler nodes
- GGUF model names, Lightx2v LoRAs, VAE, text encoder, CPU-offload device allocation, output prefix, format, and codec are patchable runtime fields with committed local defaults

The existing LoRA UI stays visible, but arbitrary project LoRA injection is not claimed by this certified graph. It requires a separate graph mutation and artifact test.

## Output Contract

Node `17` writes a native 16fps H.264 MP4 through `SaveVideo`. `WanI2VPlugin.generate()` finalizes that native artifact into the returned 24fps H.264 MP4 with local `ffmpeg`. The final artifact must be readable by `ffprobe` at `1280x720` or `720x1280`, 24fps, and duration-matched to the requested target frame count within certification tolerance.

## Test Command

```bash
pytest tests/gpu/test_wan22_i2v_a14b.py --device cuda
```

## Expected Validation

- Comfy `/object_info` includes `WanImageToVideo`, `UnetLoaderGGUFDisTorch2MultiGPU`, `VAELoaderMultiGPU`, `CLIPLoaderMultiGPU`, `LoraLoaderModelOnly`, `KSamplerAdvanced`, `CreateVideo`, and `SaveVideo`.
- `workflow.api.json` validates as Comfy API format and contains no external inference URLs.
- The production path calls `WanI2VPlugin.load()` and `WanI2VPlugin.generate()`.
- The smoke test produces a real native 16fps Comfy MP4 and a returned final 24fps MP4 through the same plugin path.
