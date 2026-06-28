# ltx23_extend_staged

Local ComfyUI workflow pack for the existing LTX 2.3 Extend button's Q5 extension-tail path.

## Existing Addon Function

- Current plugin/function: `video/ltx23_extend.py` / LTX 2.3 Extend.
- Runtime: Slopperly-owned ComfyUI.
- API workflow: `workflow.api.json`.
- Editable workflow: `workflow.editable.json`.

## Required Nodes

- `UnetLoaderGGUFDisTorch2MultiGPU`
- `LoraLoaderModelOnly`
- `VAELoaderMultiGPU`
- `LTXVAudioVAELoader`
- `LTXAVTextEncoderLoader`
- `LoadImage`
- `ImageScale`
- `ResizeImagesByLongerEdge`
- `LTXVPreprocess`
- `CLIPTextEncode`
- `LTXVConditioning`
- `EmptyLTXVLatentVideo`
- `LTXVImgToVideoInplace`
- `LTXVEmptyLatentAudio`
- `LTXVConcatAVLatent`
- `BasicGuider`
- `RandomNoise`
- `KSamplerSelect`
- `ManualSigmas`
- `SamplerCustomAdvanced`
- `LTXVSeparateAVLatent`
- `VAEDecode`
- `LTXVAudioVAEDecode`
- `CreateVideo`
- `SaveVideo`

## Model Files

- `models/unet/ltx-2.3-22b-distilled-1.1-Q5_K_M.gguf`
- `models/loras/ltx-2.3-22b-distilled-lora-384.safetensors`
- `models/vae/ltx-2.3-22b-distilled_video_vae.safetensors`
- `models/vae/ltx-2.3-22b-distilled_audio_vae.safetensors`
- `models/text_encoders/gemma_3_12B_it_fp4_mixed.safetensors`
- `models/text_encoders/ltx-2.3-22b-distilled_embeddings_connectors.safetensors`

## UI Parameter Mapping

- `prompt` -> node `11`, input `text`
- `negative_prompt` -> node `12`, input `text`
- `width` -> nodes `8`, `14`, and `36`, input `width`
- `height` -> nodes `8`, `14`, and `36`, input `height`
- `frames` -> node `14` input `length`, node `16` input `frames_number`
- `fps` -> node `13` input `frame_rate`, node `16` input `frame_rate`, node `37` input `fps`
- `strength` -> node `15`, input `strength`
- `seed` -> node `19`, input `noise_seed`
- selected video strip -> the plugin extracts the final source frame locally with ffmpeg, uploads that frame to Comfy input storage, then patches node `7`, input `image`

`steps` and `guidance` are deliberately unmapped in this initial graph because it uses a fixed `ManualSigmas` schedule and `BasicGuider` without a CFG input.

This pack generates the extension tail. `LTX2_3ExtendStagedPlugin.generate()` normalizes the source clip to the certified 720-family output profile, generates the tail through this Comfy workflow, and concatenates source plus tail into the returned MP4. The certified behavior is an output video whose duration is greater than the source clip duration.

The current certified 720-family profile maps a UI request of `1280x720` to the model-safe multiple-of-32 output size `1280x704`. Exact `1280x720` must not be claimed until a separate real artifact test proves that size.

## Output Contract

Node `38` saves an MP4 tail video. The plugin path must return the final concatenated local MP4 path and downstream Blender insertion continues to use the existing generated-file behavior.

## Test Command

```bash
pytest tests/gpu/test_ltx23_extend_staged.py --device cuda
```

## Expected Validation

- Comfy `/object_info` includes all node classes listed above.
- `workflow.api.json` validates as Comfy API format.
- The addon plugin path submits the extracted tail frame through `SlopperlyRuntimeGateway`.
- `ffprobe` reads the returned concatenated MP4.
- Width, height, fps, and duration validate. The certified smoke profile maps the UI request to `1280x704`, 24fps, and a final duration greater than the 1.0s source fixture after a 17-frame generated tail is appended.
