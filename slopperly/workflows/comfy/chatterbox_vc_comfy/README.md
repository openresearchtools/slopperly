# chatterbox_vc_comfy

Local Chatterbox voice-conversion compatibility workflow for `models_plugins/audio/chatterbox.py` when the existing audio operator marks the selected sound strip as voice-clone input.

## Required Nodes

This workflow uses `filliptm/ComfyUI_Fill-ChatterBox` at commit `596850bc61665e9318914841b41ee4154253f020`.

- ComfyUI core `LoadAudio`
- `FL_ChatterboxVC`
- ComfyUI core `SaveAudio`

The pinned source exposes class key `FL_ChatterboxVC` with required `input_audio`, `target_voice`, and `seed` inputs plus optional `use_cpu` and `keep_model_loaded`.

## Model Files

Model artifacts are downloaded only by the Slopperly model manager from `https://huggingface.co/ResembleAI/chatterbox`.

- `s3gen.pt`
- `conds.pt`

The Comfy node expects these under `ComfyUI/models/chatterbox/chatterbox_vc/`. Generation-time hosted inference is not used.

## UI Parameter Mapping

- selected sound strip or reference audio -> upload to Comfy input storage through `/upload/image`, then patch node `1`, input `audio`
- node `1`, output `0` -> `FL_ChatterboxVC.input_audio`
- node `1`, output `0` -> `FL_ChatterboxVC.target_voice`
- `ModelInputs.seed` -> `FL_ChatterboxVC.seed`
- optional scene/input `chatterbox_use_cpu` -> `FL_ChatterboxVC.use_cpu`
- optional scene/input `chatterbox_keep_model_loaded` -> `FL_ChatterboxVC.keep_model_loaded`

The existing Chatterbox UI supplies one audio path in VC mode. The pinned Comfy VC node requires both source speech and target voice audio. Until the add-on has a second target voice selector, this compatibility graph wires the same uploaded audio to both inputs and records that limitation in `params.schema.json`.

## Output Contract

`SaveAudio` writes one local audio artifact with prefix `slopperly_chatterbox_vc`. The plugin copies the first returned artifact to the existing result path and returns that path for VSE insertion.

Expected validation:

- file is readable by `ffprobe` or `soundfile`
- waveform is non-silent
- runtime history confirms `FL_ChatterboxVC` executed locally

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

The compatibility graph is considered local-backend complete when the Comfy runtime has `FL_ChatterboxVC`, accepts the uploaded audio, and returns a readable artifact. Cross-speaker VC remains blocked until the UI/runtime contract carries a separate target voice audio path.
