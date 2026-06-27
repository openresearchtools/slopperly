# Provider Migration Ledger

This ledger tracks production provider removal and local-runtime replacement work.

## 2026-06-27 Local-only guard and legacy alias block

### Production Cloud Paths Removed

- Moved the fal adapter and manifest out of production discovery to `reference/palladium/remote_backends/`.
- Deleted `MiniMax_API.txt` from the production tree.
- Removed MiniMax API submit/query/download helpers from `utils/helpers.py`.
- Removed the Google Gemini API key preference from the production preferences UI/state.
- Removed Gemini API key capture from queued job snapshots.
- Added a localhost-only guard to the generic backend client.

### Hidden Saved-project Aliases

| Legacy model ID | Production dropdown | Local target |
|---|---|---|
| `google/nano-banana` | Hidden | `qwen_image_edit_2511_multi_gguf` |
| `google/veo` | Hidden | `wan22_ti2v_5b_720p24_gguf` or local first/last-frame video workflow |
| `Hailuo/MiniMax/txt2vid` | Hidden | `wan22_ti2v_5b_720p24_gguf` |
| `Hailuo/MiniMax/img2vid` | Hidden | `wan22_ti2v_5b_720p24_gguf` |
| `Hailuo/MiniMax/subject2vid` | Hidden | `ltx23_ic_lora_subject_i2v` |

The aliases remain registered so saved projects can resolve the old model IDs, but they are not listed in production dropdowns.

### Runtime/Workflow Work Added

- Added `slopperly.runtime` with a local runtime gateway.
- Added a ComfyUI API client and workflow runner that rejects non-local URLs.
- Added pinned Comfy node manifest at `slopperly/runtime/comfy/nodes.lock.yaml`.
- Added runtime/model/dropdown registry seed files in `slopperly/config/`.
- Added the first workflow pack: `slopperly/workflows/comfy/ltx23_i2v/`.

### Verification

- `python -m compileall models models_plugins slopperly utils properties operators`
- `python test_remote_backend.py`
- `python -m slopperly.audit.no_cloud --root .`

### Blocked / Not Yet Certified

- Hidden aliases are not production-complete until their target workflow packs exist and GPU artifact tests pass through the addon `ModelPlugin.generate()` path.
- The LTX 2.3 workflow pack is structurally committed, but GPU execution has not run in this block.
- Remaining local migrations for Qwen, Wan, FLUX, audio, STT, TTS, and llama.cpp are still pending.
