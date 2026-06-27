# mmaudio_video_to_audio

Local ComfyUI workflow pack for the existing MMAudio video-to-audio plugin.

## Existing Addon Function

- Current plugin/function: `models_plugins/audio/mmaudio.py`
- Legacy model ID: `MMAudio`
- Runtime: Slopperly-owned ComfyUI.
- API workflow: `workflow.api.json`.
- Editable workflow: `workflow.editable.json`.

The production plugin remains an audio plugin and keeps the prompt, negative prompt, selected video strip, duration, steps, guidance, and seed controls. The old direct `torch`/`mmaudio` execution path is no longer used by production generation.

## Required Nodes

- VideoHelperSuite `VHS_LoadVideo`
- ComfyUI-MMAudio `MMAudioModelLoader`
- ComfyUI-MMAudio `MMAudioFeatureUtilsLoader`
- ComfyUI-MMAudio `MMAudioSampler`
- ComfyUI-MMAudio `MMAudioVoCoderLoader`
- ComfyUI core `SaveAudio`

Pinned sources verified:

- `kijai/ComfyUI-MMAudio` commit `8eaeb72edc3aaf2059b57f2d96a1f6f689f19ae2`: `MMAudioModelLoader` exposes `mmaudio_model` and `base_precision`; `MMAudioFeatureUtilsLoader` exposes `vae_model`, `synchformer_model`, `clip_model`, `mode`, and `precision`; `MMAudioSampler` exposes `duration`, `steps`, `cfg`, `seed`, `prompt`, `negative_prompt`, `mask_away_clip`, `force_offload`, and optional `images`.
- `Kosinkadink/ComfyUI-VideoHelperSuite` commit `4ee72c065db22c9d96c2427954dc69e7b908444b`: `VHS_LoadVideo` loads the selected video strip frames for the sampler.
- ComfyUI commit `603d891eaf045d726d9c23276b4428daf2977624`: `SaveAudio` writes the generated audio artifact.

`MMAudioVoCoderLoader` is pinned and required for the node pack, but the committed 44k workflow does not connect it. In the pinned node implementation, 44k mode loads NVIDIA BigVGAN v2 from the local `models/mmaudio/nvidia/bigvgan_v2_44khz_128band_512x` snapshot inside `MMAudioFeatureUtilsLoader`. The explicit vocoder node is used by 16k mode only, which is not exposed until a separate artifact test passes.

## Model Files

Primary safetensors source:

- Hugging Face artifact source: `Kijai/MMAudio_safetensors`
- Required files in `ComfyUI/models/mmaudio/`:
- `mmaudio_large_44k_v2_fp16.safetensors`
- `mmaudio_vae_44k_fp16.safetensors`
- `mmaudio_synchformer_fp16.safetensors`
- `apple_DFN5B-CLIP-ViT-H-14-384_fp16.safetensors`

Auxiliary 44k vocoder source:

- Hugging Face artifact source: `nvidia/bigvgan_v2_44khz_128band_512x`
- Required local snapshot directory: `ComfyUI/models/mmaudio/nvidia/bigvgan_v2_44khz_128band_512x/`
- Required evidence files: `config.json`, `bigvgan_generator.pt`
- Ignored snapshot files: `*3msteps*`

Runtime generation is not allowed to download these artifacts. Use `python -m slopperly.models.download --model mmaudio_video_to_audio --accept-licenses` before certification.

## UI Parameter Mapping

- selected video strip path -> upload to Comfy input storage through Comfy's `/upload/image` endpoint, then patch node `1`, input `video`
- prompt -> node `4`, input `prompt`
- negative prompt -> node `4`, input `negative_prompt`
- audio duration -> node `4`, input `duration`
- steps -> node `4`, input `steps`
- guidance -> node `4`, input `cfg`
- seed -> node `4`, input `seed`
- optional scene field `mmaudio_model` -> node `2`, input `mmaudio_model`
- optional scene field `mmaudio_base_precision` -> node `2`, input `base_precision`
- optional scene field `mmaudio_vae_model` -> node `3`, input `vae_model`
- optional scene field `mmaudio_synchformer_model` -> node `3`, input `synchformer_model`
- optional scene field `mmaudio_clip_model` -> node `3`, input `clip_model`
- optional scene field `mmaudio_mode` -> node `3`, input `mode`
- optional scene field `mmaudio_precision` -> node `3`, input `precision`
- optional scene field `mmaudio_mask_away_clip` -> node `4`, input `mask_away_clip`
- optional scene field `mmaudio_force_offload` -> node `4`, input `force_offload`
- runtime field `mmaudio_filename_prefix` -> node `5`, input `filename_prefix`

Width, height, and fps are deliberately unmapped because this workflow generates an audio artifact from the selected video frames; it does not resize or re-encode the source video.

## Output Contract

Node `5` saves one FLAC audio artifact with a per-invocation `slopperly_mmaudio_<seed>_<nonce>` prefix so repeated identical prompts still produce a fresh file. The plugin converts the first returned artifact to the existing `.wav` audio-result file path and returns that path to the queue, so the existing sound-strip insertion behavior remains unchanged.

The committed production profile returns 44.1 kHz WAV audio to the UI path. Duration must match the requested `audio_length` within tolerance unless the source video is shorter, in which case the pinned sampler may clamp to the available video duration and the certification record must state that final duration.

## Test Command

```bash
pytest tests/gpu/test_mmaudio.py --device cuda
```

## Expected Validation

- Comfy `/object_info` includes `VHS_LoadVideo`, `MMAudioModelLoader`, `MMAudioFeatureUtilsLoader`, `MMAudioSampler`, and `SaveAudio`.
- `workflow.api.json` validates as Comfy API format.
- The addon plugin path calls `MMAudioPlugin.load()` and `MMAudioPlugin.generate()`.
- `tests/fixtures/video_vsr_source.mp4` is uploaded through Comfy's `/upload/image` endpoint.
- The returned WAV artifact is readable audio, has sample rate 44100, and is non-silent for real GPU certification.
