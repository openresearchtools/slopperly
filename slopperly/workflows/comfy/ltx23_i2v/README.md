# ltx23_i2v

Local ComfyUI workflow pack for the existing LTX 2.3 Q5 image-to-video path.

## Existing Addon Function

- Current plugin/function: LTX 2.3 image-to-video workflows.
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

- `models/diffusion_models/ltx-2.3-22b-distilled-1.1-Q5_K_M.gguf`
- `models/loras/ltx-2.3-22b-distilled-lora-384.safetensors`
- `models/vae/ltx-2.3-22b-distilled_video_vae.safetensors`
- `models/vae/ltx-2.3-22b-distilled_audio_vae.safetensors`
- `models/text_encoders/gemma_3_12B_it_fp4_mixed.safetensors`
- `models/embeddings/ltx-2.3-22b-distilled_embeddings_connectors.safetensors`

## UI Parameter Mapping

- `prompt` -> node `11`, input `text`
- `negative_prompt` -> node `12`, input `text`
- `width` -> nodes `8`, `14`, and `36`, input `width`
- `height` -> nodes `8`, `14`, and `36`, input `height`
- `frames` -> node `14` input `length`, node `16` input `frames_number`
- `fps` -> node `13` input `frame_rate`, node `16` input `frame_rate`, node `37` input `fps`
- `strength` -> node `15`, input `strength`
- `seed` -> node `19`, input `noise_seed`

`steps` and `guidance` are deliberately unmapped in this initial graph because it uses a fixed `ManualSigmas` schedule and `BasicGuider` without a CFG input.

## Output Contract

Node `38` saves an MP4 video. The plugin path must return the resulting local MP4 path and downstream Blender insertion continues to use the existing generated-file behavior.

## Test Command

```bash
pytest tests/gpu/test_ltx23_i2v_existing_workflow.py --device cuda
```

## Expected Validation

- Comfy `/object_info` includes all node classes listed above.
- `workflow.api.json` validates as Comfy API format.
- The addon plugin path submits the workflow through `SlopperlyRuntimeGateway`.
- `ffprobe` reads the output MP4.
- Width, height, fps, frame count, and duration match the mapped request within normal video tolerance.
