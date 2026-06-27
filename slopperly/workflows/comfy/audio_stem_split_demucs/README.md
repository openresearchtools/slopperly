# audio_stem_split_demucs

Local ComfyUI workflow pack for the existing Stem Splitter audio plugin and sequencer operator.

## Existing Addon Function

- Current plugin/function: `models_plugins/audio/stem_split.py`
- Legacy model ID: `StemSplitter`
- Runtime: Slopperly-owned ComfyUI.
- API workflow: `workflow.api.json`.
- Editable workflow: `workflow.editable.json`.

The production display label is `Stem Splitter (Local Comfy Demucs)`. No `demucs_onnx` execution remains in the plugin path or the dedicated sequencer operator.

## Required Nodes

- ComfyUI core `LoadAudio`
- audio-separation-nodes-comfyui `AudioSeparation`
- ComfyUI core `SaveAudio`

Pinned sources verified:

- ComfyUI commit `603d891eaf045d726d9c23276b4428daf2977624`: `LoadAudio` exposes input `audio`; `SaveAudio` exposes inputs `audio` and `filename_prefix` and writes FLAC audio.
- `christian-byrne/audio-separation-nodes-comfyui` commit `ac339561973f0c1e56db2f9d40f11b0fddda6763`: class key `AudioSeparation` exposes input `audio`, optional `chunk_fade_shape`, `chunk_length`, and `chunk_overlap`, and returns four `AUDIO` outputs named Bass, Drums, Other, and Vocals.

## Model Files

The pinned node uses Torchaudio `HDEMUCS_HIGH_MUSDB_PLUS`, which loads asset key `models/hdemucs_high_trained.pt` and expects a 44.1 kHz Hybrid Demucs checkpoint.

- Hugging Face artifact source recorded for Slopperly model inventory: `paobukaidecha/hdemucs_high_trained`
- File: `hdemucs_high_trained.pt`
- Required owned-cache target: `ComfyUI/models/torchaudio/hdemucs_high_trained.pt`
- Required Torchaudio runtime mirror: `~/.cache/torch/hub/torchaudio/models/hdemucs_high_trained.pt`

This workflow must be run only after the checkpoint is already present in the owned cache and mirrored into the Torchaudio hub cache. `python -m slopperly.models.download --model audio_stem_split_demucs --accept-licenses` prepares both locations. Runtime generation is not allowed to download model artifacts.

## UI Parameter Mapping

- selected audio/movie strip audio path -> upload to Comfy input storage through `/upload/image`, then patch node `1`, input `audio`
- optional scene field `stem_split_chunk_fade_shape` -> node `2`, input `chunk_fade_shape`
- optional scene field `stem_split_chunk_length` -> node `2`, input `chunk_length`
- optional scene field `stem_split_chunk_overlap` -> node `2`, input `chunk_overlap`
- node `2`, output `0` -> node `3`, input `audio` -> bass stem
- node `2`, output `1` -> node `4`, input `audio` -> drums stem
- node `2`, output `2` -> node `5`, input `audio` -> other stem
- node `2`, output `3` -> node `6`, input `audio` -> vocals stem

The existing stem checkbox behavior is preserved by the plugin wrapper after Comfy returns all four stems. The old six-stem `htdemucs_6s` variant is blocked with a concrete diagnostic because this pinned Comfy node exposes only bass, drums, other, and vocals.

## Output Contract

Nodes `3` through `6` save FLAC audio artifacts with prefixes `slopperly_stem_bass`, `slopperly_stem_drums`, `slopperly_stem_other`, and `slopperly_stem_vocals`. The plugin path copies selected outputs to the existing multi-stem result shape:

```text
MULTI_STEM:{"vocals": "...", "drums": "...", "bass": "...", "other": "..."}
```

Each returned artifact must be readable audio, have a duration matching the source audio within tolerance, and be inserted as individual VSE sound strips by the existing queue insertion logic.

## Test Command

```bash
pytest tests/gpu/test_stem_split.py --device cuda
```

## Expected Validation

- Comfy `/object_info` includes `LoadAudio`, `AudioSeparation`, and `SaveAudio`.
- `workflow.api.json` validates as Comfy API format.
- The addon plugin path calls `StemSplitterPlugin.load()` and `StemSplitterPlugin.generate()`.
- The returned `MULTI_STEM` payload contains vocals, drums, bass, and other by default.
- Each stem artifact has the same duration as `tests/fixtures/stem_split_source.wav` within tolerance.
