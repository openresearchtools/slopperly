# ace_step_15_music

Local ACE-Step 1.5 text-to-music generation for `models_plugins/audio/ace_step.py`.

## Required Nodes

This workflow uses ComfyUI core nodes from pinned ComfyUI commit `603d891eaf045d726d9c23276b4428daf2977624`.

- `UNETLoader`
- `VAELoader`
- `DualCLIPLoader`
- `TextEncodeAceStepAudio1.5`
- `EmptyAceStep1.5LatentAudio`
- `ConditioningZeroOut`
- `ModelSamplingAuraFlow`
- `KSampler`
- `VAEDecodeAudio`
- `SaveAudio`

Sources checked:

- Comfy ACE-Step 1.5 workflow template: `https://raw.githubusercontent.com/Comfy-Org/workflow_templates/main/templates/audio_ace_step1_5_xl_base.json`
- Comfy ACE node source: `https://raw.githubusercontent.com/comfyanonymous/ComfyUI/603d891eaf045d726d9c23276b4428daf2977624/comfy_extras/nodes_ace.py`
- Comfy loader/sampler source: `https://raw.githubusercontent.com/comfyanonymous/ComfyUI/603d891eaf045d726d9c23276b4428daf2977624/nodes.py`

No `ace-step/ACE-Step-ComfyUI` cloud/local HTTP node is used in the production path.

## Model Files

Model artifacts are downloaded only through the Slopperly model manager from `https://huggingface.co/Comfy-Org/ace_step_1.5_ComfyUI_files`.

- `split_files/diffusion_models/acestep_v1.5_xl_turbo_bf16.safetensors` -> `ComfyUI/models/diffusion_models/acestep_v1.5_xl_turbo_bf16.safetensors`
- `split_files/vae/ace_1.5_vae.safetensors` -> `ComfyUI/models/vae/ace_1.5_vae.safetensors`
- `split_files/text_encoders/qwen_0.6b_ace15.safetensors` -> `ComfyUI/models/text_encoders/qwen_0.6b_ace15.safetensors`
- `split_files/text_encoders/qwen_4b_ace15.safetensors` -> `ComfyUI/models/text_encoders/qwen_4b_ace15.safetensors`

The legacy plugin ID `ACE-Step/acestep-v15-xl-turbo-diffusers` remains a compatibility alias. Generation no longer loads a Diffusers pipeline or downloads from Hugging Face at runtime.

## UI Parameter Mapping

- `ModelInputs.prompt` -> `TextEncodeAceStepAudio1.5.tags`
- `ModelInputs.lyrics` -> `TextEncodeAceStepAudio1.5.lyrics`
- `ModelInputs.audio_length` -> `TextEncodeAceStepAudio1.5.duration` and `EmptyAceStep1.5LatentAudio.seconds`
- `ModelInputs.steps` -> `KSampler.steps`
- `ModelInputs.guidance` -> `KSampler.cfg`
- `ModelInputs.seed` -> `TextEncodeAceStepAudio1.5.seed` and `KSampler.seed`
- `ModelInputs.bpm` -> `TextEncodeAceStepAudio1.5.bpm`
- `ModelInputs.key_scale` -> `TextEncodeAceStepAudio1.5.keyscale`
- `ModelInputs.time_signature` -> `TextEncodeAceStepAudio1.5.timesignature`
- Optional scene/runtime overrides such as `ace_step_language`, `ace_step_sampler`, `ace_step_scheduler`, and `ace_step_aura_shift` patch the exact inputs listed in `params.schema.json`.

The existing ACE-Step UI does not expose a negative prompt. The workflow follows the official Comfy template pattern by zeroing the positive conditioning through `ConditioningZeroOut` for sampler negative conditioning.

## Output Contract

`SaveAudio` writes one local FLAC artifact with prefix `slopperly_ace_step_15`. The plugin returns the artifact path produced by the existing `ModelPlugin.generate()` path, preserving VSE insertion behavior for a single generated audio file.

Expected validation:

- file is readable by `ffprobe` or `soundfile`
- duration matches requested `audio_length` within tolerance
- sample rate is 48 kHz for the ACE-Step 1.5 split Comfy files
- waveform is non-silent

## Test Command

```bash
pytest tests/gpu/test_ace_step.py --device cuda --profile smoke_16gb
```

Integration smoke:

```bash
python tests/integration/test_local_plugin_paths.py
python tests/integration/test_comfy_workflow_runner.py
```

## Expected Validation

The GPU test imports `AceStepPlugin`, calls `load()` and `generate()` against the configured owned ComfyUI runtime, and validates a real FLAC artifact. If ComfyUI, the model files, or required node classes are missing, the test records BLOCKED certification evidence rather than exposing the dropdown entry as production-certified.
