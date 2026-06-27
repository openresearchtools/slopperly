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
| `ZuluVision/MoviiGen1.1_Prompt_Rewriter` | Migrated wrapper, GPU/server test pending | llama.cpp | `llamacpp_prompt_rewriter` |
| `faster-whisper-transcribe` | Migrated wrapper, GPU/server test pending | vLLM | `vllm_whisper_large_v3_turbo_stt` |
| `OmniVoice` | Migrated wrapper, GPU/server test pending | vLLM-Omni | `omnivoice_vllm_omni` |
| `MOSS-TTS` | Migrated to pinned Nano profile, GPU/server test pending | vLLM-Omni | `moss_tts_nano_vllm_omni` |
| `ZhengPeng7/BiRefNet_HR` | Migrated wrapper, GPU/server test pending | ComfyUI | `birefnet_rmbg` |
| `nvidia/maxine-vsr` | Migrated wrapper, GPU/server test pending | ComfyUI | `local_image_vsr_upscale` |
| `nvidia/maxine-vsr-video` | Migrated wrapper, GPU/server test pending | ComfyUI | `local_video_vsr_upscale` |
| `Qwen/Qwen-Image-2512` | Migrated wrapper, GPU/server test pending | ComfyUI | `qwen_image_2512_t2i_gguf`, `qwen_image_2512_i2i_gguf` |
| `Qwen/Qwen-Image-Edit-2511` | Migrated wrapper, GPU/server test pending | ComfyUI | `qwen_image_edit_2511_multi_gguf` |
| `StemSplitter` | Migrated wrapper, GPU/server test pending | ComfyUI | `audio_stem_split_demucs` |
| `MMAudio` | Migrated wrapper, GPU/server test pending | ComfyUI | `mmaudio_video_to_audio` |
| `cocktailpeanut/stable-audio-3-medium-base` | Migrated wrapper, GPU/server test pending | ComfyUI | `stable_audio_3_medium_base` |
| `ACE-Step/acestep-v15-xl-turbo-diffusers` | Migrated wrapper, GPU/server test pending | ComfyUI | `ace_step_15_music` |
| `tintwotin/Foundation-1-Diffusers` | Migrated wrapper, GPU/server test pending | ComfyUI | `foundation1_music_loop` |
| `Chatterbox` | Migrated wrapper, GPU/server test pending | ComfyUI | `chatterbox_tts_vc_comfy` |
| `ChatterboxTurbo` | Migrated wrapper, GPU/server test pending | ComfyUI | `chatterbox_turbo_tts_comfy` |
| `ChatterboxMultilingual` | Migrated wrapper, GPU/server test pending | ComfyUI | `chatterbox_multilingual_tts_comfy` |

Entries are complete only after the corresponding GPU artifact test produces a real artifact through the addon plugin path.
