# chatterbox_tts_comfy

Local Chatterbox text-to-speech for `models_plugins/audio/chatterbox.py` when no reference audio is supplied.

## Required Nodes

This workflow uses `filliptm/ComfyUI_Fill-ChatterBox` at commit `596850bc61665e9318914841b41ee4154253f020`.

- `FL_ChatterboxTTS`
- ComfyUI core `SaveAudio`

The pinned source exposes class key `FL_ChatterboxTTS` with inputs `text`, `exaggeration`, `cfg_weight`, `temperature`, `seed`, optional `audio_prompt`, `use_cpu`, and `keep_model_loaded`.

## Model Files

Model artifacts are downloaded only by the Slopperly model manager from `https://huggingface.co/ResembleAI/chatterbox`.

- `ve.safetensors`
- `t3_cfg.safetensors`
- `s3gen.safetensors`
- `tokenizer.json`
- `conds.pt`

The Comfy node expects these under `ComfyUI/models/chatterbox/chatterbox/`. Generation-time hosted inference is not used.

## UI Parameter Mapping

- `ModelInputs.prompt` -> `FL_ChatterboxTTS.text`
- `ModelInputs.exaggeration` -> `FL_ChatterboxTTS.exaggeration`
- `ModelInputs.pace` -> `FL_ChatterboxTTS.cfg_weight`
- `ModelInputs.temperature` -> `FL_ChatterboxTTS.temperature`
- `ModelInputs.seed` -> `FL_ChatterboxTTS.seed`
- optional scene/input `chatterbox_use_cpu` -> `FL_ChatterboxTTS.use_cpu`
- optional scene/input `chatterbox_keep_model_loaded` -> `FL_ChatterboxTTS.keep_model_loaded`

`audio_length`, `speed`, and `remove_silence` remain visible in the existing UI but are deliberately unmapped because this pinned node does not expose those controls.

## Output Contract

`SaveAudio` writes one local audio artifact with prefix `slopperly_chatterbox`. The plugin copies the first returned artifact to the existing result path and returns that path for VSE insertion.

Expected validation:

- file is readable by `ffprobe` or `soundfile`
- sample rate is 24000 for the standard Chatterbox profile
- waveform is non-silent

## Test Command

```bash
pytest tests/gpu/test_chatterbox.py --device cuda --profile smoke_16gb
```

Integration smoke:

```bash
python tests/integration/test_local_plugin_paths.py
python tests/integration/test_comfy_workflow_runner.py
```

## Expected Validation

The GPU test imports `ChatterboxPlugin`, calls `load()` and `generate()` against the configured owned ComfyUI runtime, and validates a real FLAC artifact. If ComfyUI, the model files, or required node classes are missing, certification records the blocked reason.
