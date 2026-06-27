# chatterbox_turbo_tts_comfy

Local Chatterbox Turbo text-to-speech for `models_plugins/audio/chatterbox_turbo.py` when no reference audio is supplied.

## Required Nodes

This workflow uses `filliptm/ComfyUI_Fill-ChatterBox` at commit `596850bc61665e9318914841b41ee4154253f020`.

- `FL_ChatterboxTurboTTS`
- ComfyUI core `SaveAudio`

The pinned node exposes `text`, `temperature`, `top_k`, `top_p`, `repetition_penalty`, `seed`, optional `audio_prompt`, `use_cpu`, and `keep_model_loaded`.

## Model Files

Model artifacts are downloaded only by the Slopperly model manager from `https://huggingface.co/ResembleAI/chatterbox-turbo`.

- `ve.safetensors`
- `t3_turbo_v1.safetensors`
- `s3gen_meanflow.safetensors`
- `tokenizer_config.json`
- `special_tokens_map.json`
- `vocab.json`
- `merges.txt`
- `added_tokens.json`
- `conds.pt`

The Comfy node expects these under `ComfyUI/models/chatterbox/chatterbox_turbo/`. Generation-time hosted inference is not used.

## UI Parameter Mapping

- `ModelInputs.prompt` -> `FL_ChatterboxTurboTTS.text`
- `ModelInputs.temperature` -> `FL_ChatterboxTurboTTS.temperature`
- `ModelInputs.seed` -> `FL_ChatterboxTurboTTS.seed`
- optional scene/input `chatterbox_turbo_top_k` -> `FL_ChatterboxTurboTTS.top_k`
- optional scene/input `chatterbox_turbo_top_p` -> `FL_ChatterboxTurboTTS.top_p`
- optional scene/input `chatterbox_turbo_repetition_penalty` -> `FL_ChatterboxTurboTTS.repetition_penalty`
- optional scene/input `chatterbox_use_cpu` -> `FL_ChatterboxTurboTTS.use_cpu`
- optional scene/input `chatterbox_keep_model_loaded` -> `FL_ChatterboxTurboTTS.keep_model_loaded`

The existing UI still shows audio duration, exaggeration, pace, and reference-audio controls. Duration, exaggeration, and pace are recorded as deliberately unmapped because the pinned Turbo node does not expose those inputs. Reference audio routes to `chatterbox_turbo_ref_tts_comfy`.

## Output Contract

`SaveAudio` writes one local audio artifact with prefix `slopperly_chatterbox_turbo`. The plugin copies the first returned artifact to the existing result path and returns that path for VSE insertion.

## Test Command

```bash
pytest tests/gpu/test_chatterbox_turbo.py --device cuda --profile smoke_16gb
```

## Expected Validation

The GPU test imports `ChatterboxTurboPlugin`, calls `load()` and `generate()` against owned ComfyUI, and validates a 24 kHz non-silent FLAC artifact. Missing runtime, node classes, or model artifacts are recorded as blocked certification evidence.
