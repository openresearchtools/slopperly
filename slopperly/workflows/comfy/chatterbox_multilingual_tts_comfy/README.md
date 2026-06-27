# chatterbox_multilingual_tts_comfy

Local Chatterbox multilingual text-to-speech for `models_plugins/audio/chatterbox_multilingual.py` when no reference audio is supplied.

## Required Nodes

This workflow uses `filliptm/ComfyUI_Fill-ChatterBox` at commit `596850bc61665e9318914841b41ee4154253f020`.

- `FL_ChatterboxMultilingualTTS`
- ComfyUI core `SaveAudio`

The pinned node exposes `text`, `language`, `exaggeration`, `cfg_weight`, `temperature`, `repetition_penalty`, `min_p`, `top_p`, `seed`, optional `audio_prompt`, `use_cpu`, and `keep_model_loaded`.

## Model Files

Model artifacts are downloaded only by the Slopperly model manager from `https://huggingface.co/ResembleAI/chatterbox`.

- `ve.pt`
- `t3_mtl23ls_v2.safetensors`
- `s3gen.pt`
- `grapheme_mtl_merged_expanded_v1.json`
- `conds.pt`
- `Cangjie5_TC.json`

The Comfy node expects these under `ComfyUI/models/chatterbox/chatterbox_multilingual/`. Generation-time hosted inference is not used.

## UI Parameter Mapping

- Blender `scene.chatterbox_mtl_language` code -> plugin converts to Comfy label such as `English (en)` -> `FL_ChatterboxMultilingualTTS.language`
- `ModelInputs.prompt` -> `FL_ChatterboxMultilingualTTS.text`
- `ModelInputs.exaggeration` -> `FL_ChatterboxMultilingualTTS.exaggeration`
- `ModelInputs.pace` -> `FL_ChatterboxMultilingualTTS.cfg_weight`
- `ModelInputs.temperature` -> `FL_ChatterboxMultilingualTTS.temperature`
- `ModelInputs.seed` -> `FL_ChatterboxMultilingualTTS.seed`
- optional scene/input `chatterbox_multilingual_repetition_penalty` -> `FL_ChatterboxMultilingualTTS.repetition_penalty`
- optional scene/input `chatterbox_multilingual_min_p` -> `FL_ChatterboxMultilingualTTS.min_p`
- optional scene/input `chatterbox_multilingual_top_p` -> `FL_ChatterboxMultilingualTTS.top_p`
- optional scene/input `chatterbox_use_cpu` -> `FL_ChatterboxMultilingualTTS.use_cpu`
- optional scene/input `chatterbox_keep_model_loaded` -> `FL_ChatterboxMultilingualTTS.keep_model_loaded`

Audio duration, speed, and silence removal are deliberately unmapped because the pinned multilingual node does not expose those controls. Reference audio routes to `chatterbox_multilingual_ref_tts_comfy`.

## Output Contract

`SaveAudio` writes one local audio artifact with prefix `slopperly_chatterbox_multilingual`. The plugin copies the first returned artifact to the existing result path and returns that path for VSE insertion.

## Test Command

```bash
pytest tests/gpu/test_chatterbox_multilingual.py --device cuda --profile smoke_16gb
```

## Expected Validation

The GPU test imports `ChatterboxMultilingualPlugin`, calls `load()` and `generate()` against owned ComfyUI, and validates a 24 kHz non-silent FLAC artifact. Missing runtime, node classes, or model artifacts are recorded as blocked certification evidence.
