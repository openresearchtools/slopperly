# ltx23_lipsync_dialogue

Local ComfyUI workflow pack for the existing LTX 2.3 Lip Sync plugin path.

## Existing Addon Function

- Current plugin/function: `models_plugins/video/ltx23_lipsync.py`
- Runtime: Slopperly-owned ComfyUI.
- API workflow: `workflow.api.json`.
- Editable workflow notes: `workflow.editable.json`.

The production plugin keeps the prompt, negative prompt, source image/video strip, resolution, frame count, seed, LoRA visibility, and audio reference selector. It no longer imports Diffusers, Transformers, Torch, or SDNQ inside the add-on process for generation.

## Required Nodes

- `UnetLoaderGGUFDisTorch2MultiGPU`
- `LoraLoaderModelOnly`
- `VAELoaderMultiGPU`
- `LTXVAudioVAELoader`
- `LTXAVTextEncoderLoader`
- `LoadImage`
- `LoadAudio`
- `ImageScale`
- `ResizeImagesByLongerEdge`
- `LTXVPreprocess`
- `CLIPTextEncode`
- `LTXVConditioning`
- `LTXVReferenceAudio`
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
- audio-driven frame count -> node `14` input `length`, node `16` input `frames_number`
- `fps` -> node `13` input `frame_rate`, node `16` input `frame_rate`, node `37` input `fps`
- `strength` -> node `15`, input `strength`
- `seed` -> node `19`, input `noise_seed`
- source image or first frame from selected video -> upload to Comfy input storage, then patch node `7`, input `image`
- audio reference or selected video audio -> upload to Comfy input storage, then patch node `39`, input `audio`
- `ltx23_lipsync_identity_guidance` scene value -> node `40`, input `identity_guidance_scale`

`steps` and `guidance` are deliberately unmapped because this certified graph uses a fixed `ManualSigmas` schedule and `BasicGuider` without a CFG input. Project LoRA selection remains visible but is not dynamically injected until a separate graph mutation passes real artifact certification.

The plugin computes the target duration from the reference audio, rounds the Comfy generation length to the LTX-required `8n+1` frame count, then trims or pads the final local MP4 to the exact reference audio duration with ffmpeg.

## Output Contract

Node `38` saves a raw MP4 video from Comfy. The plugin returns a final local MP4 after muxing the reference audio and enforcing duration equality with the audio source.

## Test Command

```bash
pytest tests/gpu/test_ltx23_lipsync_audio_duration.py --device cuda
```

## Expected Validation

- Comfy `/object_info` includes all node classes listed above.
- `workflow.api.json` validates as Comfy API format.
- The add-on plugin path calls `LTX2_3LipSyncPlugin.load()` and `LTX2_3LipSyncPlugin.generate()`.
- The submitted graph uses the Q5 GGUF backbone through `UnetLoaderGGUFDisTorch2MultiGPU`.
- The submitted graph uploads both the source image and reference audio.
- `ffprobe` reads the returned MP4.
- Width, height, fps, audio presence, and duration match the certified smoke profile. The returned video duration must match the reference audio duration within tolerance.
