# stable_audio_3_medium_base

Local ComfyUI workflow pack for the existing Stable Audio 3 text-to-music plugin.

## Existing Addon Function

- Current plugin/function: `models_plugins/audio/_stable_audio_3.py`
- Legacy model ID: `cocktailpeanut/stable-audio-3-medium-base`
- Runtime: Slopperly-owned ComfyUI.
- API workflow: `workflow.api.json`.
- Editable workflow: `workflow.editable.json`.

The production plugin remains an audio plugin and keeps the prompt, negative prompt, audio duration, steps, guidance, and seed controls. The old direct `stable_audio_tools`, Torch, Torchaudio, and generation-time Hugging Face download path is no longer used by production generation.

## Required Nodes

- ComfyUI core `CheckpointLoaderSimple`
- ComfyUI core `CLIPLoader`
- ComfyUI core `CLIPTextEncode`
- ComfyUI core `ConditioningStableAudio`
- ComfyUI core `EmptyLatentAudio`
- ComfyUI core `KSampler`
- ComfyUI core `VAEDecodeAudio`
- ComfyUI core `SaveAudio`

Pinned sources verified:

- ComfyUI commit `603d891eaf045d726d9c23276b4428daf2977624`: `CheckpointLoaderSimple` exposes `ckpt_name`; `CLIPLoader` exposes `clip_name`, `type`, and optional `device`; `KSampler` exposes `seed`, `steps`, `cfg`, `sampler_name`, `scheduler`, and `denoise`.
- ComfyUI core audio nodes at the same commit expose `EmptyLatentAudio.seconds`, `ConditioningStableAudio.seconds_start` and `seconds_total`, `VAEDecodeAudio.samples`/`vae`, and `SaveAudio.audio`/`filename_prefix`.
- The official Stable Audio 3 Medium Base template uses `stable_audio_3_medium_base.safetensors` from `models/checkpoints` and `t5gemma_b_b_ul2.safetensors` from `models/text_encoders`.

## Model Files

Primary artifact source:

- Hugging Face artifact source: `Comfy-Org/stable-audio-3`
- Required checkpoint in `ComfyUI/models/checkpoints/`: `stable_audio_3_medium_base.safetensors`
- Required text encoder in `ComfyUI/models/text_encoders/`: `t5gemma_b_b_ul2.safetensors`

Runtime generation is not allowed to download these artifacts. Use `python -m slopperly.models.download --model stable_audio_3_medium_base --accept-licenses` before certification, then sync the downloaded files into the owned Comfy model folders.

## UI Parameter Mapping

- prompt -> node `3`, input `text`
- negative prompt -> node `4`, input `text`
- audio duration -> node `5`, input `seconds_total`, and node `6`, input `seconds`
- steps -> node `7`, input `steps`
- guidance -> node `7`, input `cfg`
- seed -> node `7`, input `seed`
- optional scene field `stable_audio_3_checkpoint` -> node `1`, input `ckpt_name`
- optional scene field `stable_audio_3_text_encoder` -> node `2`, input `clip_name`
- optional scene field `stable_audio_3_clip_type` -> node `2`, input `type`
- optional scene field `stable_audio_3_clip_device` -> node `2`, input `device`
- optional scene field `stable_audio_3_seconds_start` -> node `5`, input `seconds_start`
- optional scene field `stable_audio_3_batch_size` -> node `6`, input `batch_size`
- optional scene field `stable_audio_3_sampler` -> node `7`, input `sampler_name`
- optional scene field `stable_audio_3_scheduler` -> node `7`, input `scheduler`
- optional scene field `stable_audio_3_denoise` -> node `7`, input `denoise`

The old plugin's generation-time `prefs.hf_cache_dir` and `prefs.local_files_only` behavior is deliberately unmapped because model acquisition belongs to the Slopperly model manager.

## Output Contract

Node `9` saves one audio artifact with prefix `slopperly_stable_audio_3`. The plugin copies the first returned artifact to the existing audio-result file path and returns that path to the queue, so the existing sound-strip insertion behavior remains unchanged.

The committed production profile is 44.1 kHz FLAC/WAV-compatible audio. Duration must match the requested `audio_length` within tolerance.

## Test Command

```bash
pytest tests/gpu/test_stable_audio_3.py --device cuda
```

## Expected Validation

- Comfy `/object_info` includes `CheckpointLoaderSimple`, `CLIPLoader`, `CLIPTextEncode`, `ConditioningStableAudio`, `EmptyLatentAudio`, `KSampler`, `VAEDecodeAudio`, and `SaveAudio`.
- `workflow.api.json` validates as Comfy API format.
- The addon plugin path calls `StableAudio3Plugin.load()` and `StableAudio3Plugin.generate()`.
- The returned artifact is readable audio, has sample rate 44100, matches requested duration within tolerance, and is non-silent for real GPU certification.
