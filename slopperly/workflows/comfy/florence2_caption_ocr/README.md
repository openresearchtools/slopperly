# florence2_caption_ocr

Local ComfyUI workflow pack for the existing Florence-2 image caption, OCR, and Ideogram-4 prompt extraction path.

## Existing Addon Function

- Current plugin/function: `models_plugins/text/florence2.py`.
- Runtime: Slopperly-owned ComfyUI.
- API workflow: `workflow.api.json`.
- Editable workflow: `workflow.editable.json`.

## Required Nodes

- `LoadImage`
- `DownloadAndLoadFlorence2Model`
- `Florence2Run`

The Florence classes come from the pinned `kijai/ComfyUI-Florence2` node pack in `slopperly/runtime/comfy/nodes.lock.yaml`.

## Model Files

- `models/LLM/Florence-2-large/config.json`
- `models/LLM/Florence-2-large/model.safetensors`

The Comfy node can download the model from `microsoft/Florence-2-large`; Slopperly records the same Hugging Face repository in `slopperly/config/models.yaml` as a local artifact source only.

## UI Parameter Mapping

- selected image strip -> upload to Comfy input storage, then patch node `1`, input `image`
- `florence2_task` -> node `3`, input `task`
- `florence2_text_input` -> node `3`, input `text_input`
- `seed` -> node `3`, input `seed`

`steps` and `guidance` are deliberately unmapped because `Florence2Run` exposes `max_new_tokens`, `num_beams`, and `do_sample` instead of diffusion sampler controls.

## Output Contract

Node `3` returns Florence2Run text and JSON data through Comfy history outputs. The Slopperly Comfy runner collects text-like history keys, and the plugin maps them back to the existing plain caption string or Ideogram-4 JSON string.

## Test Command

```bash
pytest tests/gpu/test_florence2_caption.py --device cuda
```

## Expected Validation

- Comfy `/object_info` includes `LoadImage`, `DownloadAndLoadFlorence2Model`, and `Florence2Run`.
- `workflow.api.json` validates as Comfy API format.
- The addon plugin path submits the workflow through `SlopperlyRuntimeGateway`.
- Caption mode returns non-empty text.
- Ideogram-4 mode returns parseable JSON preserving the existing top-level keys.
