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
| `Tongyi-MAI/Z-Image` | Migrated wrapper, GPU/server test pending | ComfyUI | `zimage_t2i_i2i`, `zimage_t2i_i2i_img2img` |
| `Tongyi-MAI/Z-Image-Turbo` | Migrated wrapper, GPU/server test pending | ComfyUI | `zimage_turbo_t2i_i2i`, `zimage_turbo_t2i_i2i_img2img` |
| `mrfatso/anima-preview3-diffusers` | Migrated wrapper, GPU/server test pending | ComfyUI | `anima_t2i_i2i`, `anima_t2i_i2i_img2img` |
| `baidu/ERNIE-Image` | Migrated wrapper, GPU/server test pending | ComfyUI | `ernie_image_t2i` |
| `baidu/ERNIE-Image-Turbo` | Migrated wrapper, GPU/server test pending | ComfyUI | `ernie_image_turbo_t2i` |
| `ethanfel/Krea-2-Base-Diffusers` | Migrated wrapper, GPU/server test pending | ComfyUI | `krea2_base_t2i` |
| `OzzyGT/Krea_2_Turbo_sdnq_dynamic_8bit` | Migrated wrapper, GPU/server test pending | ComfyUI | `krea2_turbo_t2i` |
| `Alpha-VLLM/Lumina-Image-2.0` | Migrated wrapper, GPU/server test pending | ComfyUI | `lumina2_t2i` |
| `ideogram-ai/ideogram-4-nf4-diffusers` | Migrated wrapper, GPU/server test pending | ComfyUI | `ideogram4_t2i` |
| `black-forest-labs/FLUX.2-klein-4B` | Migrated wrapper, GPU/server test pending | ComfyUI | `flux2_klein_4b_t2i_edit`, `flux2_klein_4b_t2i_edit_img2img` |
| `ModelsLab/FLUX.2-klein-9B` | Migrated wrapper, GPU/server test pending | ComfyUI | `flux2_klein_9b_t2i_edit`, `flux2_klein_9b_t2i_edit_img2img` |
| `nomadoor/flux-2-klein-9B-schematic-lora` | Migrated wrapper, GPU/server test pending | ComfyUI | `flux2_klein_9b_schematic_lora` |
| `fuliucansheng/FLUX.1-Canny-dev-diffusers-lora` | Migrated wrapper, GPU/server test pending | ComfyUI | `flux1_canny_control` |
| `romanfratric234/FLUX.1-Depth-dev-lora` | Migrated wrapper, GPU/server test pending | ComfyUI | `flux1_depth_control` |
| `Runware/FLUX.1-Redux-dev` | Migrated wrapper, GPU/server test pending | ComfyUI | `flux_redux_restyle` |
| `yuvraj108c/FLUX.1-Kontext-dev` | Migrated wrapper, GPU/server test pending | ComfyUI | `flux_kontext_edit` |
| `kontext-community/relighting-kontext-dev-lora-v3` | Migrated wrapper, GPU/server test pending | ComfyUI | `kontext_relight` |
| `NucleusAI/Nucleus-Image` | Migrated wrapper, GPU/server test pending | ComfyUI | `nucleus_image_t2i` |
| `StemSplitter` | Migrated wrapper, GPU/server test pending | ComfyUI | `audio_stem_split_demucs` |
| `MMAudio` | Migrated wrapper, GPU/server test pending | ComfyUI | `mmaudio_video_to_audio` |
| `cocktailpeanut/stable-audio-3-medium-base` | Migrated wrapper, GPU/server test pending | ComfyUI | `stable_audio_3_medium_base` |
| `ACE-Step/acestep-v15-xl-turbo-diffusers` | Migrated wrapper, GPU/server test pending | ComfyUI | `ace_step_15_music` |
| `tintwotin/Foundation-1-Diffusers` | Migrated wrapper, GPU/server test pending | ComfyUI | `foundation1_music_loop` |
| `Chatterbox` | Migrated wrapper, GPU/server test pending | ComfyUI | `chatterbox_tts_vc_comfy` |
| `ChatterboxTurbo` | Migrated wrapper, GPU/server test pending | ComfyUI | `chatterbox_turbo_tts_comfy` |
| `ChatterboxMultilingual` | Migrated wrapper, GPU/server test pending | ComfyUI | `chatterbox_multilingual_tts_comfy` |

Entries are complete only after the corresponding GPU artifact test produces a real artifact through the addon plugin path.
