# Function Replacement Matrix

This matrix is the working replacement plan for production-visible functions.

| Current function/model | Status | Local runtime target | Workflow/profile |
|---|---|---|---|
| `google/nano-banana` | Hidden saved-project alias | ComfyUI | `qwen_image_edit_2511_multi_gguf` |
| `google/veo` | Hidden saved-project alias | ComfyUI | `wan22_ti2v_5b_720p24_gguf`, first/last-frame workflow where applicable |
| `Hailuo/MiniMax/txt2vid` | Hidden saved-project alias | ComfyUI | `wan22_ti2v_5b_720p24_gguf` |
| `Hailuo/MiniMax/img2vid` | Hidden saved-project alias | ComfyUI | `wan22_ti2v_5b_720p24_gguf` |
| `Hailuo/MiniMax/subject2vid` | Hidden saved-project alias | ComfyUI | `ltx23_ic_lora_subject_i2v` |
| LTX 2.3 I2V workflow | Workflow pack started | ComfyUI | `ltx23_i2v` |

Entries are complete only after the corresponding GPU artifact test produces a real artifact through the addon plugin path.
