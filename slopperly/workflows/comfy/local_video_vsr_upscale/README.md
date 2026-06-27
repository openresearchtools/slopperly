# local_video_vsr_upscale

Local ComfyUI workflow pack for the former NVIDIA Maxine video super-resolution plugin.

## Existing Addon Function

- Current plugin/function: `models_plugins/video/maxine_vsr_video.py`
- Legacy model ID: `nvidia/maxine-vsr-video`
- Runtime: Slopperly-owned ComfyUI.
- API workflow: `workflow.api.json`.
- Editable workflow: `workflow.editable.json`.

The production dropdown label is `Video: Local Super Resolution`; no NVIDIA Maxine runtime is used.

## Required Nodes

- ComfyUI-VideoHelperSuite `VHS_LoadVideo`
- ComfyUI core `UpscaleModelLoader`
- ComfyUI core `ImageUpscaleWithModel`
- ComfyUI core `ImageScale`
- ComfyUI-VideoHelperSuite `VHS_VideoCombine`

The VideoHelperSuite node inputs and outputs were verified against pinned commit `4ee72c065db22c9d96c2427954dc69e7b908444b`. `VHS_LoadVideo` exposes `video`, `force_rate`, `custom_width`, `custom_height`, `frame_load_cap`, `skip_first_frames`, and `select_every_nth`, and returns `IMAGE`, `frame_count`, `audio`, and `video_info`. `VHS_VideoCombine` accepts `images`, `frame_rate`, `filename_prefix`, `format`, `save_output`, and optional `audio`.

The Comfy core upscale node inputs were verified against pinned ComfyUI commit `603d891eaf045d726d9c23276b4428daf2977624`.

## Model Files

The workflow uses the same local upscaler artifact as image VSR:

- Hugging Face artifact source: `ai-forever/Real-ESRGAN`
- File: `RealESRGAN_x4.pth`
- Comfy location: `models/upscale_models/RealESRGAN_x4.pth`

## UI Parameter Mapping

- selected video strip -> upload to Comfy input storage through Comfy's `/upload/image` endpoint, then patch node `1`, input `video`
- source video fps -> node `5`, input `frame_rate`
- `width` -> node `4`, input `width`
- `height` -> node `4`, input `height`
- optional scene field `local_vsr_model` -> node `2`, input `model_name`
- optional scene field `local_vsr_upscale_method` -> node `4`, input `upscale_method`
- optional scene field `local_vsr_crop` -> node `4`, input `crop`
- optional scene field `local_video_vsr_frame_load_cap` -> node `1`, input `frame_load_cap`
- optional scene field `local_video_vsr_format` -> node `5`, input `format`
- `VHS_LoadVideo` audio output -> node `5`, input `audio`

The old Maxine-only quality selector is deliberately unmapped because this workflow does not use the NVIDIA Maxine runtime.

## Output Contract

Node `5` saves an MP4 using `video/h264-mp4`. The plugin path must return the local file path. The artifact must be ffprobe-readable, match the requested width and height, preserve the source fps/duration within one frame, and include an audio stream when the source has audio.

## Test Command

```bash
pytest tests/gpu/test_local_video_vsr_upscale.py --device cuda
```

## Expected Validation

- Comfy `/object_info` includes all node classes listed above.
- `workflow.api.json` validates as Comfy API format.
- The addon plugin path calls `MaxineVSRVideoPlugin.load()` and `MaxineVSRVideoPlugin.generate()`.
- The returned MP4 width and height match the requested resolution.
- The returned MP4 fps and duration match the source fixture within tolerance.
- The returned MP4 contains audio when the input video contains audio.
