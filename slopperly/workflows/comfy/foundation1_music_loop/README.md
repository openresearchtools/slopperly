# foundation1_music_loop

Local Foundation-1 structured text-to-sample loop generation for `models_plugins/audio/foundation_music.py`.

## Required Nodes

This workflow uses the pinned `Saganaki22/ComfyUI-Foundation-1` node pack at commit `41f4692dd20268d40cc806989063a7a1f4b5b3fe`.

- `Foundation1ModelLoader`
- `Foundation1Generate`

It also uses ComfyUI core `SaveAudio` from pinned ComfyUI commit `603d891eaf045d726d9c23276b4428daf2977624`.

Sources checked:

- `ComfyUI-Foundation-1/__init__.py` registers `Foundation1ModelLoader` and `Foundation1Generate`.
- `nodes/loader_node.py` exposes `Foundation1ModelLoader.model` and `Foundation1ModelLoader.attention`.
- `nodes/generate_node.py` exposes `Foundation1Generate.tags`, `bpm`, `bars`, `key`, `steps`, `cfg_scale`, `seed`, `sampler_type`, `sigma_min`, `sigma_max`, `unload_after_generate`, `torch_compile`, and optional `init_noise_level`.

No cloud, hosted inference, or generation-time Hugging Face API node is used in the production graph.

## Model Files

Model artifacts are downloaded only through the Slopperly model manager from `https://huggingface.co/RoyalCities/Foundation-1`.

- `Foundation_1.safetensors` -> `ComfyUI/models/stable_audio/Foundation-1/Foundation_1.safetensors`
- `model_config.json` -> `ComfyUI/models/stable_audio/Foundation-1/model_config.json`

The loader's model dropdown label for this placement is `Foundation-1/Foundation_1.safetensors`. The verified upstream `model_config.json` declares `sample_rate` 44100 and stereo audio.

The legacy plugin ID `tintwotin/Foundation-1-Diffusers` remains a compatibility alias. Generation no longer loads a Diffusers pipeline or downloads from Hugging Face at runtime.

## UI Parameter Mapping

- `ModelInputs.prompt`, with negative prompt folded in as an avoidance phrase by the plugin -> `Foundation1Generate.tags`
- `ModelInputs.steps` -> `Foundation1Generate.steps`
- `ModelInputs.seed` -> `Foundation1Generate.seed`
- Requested `ModelInputs.audio_length` -> nearest supported `foundation1_bpm` and `foundation1_bars` pair, using `round(bars * 4 / bpm * 60)`
- Optional scene/input field `foundation1_bpm` -> `Foundation1Generate.bpm`
- Optional scene/input field `foundation1_bars` -> `Foundation1Generate.bars`
- Optional scene/input field `foundation1_key` -> `Foundation1Generate.key`
- Optional scene field `foundation1_model` -> `Foundation1ModelLoader.model`
- Optional scene field `foundation1_attention` -> `Foundation1ModelLoader.attention`
- Optional scene field `foundation1_cfg_scale` -> `Foundation1Generate.cfg_scale`
- Optional scene field `foundation1_sampler_type` -> `Foundation1Generate.sampler_type`
- Optional scene field `foundation1_sigma_min` -> `Foundation1Generate.sigma_min`
- Optional scene field `foundation1_sigma_max` -> `Foundation1Generate.sigma_max`
- Optional scene field `foundation1_unload_after_generate` -> `Foundation1Generate.unload_after_generate`
- Optional scene field `foundation1_torch_compile` -> `Foundation1Generate.torch_compile`
- Optional scene field `foundation1_init_noise_level` -> `Foundation1Generate.init_noise_level`
- Runtime field `foundation1_filename_prefix` -> `SaveAudio.filename_prefix`

The existing plugin UI does expose a negative prompt. The native Foundation-1 Comfy node does not expose separate negative conditioning, so the production wrapper preserves the field by adding it to the structured tags as an avoidance phrase.

## Output Contract

`SaveAudio` writes one local FLAC artifact with a per-invocation `slopperly_foundation1_<seed>_<nonce>` prefix so repeated identical prompts still produce a fresh file. The plugin converts the first returned artifact to the existing `.wav` audio-result file path and returns that path to the queue, preserving VSE insertion behavior for a single generated audio file.

Expected validation:

- WAV file is readable by `ffprobe` or `soundfile`
- sample rate is 44100
- duration matches the selected BPM/bar mapping within tolerance
- waveform is non-silent

## Test Command

```bash
pytest tests/gpu/test_foundation_music.py --device cuda --profile smoke_16gb
```

Integration smoke:

```bash
python tests/integration/test_local_plugin_paths.py
python tests/integration/test_comfy_workflow_runner.py
```

## Expected Validation

The GPU test imports `FoundationMusicPlugin`, calls `load()` and `generate()` against the configured owned ComfyUI runtime, and validates a real FLAC artifact. If ComfyUI, the model files, or required node classes are missing, the test records BLOCKED certification evidence rather than exposing the dropdown entry as production-certified.
