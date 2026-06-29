# ltx23_multi_staged

Local ComfyUI workflow pack for the existing LTX 2.3 multi-anchor video path.

## Existing Addon Function

- Current plugin/function: `models_plugins/video/ltx23_multi.py` / LTX 2.3 Multi-Input Staged.
- Runtime: Slopperly-owned ComfyUI.
- API workflow: `workflow.api.json`.
- Editable workflow: `workflow.editable.json`.
- Certified backbone: `ltx-2.3-22b-distilled-1.1-Q5_K_M.gguf` through `UnetLoaderGGUFDisTorch2MultiGPU`.

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
- `LTXVAddGuide`
- `LTXVCropGuides`
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
- `width` -> nodes `8`, `14`, `25`, `30`, `41`, and `46`, input `width`
- `height` -> nodes `8`, `14`, `25`, `30`, `41`, and `46`, input `height`
- `frames` -> node `14` input `length`, node `16` input `frames_number`
- `fps` -> node `13` input `frame_rate`, node `16` input `frame_rate`, node `37` input `fps`
- `strength` -> node `15`, input `strength`
- `seed` -> node `19`, input `noise_seed`
- selected start image or first frame from selected video strip -> upload to node `7`, input `image`
- first middle anchor -> upload to node `24`, input `image`; plugin maps its fraction to node `28`, input `frame_idx`
- second middle anchor -> upload to node `40`, input `image`; plugin maps its fraction to node `44`, input `frame_idx`
- third middle anchor -> upload to node `45`, input `image`; plugin maps its fraction to node `49`, input `frame_idx`
- selected final anchor -> upload to node `29`, input `image`; plugin maps it to node `33`, input `frame_idx=-1`
- `ltx_guide_strength` -> nodes `28`, `33`, `44`, and `49`, input `strength`

`steps` and `guidance` are deliberately unmapped because this GGUF graph uses a fixed `ManualSigmas` schedule and `BasicGuider` without a CFG input. The legacy `ltx23_stage_mode` selector remains visible; the certified local graph runs the full Q5 Comfy path. STEP1/STEP2 require separate local Comfy graphs and artifact tests before they can be claimed.

The current certified 720-family profile maps a UI request of `1280x720` to the model-safe multiple-of-32 output size `1280x704`. Exact `1280x720` must not be claimed until a separate real artifact test proves that size.

## Output Contract

Node `38` saves an MP4 video. The plugin path must return the resulting local MP4 path and downstream Blender insertion continues to use the existing generated-file behavior.

## Test Command

```bash
pytest tests/gpu/test_ltx23_multi_staged.py --device cuda
```

## Expected Validation

- Comfy `/object_info` includes all node classes listed above.
- `workflow.api.json` validates as Comfy API format and contains no external inference URLs.
- The addon plugin path submits the workflow through `LTX2_3MultiStagedPlugin.load()` and `LTX2_3MultiStagedPlugin.generate()`.
- The submitted prompt uses `UnetLoaderGGUFDisTorch2MultiGPU` with `ltx-2.3-22b-distilled-1.1-Q5_K_M.gguf`.
- Start, middle, and final anchor uploads are patched into local Comfy `LoadImage` nodes.
- `ffprobe` reads the output MP4.
- Width, height, fps, frame count, and duration match the mapped request within normal video tolerance. The certified smoke profile is `1280x704`, 24fps, 17 frames, with audio present.
