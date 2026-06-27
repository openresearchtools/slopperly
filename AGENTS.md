# Slopperly local backend migration specification

This document is the handoff target for the implementation agent. Read and update this document every time you work.

All work must be performed in the **WIP** branch and committed and pushed after each block of changes to maintain a complete history of tracked changes in case anything needs to be fixed or reverted.

Always read this document before starting work and do not deviate from it. Mark each line as completed before moving on to the next one until everything is tested, complete, and production-ready.

For testing, you are free to set up Python environments, ComfyUI, download required models, and test any workflows you create. An example of a working **LTX 2.3** video generation workflow (1080p, 24 FPS, 20 seconds, CPU/GPU weight offloading) for porting to ComfyUI is available in the `workflows` folder.

Run and validate **vLLM**, **Llama**, **ComfyUI**, and related components on the available RTX 4090. When porting functionality, ensure everything works correctly. All functions and workflows must be live-tested using real inputs and generated artifacts.

Be careful when selecting text encoders. If a text encoder can reasonably fit within 16 GB of VRAM with CPU offloading where appropriate, prefer the original **Safetensors** model over **GGUF**, unless GGUF is fully and properly supported as a text encoder for the specific image or video workflow.



You are the lead implementation agent for the Palladium-to-Slopperly fork.

Your task is to build local ai fork of the Palladium. Slopperly implementation must remove all external AI providers and route all generation, inference, speech, transcription, image, video, background removal, and workflow execution through local runtimes only.

This is not a prototype. Do not stub, mock, comment out, or cosmetically rename features. A feature is complete only when the existing UI button/flow still works end-to-end through the new local backend, or when you have documented the exact blocking reason with evidence and preserved a non-breaking UI state.

Primary goal:
Port Palladium into Slopperly as a local-only Ubuntu x64 CUDA application using only these AI execution backends:
1. llama.cpp for direct chat, prompt enhancement, planning, metadata generation, and other low-latency or long-context text inference OpenAI-compatible text, multimodal,
2. vLLM and vLLM-Omni for local  speech-to-text, and text-to-speech voice cloning, etc etc.
3. ComfyUI for image, video, image-editing, video-editing, frame interpolation, background removal, and node-graph workflows.
4. Blender only where the existing app already uses or requires Blender-style 3D/render logic.

No OpenAI, Anthropic, Gemini, Replicate, ElevenLabs, Runway, Stability hosted APIs, cloud Comfy services, hosted Hugging Face inference APIs, or other external inference providers may remain in the production Slopperly path. Hugging Face may be used only as a model artifact source for local download/cache.

## 0. Non-negotiable behavior

The Blender add-on UI is not to be redesigned. The existing panels, buttons, operator flow, strip picking, prompt fields, negative prompt fields, image/video/audio strip selectors, resolution controls, frame controls, seed, steps, guidance, strength, LoRA controls, and output insertion behavior stay intact.

The allowed UI changes are only these:

1. Remove external/cloud provider settings, API key prompts, and remote cloud backend discovery from production Slopperly.
2. Replace provider/runtime settings with local runtime settings for owned ComfyUI, vLLM, vLLM-Omni, and llama.cpp.
3. Replace cloud-only model dropdown entries with direct local model entries only after those direct local entries have passing artifact tests. Do not keep cloud-branded saved-project aliases in production Slopperly.
4. Remove or hide a dropdown model entry when there is no committed local workflow and no passing artifact test.
5. Rename Palladium to Slopperly.

The migration path is not “replace every old model with some newer model.” Existing local models already present in the add-on must be migrated to the permitted execution backends. For image/video/audio diffusion models, that means ComfyUI workflows or Slopperly-owned Comfy custom nodes. For STT/VLM, that means vLLM. For TTS/voice clone, existing models with real Comfy node support stay on Comfy, while Qwen/Fish/OmniVoice/MOSS profiles use vLLM-Omni. For text rewrite/chat/planning, that means llama.cpp.

Hugging Face is allowed only as a model artifact source. Hugging Face hosted inference is not allowed.


## Current code-derived parity report (2026-06-27)

This section is the live progress report. The historical implementation log below is evidence of scaffold work only and does not mark a function complete. A function is **DONE ON SPEC** only when the existing Blender UI flow calls the real `ModelPlugin.generate()` path, patches every relevant UI control into the local runtime workflow, produces a real local artifact on the RTX 4090, validates that artifact, and leaves the production dropdown certified for that exact profile.

Current hard truth:

- **DONE ON SPEC:** `audio/_stable_audio_3.py` Stable Audio 3, `audio/ace_step.py` ACE-Step, `audio/foundation_music.py` Foundation-1, `audio/mmaudio.py` MMAudio, `audio/chatterbox.py` Chatterbox, `audio/chatterbox_turbo.py` Chatterbox Turbo, `audio/chatterbox_multilingual.py` Chatterbox Multilingual, `audio/omnivoice.py` OmniVoice, `audio/moss_tts.py` MOSS-TTS, `text/faster_whisper_transcribe.py` STT, `text/marlin_video_captions.py` Marlin Video Captions, `text/moviigen_rewriter.py` prompt rewriter, `text/florence2.py` Florence2, and the certified four-stem path of `audio/stem_split.py` Stem Splitter from baseline commit `50cf377bf11349685010acb726a5e2b2e3cb9962` now have real local `ModelPlugin.generate()` PASS artifacts on the RTX 4090 profile. The Comfy-backed entries run through owned Slopperly ComfyUI; OmniVoice and MOSS-TTS run through the owned local vLLM-Omni runtime; STT and Marlin run through the owned local vLLM runtime; MoviiGen runs through the owned local llama.cpp runtime. Stem Splitter's old six-stem option and Chatterbox's true two-audio cross-speaker VC remain documented blocked modes until separate UI/workflow certification exists.
- **CERTIFIED NEW LOCAL DEFAULT:** new `video/wan_ti2v_5b.py` now has fresh direct T2V and direct I2V PASS records through `WanTI2V5BPlugin.generate()` against owned Slopperly ComfyUI on the RTX 4090 profile. This is not original Palladium parity; original Wan A14B, LTX, and other baseline functions still need their own migrations and real artifacts.
- **CERTIFICATION SUMMARY:** `python -m slopperly.audit.dropdown_certification --profile smoke_16gb --report-only` now reports `PASS wan22_ti2v_5b_720p24_gguf`, `PASS vllm_whisper_large_v3_turbo_stt`, `PASS vllm_video_caption_vlm`, `PASS florence2_caption_ocr`, `PASS audio_stem_split_demucs`, `PASS mmaudio_video_to_audio`, `PASS stable_audio_3_medium_base`, `PASS ace_step_15_music`, `PASS foundation1_music_loop`, `PASS chatterbox_tts_vc_comfy`, `PASS chatterbox_turbo_tts_comfy`, `PASS chatterbox_multilingual_tts_comfy`, `PASS llamacpp_prompt_rewriter`, `PASS omnivoice_vllm_omni`, `PASS moss_tts_nano_vllm_omni`, and 25 blocked entries still requiring the next model install/runtime/artifact test.
- **SCAFFOLD ONLY:** Comfy workflow packs, schemas, model registries, integration tests against fake loopback servers, and GPU test files exist for many functions. Those are not completion evidence.
- **NOT VALID COMPLETION:** any report that says a function is done because a fake Comfy/vLLM server accepted a payload is wrong. It must say scaffold only.
- **WORDING RULE:** human progress prose must state the required action when work is incomplete: install nodes/models, copy existing cache files, start the runtime, wire UI controls, or run the real artifact test. Machine certification JSON may contain a non-PASS status, but the AGENTS report must state the next action.
- **CLOUD REMOVAL:** Google Nano Banana, Google Veo, and MiniMax production plugins are deleted and must not return as aliases or dropdown entries. Their replacement local workflows must stand on their own direct certified entries.
- **DIRECT TORCH/DIFFUSERS VIDEO GAP:** `video/ltx2.py`, `video/ltx23_extend.py`, `video/ltx23_lipsync.py`, `video/ltx23_multi.py`, `video/ltx23_multi_ic_lora.py`, `video/skyreels.py`, `video/wan_t2v.py`, and `video/wan_i2v.py` still contain direct Torch/Diffusers/Transformers generation paths. These are not migrated to the required Comfy gateway.

Runtime and model-cache facts found on disk:

- Owned Slopperly Comfy runtime path: `.slopperly/runtimes/ComfyUI`.
- Owned Slopperly Comfy model cache was populated from `/home/user/Documents/Comfy/ComfyUI/models` into `.slopperly/runtimes/ComfyUI/models` on 2026-06-27 with `rsync -a --ignore-existing --partial`. Verification dry-run reported 0 remaining transfers. Owned cache size after copy: `202G`.
- Existing user Comfy cache to reuse before any download: `/home/user/Documents/Comfy/ComfyUI/models` (`191G` found). Do not redownload model assets that exist there; the copied owned cache still needs model-registry reconciliation before individual workflow certification.
- Existing LTX workflow source to port before making a new graph: `/home/user/Documents/Comfy/workflows/*.json`, including many LTX 2.3 Q5/NVFP4/FP8 API workflows and known-good I2V variants.
- LTX model assets now present in the owned cache include `ltx-2.3-22b-dev-fp8.safetensors`, `ltx-2.3-22b-dev-nvfp4.safetensors`, `ltx-2.3-22b-dev-UD-Q5_K_M.gguf`, `ltx-2.3-22b-distilled-1.1-Q5_K_M.gguf`, `ltx-2.3-22b-distilled-1.1-Q6_K.gguf`, LTX text projection/connector files, LTX video/audio VAEs, LTX IC-LoRA files, and LTX latent upscaler files.
- Wan A14B I2V Q5 high/low noise files now present in the owned cache: `.slopperly/runtimes/ComfyUI/models/unet/HighNoise/Wan2.2-I2V-A14B-HighNoise-Q5_K_M.gguf` and `.slopperly/runtimes/ComfyUI/models/unet/LowNoise/Wan2.2-I2V-A14B-LowNoise-Q5_K_M.gguf`.
- Existing user Comfy custom nodes include `ComfyUI-GGUF`, `ComfyUI-MultiGPU`, `WhatDreamsCost-ComfyUI`, and `ComfyUI-KJNodes`; owned Slopperly Comfy has now been live-tested with `comfyui_gguf`, `video_helper_suite`, `mmaudio`, `audio_separation`, `foundation_1`, `chatterbox`, and `florence2` for the certified blocks. Missing future node packs must be installed into `.slopperly/runtimes/ComfyUI/custom_nodes`, not relied on from the user Comfy tree.
- Owned Slopperly Comfy was live-tested on `127.0.0.1:8190` for the Wan2.2 TI2V-5B direct local default with API nodes disabled, CUDA 13 PyTorch, dynamic VRAM, `ComfyUI-GGUF`, `VideoHelperSuite`, UMT5 FP8, Wan VAE, and the Wan TI2V Q5 GGUF model from the owned model cache.
- Florence-2 Large files are now installed in the owned Comfy model cache under `.slopperly/runtimes/ComfyUI/models/LLM/Florence-2-large/`, including `model.safetensors` (`1.5G`), `config.json`, local modeling/processing files, tokenizer files, and processor files.
- Owned Slopperly Comfy was live-tested on `127.0.0.1:8190` for Florence2 caption/OCR with `DownloadAndLoadFlorence2Model`, `Florence2Run`, and `PreviewAny` available in `/object_info`. `Florence2Plugin.generate()` produced a real caption text artifact plus IDEOGRAM4 JSON from `tests/fixtures/florence2_caption.png`; the fixture caption matched red/green/blue/text/local/test concepts, and the JSON validated required keys plus text/OCR evidence.
- Stable Audio 3 Medium Base files are now installed in the owned Comfy model cache: `models/checkpoints/stable_audio_3_medium_base.safetensors` and `models/text_encoders/t5gemma_b_b_ul2.safetensors`.
- Owned Slopperly Comfy was restarted on `127.0.0.1:8190` after the Stable Audio 3 files landed, then live-tested through `StableAudio3Plugin.generate()` with StableAudio3, SAT5Gemma, and SA3AudioVAE loads from the owned cache and a real 2.043356s FLAC output.
- ACE-Step 1.5 XL Turbo files are now installed in the owned Comfy model cache: `models/diffusion_models/acestep_v1.5_xl_turbo_bf16.safetensors`, `models/vae/ace_1.5_vae.safetensors`, `models/text_encoders/qwen_0.6b_ace15.safetensors`, and `models/text_encoders/qwen_4b_ace15.safetensors`.
- Owned Slopperly Comfy was restarted on `127.0.0.1:8190` after the ACE-Step files landed, then live-tested through `AceStepPlugin.generate()` with ACE text encoder/diffusion/VAE loads from the owned cache and a real 2.000s FLAC output.
- Foundation-1 files are now installed in the owned Comfy model cache: `models/stable_audio/Foundation-1/Foundation_1.safetensors` and `models/stable_audio/Foundation-1/model_config.json`; the pinned Foundation node pack dependencies and private `k-diffusion==0.1.1` target are installed in `.slopperly/runtimes/comfy-venv`.
- Owned Slopperly Comfy was restarted on `127.0.0.1:8190` after the Foundation-1 files and node dependencies landed, then live-tested through `FoundationMusicPlugin.generate()` with Foundation-1 loading from the owned cache, local k-diffusion sampling, and a real 9.984580s WAV output converted from Comfy's FLAC save.
- MMAudio files are now installed in the owned Comfy model cache: `models/mmaudio/mmaudio_large_44k_v2_fp16.safetensors`, `models/mmaudio/mmaudio_vae_44k_fp16.safetensors`, `models/mmaudio/mmaudio_synchformer_fp16.safetensors`, `models/mmaudio/apple_DFN5B-CLIP-ViT-H-14-384_fp16.safetensors`, and the NVIDIA BigVGAN v2 44 kHz snapshot under `models/mmaudio/nvidia/bigvgan_v2_44khz_128band_512x/`.
- Owned Slopperly Comfy was restarted on `127.0.0.1:8190` after the MMAudio files landed, then live-tested through `MMAudioPlugin.generate()` with VideoHelperSuite MP4 upload through Comfy's real `/upload/image` endpoint, MMAudio/BigVGAN loading from the owned cache, and a real 1.509297s WAV output converted from Comfy's FLAC save.
- Stem Splitter's Hybrid Demucs checkpoint is now installed in the owned Comfy model cache at `models/torchaudio/hdemucs_high_trained.pt` and mirrored to Torchaudio's runtime cache at `/home/user/.cache/torch/hub/torchaudio/models/hdemucs_high_trained.pt`; both files are `320M`.
- Owned Slopperly Comfy was live-tested through `StemSplitterPlugin.generate()` with `AudioSeparation` loading the mirrored local Torchaudio checkpoint and producing four 1.000000s FLAC stems: bass, drums, other, and vocals.
- Chatterbox standard TTS/VC files are now installed in the owned Comfy model cache under `models/chatterbox/chatterbox/` and `models/chatterbox/chatterbox_vc/`, including `ve.safetensors`, `t3_cfg.safetensors`, `s3gen.safetensors`, `s3gen.pt`, `tokenizer.json`, and `conds.pt`; both folders came from the `ResembleAI/chatterbox` local artifact source.
- Owned Slopperly Comfy was live-tested through `ChatterboxPlugin.generate()` with `ComfyUI_Fill-ChatterBox` on CUDA. Comfy logged cached local model use for TTS and VC, and the plugin produced validated WAV artifacts for plain TTS, reference TTS, and the current one-audio VC compatibility mode.
- Chatterbox Turbo files are now installed in the owned Comfy model cache under `models/chatterbox/chatterbox_turbo/`, including `ve.safetensors`, `t3_turbo_v1.safetensors`, `s3gen_meanflow.safetensors`, tokenizer files, and `conds.pt` from the `ResembleAI/chatterbox-turbo` local artifact source.
- Owned Slopperly Comfy was live-tested through `ChatterboxTurboPlugin.generate()` with `FL_ChatterboxTurboTTS` on CUDA. Comfy logged cached local Turbo model use and produced validated WAV artifacts for prompt-only Turbo TTS and reference-audio Turbo TTS.
- Chatterbox Multilingual files are now installed in the owned Comfy model cache under `models/chatterbox/chatterbox_multilingual/`, including `ve.pt` (`5698626` bytes), `t3_mtl23ls_v2.safetensors` (`2143989752` bytes), `s3gen.pt` (`1057165844` bytes), `grapheme_mtl_merged_expanded_v1.json`, `conds.pt`, and `Cangjie5_TC.json`; these were hardlinked from the already-installed `ResembleAI/chatterbox` local artifact snapshot to avoid redownloading duplicate files.
- Owned Slopperly Comfy was live-tested through `ChatterboxMultilingualPlugin.generate()` with `FL_ChatterboxMultilingualTTS` on CUDA. Comfy logged cached local multilingual file use and produced validated WAV artifacts for French prompt-only multilingual TTS and Spanish reference-audio multilingual TTS.
- `.slopperly/vllm-omni-venv` is now installed with matching `vllm-omni==0.22.0` and `vllm==0.22.0`; the installer applies Slopperly patches to the local OmniVoice pipeline so request `extra_params` can drive the existing steps and guidance UI controls (`num_step` and `guidance_scale`), and to MOSS-TTS-Nano serving so request `max_new_tokens`, seed, and text/audio sampling controls are forwarded into per-request runtime information instead of being dropped.
- The local OmniVoice snapshot is now installed under `.slopperly/runtimes/vllm-omni/models/vllm_omni/k2-fsa/OmniVoice` (`3.1G`), including `config.json`, `model.safetensors`, tokenizer files, and the nested `audio_tokenizer/model.safetensors`.
- vLLM-Omni was live-tested on `127.0.0.1:8091` through `OmniVoicePlugin.generate()` with the local OmniVoice model loaded on CUDA. Prompt-only TTS and voice-clone TTS produced validated WAV artifacts; the client inlines local reference audio as `data:` URIs because the pure diffusion vLLM-Omni speech route rejected `file://` references despite the local-media server flag.
- The local MOSS-TTS-Nano snapshot is now installed under `.slopperly/runtimes/vllm-omni/models/vllm_omni/OpenMOSS-Team/MOSS-TTS-Nano` (`227M`), including `config.json`, `pytorch_model.bin`, tokenizer files, and local remote-code files. The auxiliary MOSS audio tokenizer snapshot is installed under `.slopperly/runtimes/vllm-omni/models/vllm_omni/OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano` (`85M`), including `config.json`, `model-00001-of-00001.safetensors` (`87922568` bytes), and local tokenizer/modeling code; the local MOSS config points to this local tokenizer path.
- vLLM-Omni was live-tested on `127.0.0.1:8091` through `MossTTSPlugin.generate()` with the local MOSS-TTS-Nano model and local MOSS audio tokenizer loaded on CUDA. Voice-clone TTS produced a validated WAV artifact; the plugin resolves the actual single served model ID from `/v1/models` when the local server advertises its snapshot path instead of the Hugging Face repo ID.
- `.slopperly/vllm-venv` is now installed with `vllm==0.23.0`, `torch==2.11.0`, CUDA 13 dependencies, `av==17.1.0`, and the `vllm[audio]` install target; the installer manifest is `.slopperly/vllm-install-manifest.json`.
- The local Whisper large-v3-turbo snapshot for STT is now installed under `.slopperly/runtimes/vllm/models/vllm/openai/whisper-large-v3-turbo` (`1.6G`), including `config.json`, `generation_config.json`, `preprocessor_config.json`, tokenizer files, and `model.safetensors` (`1617824864` bytes).
- vLLM was live-tested on `127.0.0.1:8090` through `FasterWhisperTranscribePlugin.generate()` with local `openai/whisper-large-v3-turbo` served from the Slopperly snapshot. The certified launch profile uses `served_model_name=openai/whisper-large-v3-turbo`, `max_num_batched_tokens=2048`, `gpu_memory_utilization=0.35`, `max_num_seqs=1`, eager mode, and local media access under `/home/user/Documents/Slopperly`. vLLM logs showed `WhisperForConditionalGeneration`, supported task `transcription`, max model length 448, 1.51 GiB checkpoint size, 1.51 GiB GPU model memory, 2048-token encoder cache budget, and 35,716 GPU KV-cache tokens; runtime GPU use after load was 6252 MiB of 16376 MiB.
- The STT known-speech fixture is committed at `tests/fixtures/vllm_stt_hello_local_world.wav`, WAV PCM s16le mono 16 kHz, 2.760000s, RMS 4883.239675826595, generated locally from ffmpeg `flite` text `Hello local world. This is a whisper test.` A direct local vLLM transcription probe returned `Hello, local world, this is a whisper test.` before plugin-path certification.
- The local Qwen2.5-VL snapshot for Marlin video captions is now installed under `.slopperly/runtimes/vllm/models/vllm/Qwen/Qwen2.5-VL-7B-Instruct` (`16G`), including `config.json`, `chat_template.json`, `preprocessor_config.json`, tokenizer files, `model.safetensors.index.json`, and five safetensors shards: `3900233256`, `3864726320`, `3864726424`, `3864733680`, and `1089994880` bytes.
- vLLM was live-tested on `127.0.0.1:8090` through `MarlinVideoCaptionsPlugin.generate()` with local `Qwen/Qwen2.5-VL-7B-Instruct` served from the Slopperly snapshot. The certified launch profile uses `max_model_len=16384`, `gpu_memory_utilization=0.82`, `cpu_offload_gb=6`, `max_num_seqs=1`, two sampled video frames, local `file://` video access under `/home/user/Documents/Slopperly`, and no multimodal processor cache. vLLM logs showed the 15.45 GiB checkpoint loaded with 9.55 GiB GPU model memory and 6.08 GiB CPU-offloaded parameters, then accepted real `/v1/chat/completions` calls for caption and find modes.
- No remaining production blocker exists for the certified `vllm_whisper_large_v3_turbo_stt` profile; any future STT model profile still needs its own local server/model artifact certification before exposure.
- Remaining future vLLM-Omni speech profiles require one local speech model per server instance and their own real artifact tests before exposure.
- `.slopperly/runtimes/llama.cpp` is now installed from release `b9803` using the Ubuntu x64 CUDA 13 artifact `llama-b9803-bin-ubuntu-cuda13-x64.tar.gz`; the owned runtime size is `249M`, the binary `.slopperly/runtimes/llama.cpp/llama-b9803/llama-server` passed its launch check, and `.slopperly/runtimes/llamacpp-install-manifest.json` records the exact release asset URL.
- The local Qwen2.5 7B Instruct Q5 GGUF prompt model is now installed at `.slopperly/runtimes/models/llamacpp/Qwen2.5-7B-Instruct-Q5_K_M.gguf` (`5.1G`) from `bartowski/Qwen2.5-7B-Instruct-GGUF`.
- llama.cpp was live-tested on `127.0.0.1:8092` through `MoviiGenRewriterPlugin.generate()` with the local Qwen2.5 Q5 GGUF served from the Slopperly cache. The certified launch profile requests `--ctx-size 60000`, `--n-predict 30000`, `--n-gpu-layers 999`, `--flash-attn on`, and one server slot; llama.cpp loaded on CUDA with runtime GPU use at 8926 MiB of 16376 MiB. The Qwen GGUF reports `n_ctx_train=32768`, so llama.cpp capped the served slot to `n_ctx=32768`; `LlamaCppClient` now records that fallback in plugin diagnostics instead of silently claiming the requested 60k context was honored.

Historical progress-block truth:

| Progress block | Code-derived truth | What is not done | Required proof |
|---|---|---|---|
| Indexed Comfy media schema | Schema helper scaffold exists for indexed fields and media uploads. | It proves no model parity by itself. | At least Qwen edit, OmniGen, and LTX staged workflows must pass real multi-reference artifact tests. |
| GPU certification harness | Test harness and certification JSON writer exist. | Harness does not mean a function passed; most GPU tests have not been run against real runtimes. | Each plugin test must run with real local runtime and validated artifact. |
| Comfy upload endpoint schema | Upload route declarations exist and reject absolute endpoints. Owned Comfy 0.26.0 accepts arbitrary media files for VideoHelperSuite through `/upload/image`; `/upload/video` is not a real core route. | It does not prove video/audio/image workflows run. | Real media-upload workflows must generate artifacts through the Comfy-supported endpoint for that runtime/node pack. |
| No-cloud audit | Audit script exists and cloud files are being removed. | Audit alone does not prove local replacement parity. | No-cloud audit plus local artifact certification per dropdown entry. |

Per-function parity table:

| Function / model | Current code truth | Not done / not on spec | Runtime, models, and UI mapping required before completion | Required real test |
|---|---|---|---|---|
| `audio/ace_step.py` ACE-Step | DONE ON SPEC for `smoke_16gb`: Comfy wrapper and `ace_step_15_music` workflow pack use owned Comfy with ACE-Step 1.5 XL Turbo files, and `AceStepPlugin.generate()` produced a validated local FLAC artifact. | No remaining production blocker for the certified profile; broader devices still need their own certification before exposure there. | Prompt, lyrics, BPM, key, time signature, duration, steps, guidance, and seed are patched into the owned Comfy workflow. | PASS: `.slopperly/gpu-artifacts/smoke_16gb/ace_step_15_music/24680_bright_indie_pop_loop_clean_g_ace_step_15.flac`, FLAC stereo 48 kHz, 2.000s, non-silent validation. |
| `audio/_stable_audio_3.py` Stable Audio 3 | DONE ON SPEC for `smoke_16gb`: Comfy wrapper and `stable_audio_3_medium_base` workflow pack use owned Comfy with Stable Audio 3 Medium Base files, and `StableAudio3Plugin.generate()` produced a validated local FLAC artifact. | No remaining production blocker for the certified profile; broader devices still need their own certification before exposure there. | Prompt, negative prompt, duration, steps, guidance, seed, sampler, scheduler, denoise, checkpoint, and text encoder are patched into the owned Comfy workflow. | PASS: `.slopperly/gpu-artifacts/smoke_16gb/stable_audio_3_medium_base/31415_warm_lo-fi_electric_piano_chords_soft_brushed_drums_rounded_bass_stable_audio_3.flac`, FLAC stereo 44.1 kHz, 2.043356s, non-silent validation. |
| `audio/foundation_music.py` Foundation-1 | DONE ON SPEC for `smoke_16gb`: Comfy wrapper and `foundation1_music_loop` workflow pack use owned Comfy with Foundation-1 files and pinned node dependencies, and `FoundationMusicPlugin.generate()` produced a validated local WAV loop artifact. | No remaining production blocker for the certified profile; broader devices still need their own certification before exposure there. | Prompt, negative prompt folded into tags, BPM, bar count, key, duration-to-loop selection, steps, seed, sampler, cfg, sigma controls, and per-run save prefix are patched into the owned Comfy workflow. | PASS: `.slopperly/gpu-artifacts/smoke_16gb/foundation1_music_loop/424242_warm_analog_bass_clipped_hous_foundation1.wav`, WAV stereo 44.1 kHz, 9.984580s for 100 BPM / 4 bars, non-silent validation. |
| `audio/mmaudio.py` MMAudio | DONE ON SPEC for `smoke_16gb`: Comfy wrapper and `mmaudio_video_to_audio` workflow pack use owned Comfy with VideoHelperSuite, ComfyUI-MMAudio, MMAudio safetensors, and BigVGAN cache, and `MMAudioPlugin.generate()` produced a validated local WAV artifact. | No remaining production blocker for the certified profile; broader devices still need their own certification before exposure there. | Selected video strip upload, prompt, negative prompt, duration, steps, guidance/cfg, seed, mask-away-CLIP, force-offload, exact local model files, and per-run save prefix are patched into the owned Comfy workflow. | PASS: `.slopperly/gpu-artifacts/smoke_16gb/mmaudio_video_to_audio/2468_subtle_cloth_movement_quiet_room_tone_small_mechanical_hum_mmaudio.wav`, WAV mono 44.1 kHz, 1.509297s, non-silent validation from a generated 3s local MP4 source. |
| `audio/stem_split.py` Stem Splitter | DONE ON SPEC for the certified four-stem `smoke_16gb` profile: Comfy Demucs wrapper and `audio_stem_split_demucs` workflow pack use owned Comfy with `audio_separation`, local Hybrid Demucs checkpoint cache, and `StemSplitterPlugin.generate()` produced four validated local FLAC stems. | No remaining production blocker for the certified four-stem profile; the old six-stem `htdemucs_6s` option remains blocked with a concrete diagnostic until a pinned six-stem Comfy workflow passes artifact certification. | Selected audio/video strip audio path, chunk fade shape, chunk length, chunk overlap, selected-stem checkboxes, and the existing `MULTI_STEM` return shape are preserved; the checkpoint is mirrored into Torchaudio's local hub cache before generation. | PASS: `.slopperly/certification/smoke_16gb/audio_stem_split_demucs.json`, manifest plus bass/drums/other/vocals FLAC files, each stereo 44.1 kHz, 1.000000s, duration-matched to `tests/fixtures/stem_split_source.wav`. |
| `audio/chatterbox.py` Chatterbox | DONE ON SPEC for `smoke_16gb`: Comfy wrapper/workflows use owned Comfy with pinned `ComfyUI_Fill-ChatterBox`, local `ResembleAI/chatterbox` TTS/VC files, and `ChatterboxPlugin.generate()` produced validated local WAV artifacts for plain TTS, reference TTS, and the current one-audio VC compatibility path. | No remaining production blocker for the certified prompt/ref/legacy-single-audio VC profile; true cross-speaker VC remains blocked until the existing UI gains a second target voice selector and that two-audio workflow passes artifact certification. | Prompt, audio ref upload, voice-conversion mode, seed, exaggeration, cfg/pace, temperature, use-CPU, keep-loaded, per-run save prefix, and WAV conversion are mapped; audio duration/speed/remove-silence remain explicit unmapped node limitations. | PASS: `.slopperly/certification/smoke_16gb/chatterbox_tts_vc_comfy.json`, manifest plus three WAV files: plain TTS 3.480s, reference TTS 3.200s, and VC 3.480s, all mono 24 kHz and non-silent. |
| `audio/chatterbox_turbo.py` Chatterbox Turbo | DONE ON SPEC for `smoke_16gb`: Comfy wrapper/workflows use owned Comfy with pinned `ComfyUI_Fill-ChatterBox`, local `ResembleAI/chatterbox-turbo` files, and `ChatterboxTurboPlugin.generate()` produced validated local WAV artifacts for prompt-only and reference-audio Turbo TTS. | No remaining production blocker for the certified prompt/ref profile; Turbo is not two-audio speech-to-speech VC, which remains covered by standard Chatterbox's documented compatibility path until a second target selector exists. | Prompt, optional audio ref upload, seed, temperature, top_k, top_p, repetition_penalty, use-CPU, keep-loaded, per-run save prefix, and WAV conversion are mapped; duration, speed, silence trimming, exaggeration, and pace remain explicit unmapped node limitations. | PASS: `.slopperly/certification/smoke_16gb/chatterbox_turbo_tts_comfy.json`, manifest plus prompt-only WAV 11.280s and reference-audio WAV 4.160s, both mono 24 kHz and non-silent. |
| `audio/chatterbox_multilingual.py` Chatterbox Multilingual | DONE ON SPEC for `smoke_16gb`: Comfy wrapper/workflows use owned Comfy with pinned `ComfyUI_Fill-ChatterBox`, local `ResembleAI/chatterbox` multilingual files, and `ChatterboxMultilingualPlugin.generate()` produced validated local WAV artifacts for multilingual prompt-only TTS and reference-audio TTS. | No remaining production blocker for the certified prompt/ref profile; true two-audio speech-to-speech VC remains covered by standard Chatterbox's documented compatibility path until a second target selector exists and a two-audio multilingual VC graph passes certification. | Prompt, language, optional audio ref upload, seed, exaggeration, cfg/pace, temperature, repetition_penalty, min_p, top_p, use-CPU, keep-loaded, per-run save prefix, and WAV conversion are mapped; audio duration/speed/remove-silence remain explicit unmapped node limitations. | PASS: `.slopperly/certification/smoke_16gb/chatterbox_multilingual_tts_comfy.json`, manifest plus French prompt-only WAV 7.270s and Spanish reference-audio WAV 9.030s, both mono 24 kHz and non-silent. |
| `audio/omnivoice.py` OmniVoice | DONE ON SPEC for `smoke_16gb`: vLLM-Omni runtime/client/supervisor use a local `vllm-omni==0.22.0` plus `vllm==0.22.0` venv, the local `k2-fsa/OmniVoice` snapshot is cached under the Slopperly runtime tree, and `OmniVoicePlugin.generate()` produced validated local WAV artifacts for prompt-only TTS and voice-clone TTS. | No remaining production blocker for the certified prompt/clone profile; each other vLLM-Omni speech model still needs its own local server/model and artifact certification. | Prompt, ref audio, ref text, language, instructions, speed, seed, steps, and guidance are mapped to the localhost speech request. Local reference audio is encoded as a `data:` URI for clone mode; the installer patches the local OmniVoice pipeline to honor steps/guidance from `extra_params`. | PASS: `.slopperly/certification/smoke_16gb/omnivoice_vllm_omni.json`, manifest plus prompt-only WAV 2.960s and clone WAV 4.920s, both mono 24 kHz and non-silent through local vLLM-Omni. |
| `audio/moss_tts.py` MOSS-TTS | DONE ON SPEC for `smoke_16gb`: vLLM-Omni runtime/client use the local `OpenMOSS-Team/MOSS-TTS-Nano` snapshot plus the local `OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano` auxiliary snapshot, and `MossTTSPlugin.generate()` produced a validated local WAV voice-clone artifact through the local server. | No remaining production blocker for the certified MOSS-TTS-Nano voice-clone profile; other vLLM-Omni speech profiles still need separate local servers/models and certification. | Prompt, selected/shared audio ref or MOSS custom ref path, language field, seed, duration tokens, max-new-token cap, temperature, top-p, and top-k are mapped into the local speech request; local reference audio is encoded as a `data:` URI and the local vLLM-Omni serving patch forwards MOSS sampling controls into runtime information. | PASS: `.slopperly/certification/smoke_16gb/moss_tts_nano_vllm_omni.json`, manifest plus `moss_tts_nano.wav`, WAV mono 48 kHz, 4.800s, RMS 4441.058497322528, non-silent through local vLLM-Omni. |
| `text/faster_whisper_transcribe.py` STT | DONE ON SPEC for `smoke_16gb`: vLLM STT client/plugin path uses the dedicated local vLLM runtime with local `openai/whisper-large-v3-turbo`, and `FasterWhisperTranscribePlugin.generate()` produced validated VSE text-strip output from a known speech WAV fixture. | No remaining production blocker for the certified Whisper large-v3-turbo STT profile; any future STT model profile still needs separate local runtime/model and artifact certification. | Selected audio path, language selection, served-model resolution, multipart `/v1/audio/transcriptions`, subtitle chunking, free-channel insertion, and existing VSE text-strip output are mapped through the local vLLM transcription client. | PASS: `.slopperly/certification/smoke_16gb/vllm_whisper_large_v3_turbo_stt.json`, artifact `.slopperly/gpu-artifacts/smoke_16gb/vllm_whisper_large_v3_turbo_stt/transcript.txt`, expected words `hello`, `local`, `world`, `whisper`, and `test` from `tests/fixtures/vllm_stt_hello_local_world.wav`. |
| `text/marlin_video_captions.py` video captions | DONE ON SPEC for `smoke_16gb`: vLLM VLM client/plugin path uses the dedicated local vLLM runtime with local `Qwen/Qwen2.5-VL-7B-Instruct`, and `MarlinVideoCaptionsPlugin.generate()` produced validated caption strips plus a Find-mode timeline marker from a real MP4 fixture. | No remaining production blocker for the certified Marlin video-caption/find-marker profile; any future vLLM profile still needs its own server/model and artifact certification. | Selected video path, caption mode, Find query, marker insertion, speed token budget, local served-model resolution, local `file://` video URL, and existing VSE text-strip output are mapped through the local vLLM chat-completions client. | PASS: `.slopperly/certification/smoke_16gb/vllm_video_caption_vlm.json`, artifact `.slopperly/gpu-artifacts/smoke_16gb/vllm_video_caption_vlm/video_captions.txt`, 3 caption strips total and 1 `MARLIN:` marker from `tests/fixtures/video_caption_smoke.mp4`. |
| `text/moviigen_rewriter.py` prompt rewriter | DONE ON SPEC for `smoke_16gb`: llama.cpp client/plugin path uses the owned `b9803` Ubuntu x64 CUDA runtime with local `Qwen2.5-7B-Instruct-Q5_K_M.gguf`, and `MoviiGenRewriterPlugin.generate()` produced a validated local prompt rewrite artifact. | No remaining production blocker for the certified Qwen2.5 Q5 prompt-rewriter profile; future prompt/chat profiles still need their own local GGUF and artifact certification. | Prompt field, system rewrite instruction, temperature, local `/v1/chat/completions`, `n_ctx=60000`, `n_predict/max_tokens=30000`, GPU offload, output text return, and explicit context fallback diagnostics are mapped through the local llama.cpp client. | PASS: `.slopperly/certification/smoke_16gb/llamacpp_prompt_rewriter.json`, artifact `.slopperly/gpu-artifacts/smoke_16gb/llamacpp_prompt_rewriter/prompt_rewrite.txt`, preserving expected concepts `train`, `station`, and `robot` while recording served `n_ctx=32768` after the requested 60k context. |
| `text/florence2.py` Florence2 | DONE ON SPEC for `smoke_16gb`: Comfy wrapper and `florence2_caption_ocr` workflow pack use owned Comfy with pinned Florence2 nodes, local Florence-2 Large files, and `Florence2Plugin.generate()` produced validated local caption text plus IDEOGRAM4 JSON artifacts. | No remaining production blocker for the certified caption/OCR/IDEOGRAM4 profile; broader Florence task modes or future model profiles still need their own artifact certification if exposed separately. | Selected image input, Florence task mode, local model loader, Comfy text/JSON history collection through `PreviewAny`, bbox/quad normalization for real Florence JSON shapes, and existing text return behavior are mapped through the owned Comfy workflow. | PASS: `.slopperly/certification/smoke_16gb/florence2_caption_ocr.json`, manifest plus `caption.txt` and `ideogram4.json` under `.slopperly/gpu-artifacts/smoke_16gb/florence2_caption_ocr/`; caption matched red/green/blue/text/local/test concepts and IDEOGRAM4 JSON validated required keys plus text/OCR evidence. |
| `image/_krea2_base.py` Krea 2 Base | Comfy wrapper/workflow pack exists. | Scaffold only; not GGUF-certified; no real image artifact. | Owned Comfy Krea files; map prompt, negative, resolution, frames, steps, guidance, seed, LoRA if UI exposes it. | Real PNG at requested size/aspect. |
| `image/krea2_turbo.py` Krea 2 Turbo | Comfy wrapper/workflow pack exists. | Scaffold only; default-step parity not proven. | Owned Comfy Krea Turbo files; map prompt, resolution, frames, steps, guidance, seed, any negative/LoRA UI gaps. | Real PNG with Turbo defaults validated. |
| `image/anima.py` Anima | Comfy wrapper and T2I/I2I packs exist. | Scaffold only; no real T2I/I2I artifact. | Owned Comfy Anima files; map prompt, negative, image strip, resolution, frames, steps, guidance, strength, seed, LoRA. | Real PNG T2I and I2I tests. |
| `image/birefnet.py` BiRefNet | Comfy RMBG wrapper exists. | Scaffold only; no real alpha PNG. | Owned Comfy RMBG/BiRefNet nodes/model; map selected image strip and preserve dimensions. | Real PNG with alpha channel. |
| `image/ernie.py` ERNIE Image | Comfy wrapper/workflow exists. | Scaffold only; no real image artifact. | Owned Comfy ERNIE files; map prompt, negative, resolution, frames, steps, guidance, seed. | Real PNG generation. |
| `image/ernie_turbo.py` ERNIE Turbo | Comfy wrapper/workflow exists. | Scaffold only; 8-step default not proven. | Owned Comfy ERNIE Turbo files; map prompt, negative, resolution, frames, steps default 8, guidance, seed. | Real PNG Turbo test. |
| `image/flux2_dev.py` FLUX.2 Dev | Comfy GGUF-quality workflow packs exist. | Scaffold only; FLUX.2 Dev Q5 is not 16GB default and no real artifact. | Owned Comfy GGUF + FLUX.2 nodes; install/copy `flux2-dev-Q5_K_M.gguf`, Mistral FLUX.2 text encoder, VAE; map prompt, multi-image refs, resolution, frames, steps, guidance, seed, strength/LoRA gaps. | Real T2I and multi-ref PNG on certified profile only. |
| `image/flux2_klein_4b.py` FLUX.2 Klein 4B | Comfy wrapper/workflow packs exist. | Scaffold only; not GGUF; no real RTX artifact; dropdown not certifiable. | Owned Comfy FLUX.2 Klein 4B files/text encoder/VAE; map prompt, image strip/edit mode, resolution, frames, steps, guidance, strength, seed, LoRA. | Real T2I and image-edit PNG tests. |
| `image/flux2_klein_9b.py` FLUX.2 Klein 9B | Comfy wrapper/workflow packs exist. | Scaffold only; not GGUF; device-profile certification missing. | Owned Comfy 9B model/text encoder/VAE; map same controls as 4B. | Real T2I/edit PNG on certified hardware profile. |
| `image/flux2_klein_9b_schematic.py` schematic LoRA | Comfy workflow pack exists. | Scaffold only; LoRA stack not proven installed or wired by UI. | Owned Comfy 9B base plus six schematic LoRA files; map prompt, image strip, frames, steps, guidance, seed, LoRA selection. | Real schematic-style PNG test. |
| `image/flux_canny.py` FLUX Canny | Comfy control workflow exists. | Scaffold only; control strength/LoRA mapping not proven. | Owned Comfy controlnet aux/FLUX files; map control image strip, prompt, resolution, frames, steps, guidance, strength, seed, LoRA. | Real edge-preservation PNG. |
| `image/flux_depth.py` FLUX Depth | Comfy control workflow exists. | Scaffold only; depth preprocessor/model not proven. | Owned Comfy DepthAnything/FLUX files; map control image, prompt, resolution, frames, steps, guidance, strength, seed, LoRA. | Real layout-preservation PNG. |
| `image/flux_kontext.py` Kontext | Comfy edit workflow exists. | Scaffold only; inpaint/mask and strength parity not proven. | Owned Comfy Kontext files; map prompt, image strip, resolution, frames, steps, guidance, strength, seed, LoRA, mask if exposed. | Real semantic edit PNG. |
| `image/flux_redux.py` Redux | Comfy restyle workflow exists. | Scaffold only; no real style transfer artifact. | Owned Comfy Redux/style/vision files; map image strip, resolution, frames, steps, guidance, seed. | Real Redux PNG. |
| `image/kontext_relight.py` Relight | Comfy relight workflow exists. | Scaffold only; illumination controls not proven in artifact. | Owned Comfy Kontext + relight LoRA files; map prompt, image strip, resolution, frames, steps, guidance, illumination style, direction, seed. | Real relight PNG with direction check. |
| `image/ideogram4.py` Ideogram 4 | Comfy wrapper/workflow exists. | Scaffold only; prompt upsampling/text rendering parity not proven. | Owned Comfy Ideogram files; map prompt/structured prompt, resolution, frames, steps, guidance, seed, LoRA if exposed. | Real PNG including text-rendering smoke. |
| `image/lumina2.py` Lumina 2 | Comfy wrapper/workflow exists. | Scaffold only; no real artifact. | Owned Comfy Lumina checkpoint/text/VAE files; map prompt, negative, resolution, frames, steps, guidance, seed. | Real PNG. |
| `image/maxine_vsr.py` local image VSR | Comfy VSR wrapper exists and display should be local, not Maxine. | Scaffold only; no real upscale artifact. | Owned Comfy upscale nodes and RealESRGAN model; map selected image, target resolution, frames/seed if UI exposes. | Real input image to requested resolution PNG. |
| `image/nucleus_moe.py` Nucleus | Slopperly-owned Comfy diffusers node scaffold exists. | Scaffold only; not native Comfy; not a Qwen/FLUX substitute; no real artifact. | Owned Comfy local `slopperly_nodes` plus Nucleus diffusers snapshot/FP8 patch; map prompt, negative, resolution, frames, steps, guidance, seed. | Real PNG through Slopperly node. |
| `image/omnigen.py` OmniGen | Comfy multi-image workflow exists. | Scaffold only; multi-image prompt parity not proven. | Owned Comfy OmniGen nodes/model; map up to three image refs, per-image prompts/placeholders, resolution, frames, steps, guidance, seed. | Real triple-reference PNG. |
| `image/qwen_image.py` Qwen Image 2512 | Comfy GGUF/native packs exist. | Scaffold only; no real Q5/native artifact; dynamic LoRA gaps remain. | Owned Comfy GGUF/Qwen files; map prompt, optional image strip, resolution, frames, steps, strength, seed, LoRA. | Real T2I and I2I PNG, including aspect presets. |
| `image/qwen_image_edit.py` Qwen Image Edit 2511 | Comfy GGUF multi-ref pack exists. | Scaffold only; no one-ref/three-ref real artifacts. | Owned Comfy Qwen edit files; map prompt, negative, 1-3 images, resolution, frames, steps, seed, LoRA. | Real one-ref and three-ref edit PNGs. |
| `image/zimage.py` Z-Image | Comfy T2I/I2I packs exist. | Scaffold only; negative prompt gap exists for Turbo; no artifact. | Owned Comfy Z-Image files; map prompt, negative where supported, image strip, resolution, frames, steps, guidance, strength, seed. | Real T2I and I2I PNG for base and Turbo. |
| `image/google_nano_banana.py` Google Nano Banana | Production plugin file deleted. | Cloud removal is correct, but no replacement parity is done. | Do not alias old cloud ID. Qwen Image Edit must be a direct local entry with its own certified UI mapping. | Registry rejects cloud ID; Qwen edit real artifacts pass. |
| `video/google_veo.py` Google Veo | Production plugin file deleted. | Cloud removal is correct, but local video parity is not done. | Do not alias old cloud ID. Wan/LTX entries must be direct certified local entries. | Registry rejects cloud ID; direct local video tests pass. |
| `video/minimax.py` MiniMax txt/img/subject | Production plugin file deleted. | Cloud removal is correct, but saved-project alias path is not acceptable and not parity. | Do not alias old cloud IDs. Direct Wan/LTX/reference-video workflows must be certified independently. | Registry rejects cloud IDs; direct T2V/I2V/subject tests pass. |
| `video/wan_ti2v_5b.py` Wan TI2V-5B | New direct local Comfy default is certified for the `smoke_16gb` dropdown profile with separate T2V and I2V PASS records from `WanTI2V5BPlugin.generate()` against owned ComfyUI on `127.0.0.1:8190`. | Not original Palladium parity; it does not complete `video/wan_t2v.py`, `video/wan_i2v.py`, LTX, or old cloud replacement parity beyond this direct local entry. | Owned Comfy with GGUF, UMT5 FP8, Wan VAE, VideoHelperSuite; prompt, negative, optional image strip, 720P-family resolution mapping, frames, steps, guidance, seed, and fps=24 are mapped. | PASS: direct T2V and direct I2V MP4, both 1280x704, 24fps, 49 frames, 2.041667s, validated by `ffprobe` through plugin-path GPU tests. |
| `video/wan_t2v.py` Wan A14B T2V | Current production file still direct Torch/Diffusers/Transformers. | Not migrated; not GGUF workflow; not spec. | Copy/symlink high/low-noise T2V Q5 files if available or download; owned Comfy two-stage workflow; map prompt, negative, resolution, frames, seed, steps/guidance/LoRA. | Real 16fps native to 24fps final MP4. |
| `video/wan_i2v.py` Wan A14B I2V | Current production file still direct Torch/Diffusers/Transformers. | Not migrated; I2V high/low Q5 files are now copied into the owned Comfy cache but no Comfy workflow/plugin-path artifact exists. | Use owned Comfy two-stage workflow with the copied high/low-noise Q5 files; map image strip, prompt, negative, resolution, frames, seed, LoRA. | Real I2V 16fps native to 24fps final MP4. |
| `video/ltx2.py` LTX2 19B | Current file still direct Diffusers. | Not migrated; no Comfy gateway; no owned cache import; no real Slopperly artifact. | Reuse `/home/user/Documents/Comfy` LTX 2.3 workflows/models before download; port to owned Comfy workflow pack; map prompt, negative, image/video strip, resolution, frames, seed, LoRA. | Real MP4 through `LTX2Plugin.generate()`. |
| `video/ltx23_extend.py` LTX 2.3 Extend | Current file still direct Torch/Diffusers/Transformers. | Not migrated; not using existing working Comfy workflow. | Port existing `/home/user/Documents/Comfy/workflows` extend-capable graph or build from it; copy LTX cache; map selected video, prompt, negative, extension duration/frames, seed. | Real extended MP4 with duration greater than source. |
| `video/ltx23_lipsync.py` LTX 2.3 Lipsync | Current file still direct Torch/Diffusers/Transformers. | Not migrated; audio-duration/frame mapping not proven. | Owned Comfy LTX lipsync/dialogue workflow; copy LTX audio/video VAE, LoRAs; map audio ref, source image/video, prompt, negative, target fps/frame count. | Real MP4 duration matching audio within tolerance. |
| `video/ltx23_multi.py` LTX 2.3 Multi | Current file still direct Torch/Diffusers/Transformers. | Not migrated; middle anchor UI not proven. | Port existing LTX multi-anchor workflow; copy LTX cache; map image/video refs, middle anchors, prompt, negative, seed, LoRA. | Real staged MP4 with anchor timing smoke. |
| `video/ltx23_multi_ic_lora.py` LTX IC-LoRA | Current file still direct Torch/Diffusers/Transformers. | Not migrated; IC-LoRA files not in owned cache. | Copy LTX IC-LoRA files from user Comfy; owned Comfy workflow; map image refs, prompt, seed, LoRA choice/strength. | Real reference-consistency MP4. |
| `video/skyreels.py` SkyReels | Current file still direct Diffusers/Torch. | Not migrated to Comfy; no real artifact. | Owned Comfy SkyReels/Hunyuan nodes/models; map prompt, negative, image/video strip, resolution, frames, steps, guidance, seed. | Real T2V/I2V MP4. |
| `video/maxine_vsr_video.py` local video VSR | Comfy wrapper exists and display should be local, not Maxine. | Scaffold only; no real upscale MP4. | Owned Comfy VideoHelperSuite/upscale model; map selected video strip, target resolution, seed; preserve fps/duration/audio. | Real MP4 target size with fps/duration/audio validation. |
| `video/cogvideox.py` CogVideoX | Present in original baseline but absent from current production plugins. | Not done; not hidden with explicit certified block in this report before now. | Either restore as local Comfy workflow or keep removed/hidden with documented reason. | If restored, real MP4 through plugin. |
| `image/cosmos3_nano.py` Cosmos3 image | Present in original baseline but absent now. | Not done; no local workflow. | Restore local Comfy/vLLM workflow or hide with explicit block. | Real image artifact if restored. |
| `video/cosmos3_nano.py` Cosmos3 video | Present in original baseline but absent now. | Not done; no local workflow. | Restore local Comfy workflow or hide with explicit block. | Real video artifact if restored. |
| old FLUX2 Klein KV/old files | Present in original baseline variants, absent now. | Not done as original model parity. | Either explicitly supersede with certified direct Klein entries or restore exact local workflow. | Real artifacts for any exposed entry. |

The next implementation block must update this table in place after each function is fixed and tested. Do not create separate progress docs.


## 1. Current repository facts

The uploaded code still has the Pallaidium plugin architecture:

```text
models/base.py                       ModelPlugin, ModelInputs, InputSpec, UISection, ParamSpec
models_plugins/<type>/*.py           actual model plugins
models/remote_base.py                generic OpenAI-style remote plugin factory
remote_backends/comfyui_adapter.py   local Comfy bridge, currently user-supplied Comfy instance
remote_backends/fal_adapter.py       fal.ai cloud bridge
properties/preferences.py            model source + remote/backend/API-key preferences
utils/remote_backend.py              generic backend HTTP client
utils/helpers.py                     direct MiniMax video cloud helpers
```

The current dispatch seam is already correct and must be preserved:

```text
Blender UI/operator
  -> selected ModelPlugin
  -> ModelPlugin.generate(ModelInputs)
  -> runtime implementation
  -> artifact file
  -> existing VSE/output insertion logic
```

The migration must not bypass `ModelPlugin.generate()`. The tests must exercise that same path.

## 2. External/cloud code removal map

| File/path | Current behavior | Production Slopperly action |
|---|---|---|
| `remote_backends/fal_adapter.py` | Forwards to `https://queue.fal.run` for Seedance, Seed Audio, and cloud FLUX. | Remove from production discovery. Keep only in `/reference/palladium` or docs archive. |
| `remote_backends/fal_adapter.manifest.json` | Makes fal visible as a backend. | Remove from production manifests. |
| `models_plugins/image/google_nano_banana.py` | Uses Google Gemini/Nano Banana image API and `GEMINI_API_KEY`. | Remove from production. Do not register old cloud model IDs as production aliases. |
| `models_plugins/video/google_veo.py` | Uses Google Veo cloud video. | Remove from production. Do not register old cloud model IDs as production aliases. |
| `models_plugins/video/minimax.py` | MiniMax/Hailuo cloud video model family. | Remove from production. Do not register old cloud model IDs as production aliases. |
| `MiniMax_API.txt` | Local file for MiniMax API key. | Delete from production tree. |
| `utils/helpers.py` MiniMax functions | `invoke_video_generation`, `query_video_generation`, `fetch_video_result` call `api.minimaxi.chat`. | Delete or move to reference-only. Production grep must fail if these URLs remain reachable. |
| `properties/preferences.py` remote key fields | `gemini_api_key`, `remote_backend_key`, remote URL/key UI. | Replace with local runtime paths/ports/model-cache settings. No cloud keys. |
| `models/base.py` `InputSpec.API_KEY` | External provider API-key input. | Remove from production plugin inputs. Preserve only in reference code. |
| `models/remote_base.py` and `utils/remote_backend.py` | Generic remote backend client. | Either rename/rewrite as localhost-only runtime client or isolate in reference. Production client must reject non-localhost inference URLs. |

Production no-cloud grep must fail on these outside reference/docs/test allowlists:

```text
queue.fal.run
fal.ai
FAL_KEY
google.genai
GEMINI_API_KEY
MiniMax_API.txt
api.minimaxi.chat
OPENAI_API_KEY
ANTHROPIC_API_KEY
ELEVENLABS_API_KEY
REPLICATE_API_TOKEN
api.stability.ai
runway
vertex
bedrock
```

## 3. Runtime architecture

```mermaid
flowchart LR
    UI[Existing Blender add-on UI\nNo layout/function redesign] --> OPS[Existing operators/queue]
    OPS --> PLUGIN[Existing ModelPlugin.generate\nModelInputs unchanged]
    PLUGIN --> GATEWAY[Slopperly local runtime gateway]

    GATEWAY --> COMFY[Owned ComfyUI runtime\nAPI-format workflows]
    GATEWAY --> VLLM[vLLM local server\nSTT + VLM]
    GATEWAY --> OMNI[vLLM-Omni local server\nTTS + voice clone]
    GATEWAY --> LLAMA[llama.cpp local server\nchat + prompt rewrite]

    COMFY --> ART[PNG / MP4 / WAV artifacts]
    VLLM --> ART
    OMNI --> ART
    LLAMA --> TXT[Text result]
    ART --> RESULT[Existing result mapping\nVSE strips, text files, audio strips]
    TXT --> RESULT
```

```mermaid
sequenceDiagram
    participant UI as Blender UI/operator
    participant P as Current ModelPlugin
    participant G as SlopperlyRuntimeGateway
    participant C as Owned ComfyUI
    participant T as Test harness

    UI->>P: generate(ModelInputs)
    P->>G: run_workflow(plugin_id, inputs)
    G->>C: /object_info node availability check
    G->>C: /upload/image or runtime-supported media upload refs
    G->>C: POST /prompt workflow.api.json with patched params
    C-->>G: prompt_id
    loop poll
        G->>C: GET /history/{prompt_id}
    end
    G->>C: GET /view outputs
    G-->>P: local artifact path + metadata
    P-->>UI: existing result object
    T->>P: Same generate() call with smoke payload
```

```mermaid
flowchart TD
    A[Implement or update plugin wrapper] --> B[Run unit config/adapter test]
    B --> C[Start local runtime]
    C --> D[Call plugin generate with real parameters]
    D --> E[Collect artifact]
    E --> F{Validate artifact}
    F -->|image| I[PIL: readable, dimensions, alpha when needed]
    F -->|video| V[ffprobe: width, height, fps, duration, frame count]
    F -->|audio| W[ffprobe/soundfile: duration, sample rate, non-silent]
    F -->|text| X[expected text shape]
    I --> G[Mark plugin migrated]
    V --> G
    W --> G
    X --> G
    F -->|fail| H[Not shown in production dropdown]
```

## 4. Runtime responsibilities

| Runtime | Required use in Slopperly | Notes |
|---|---|---|
| ComfyUI owned runtime | Image generation, image editing, video generation, video editing, background removal, super-resolution, frame interpolation, music/audio diffusion, video-to-audio, stem splitting, Florence-style image captioning when implemented as Comfy workflow. | Use API-format workflows. Normal UI-save JSON is not enough. Store editable and API JSON side by side. |
| vLLM | Speech-to-text/transcription and video/image VLM captioning where the chosen local model is served through vLLM. | Use a dedicated vLLM venv. Use `vllm[audio]` for transcription. |
| vLLM-Omni | TTS, voice design, voice cloning, uploaded voice cache, batch speech. | Use dedicated vLLM-Omni server instances. Each server instance runs one model. |
| llama.cpp | Prompt enhancement, prompt rewriting, chat, planning, metadata, script generation. | Use requested Ubuntu x64 CUDA 13 release artifact. Defaults: 60k context, 30k max new tokens, with explicit diagnostics when a model/runtime cannot honor the request. |
| Blender | Existing sequencing, insertion, timeline, render/export logic. | Do not move UI logic into runtime adapters. |

Key upstream facts used by this spec:

- ComfyUI API submission uses API-format workflows; the editable UI workflow and API workflow are different artifacts.
- The requested llama.cpp release lists an Ubuntu x64 CUDA 13 artifact and says CUDA artifacts are built against CUDA 13.2 and do not bundle NVIDIA runtime/driver libraries.
- vLLM exposes OpenAI-compatible transcription APIs and requires audio extras for STT.
- vLLM-Omni exposes OpenAI-compatible speech APIs and lists Qwen3-TTS, Fish Speech S2 Pro, Voxtral TTS, CosyVoice3, OmniVoice, VoxCPM2, and MOSS-TTS-Nano support.

## 5. Required repository layout

```text
slopperly/
  runtime/
    gateway.py
    comfy/
      supervisor.py
      api_client.py
      workflow_runner.py
      install.py
      nodes.lock.yaml
    vllm/
      supervisor.py
      stt_client.py
      vlm_client.py
      install.py
    vllm_omni/
      supervisor.py
      tts_client.py
      voice_client.py
      install.py
    llamacpp/
      supervisor.py
      client.py
      install.py
  workflows/
    comfy/<workflow_id>/
      workflow.editable.json
      workflow.api.json
      params.schema.json
      models.yaml
      test_payload.json
      README.md
  config/
    runtimes.yaml
    models.yaml
    dropdown_profiles.yaml
  tests/
    unit/
    integration/
    gpu/
reference/
  palladium/
```

The original Palladium/Pallaidium reference code remains separate. Production Slopperly code must not import from `/reference`.

Progress and parity status lives in this `AGENTS.md` file only.

## 6. ComfyUI runtime requirements

Slopperly must install and launch its own ComfyUI runtime. It must not depend on the user’s existing Comfy install.

Required Comfy runtime behavior:

1. Install pinned ComfyUI commit or released version into the Slopperly runtime directory.
2. Install pinned custom node packs by git URL and commit SHA.
3. Download model artifacts from `slopperly/config/models.yaml` only when explicitly requested.
4. Validate required node classes by calling `/object_info` before a workflow is marked available.
5. Convert or export every workflow to API format.
6. Execute workflows through `/prompt`, `/history/{prompt_id}`, `/view`, `/upload/image`, and equivalent upload endpoints.
7. Return artifacts in the current add-on result shape.
8. Surface progress/phase through existing `ModelInputs.progress_fn` and `phase_fn`.
9. Reject any workflow that references a cloud Partner Node or external inference endpoint.

### Required Comfy custom node packs

| Pack | Source | Required node classes / use | Used by |
|---|---|---|---|
| ComfyUI core | pinned ComfyUI repo | `LoadImage`, `Load Diffusion Model`, `DualCLIPLoader`, `CLIPTextEncode`, `Load VAE`, `KSampler`/new sampler graph, `VAEDecode`, `SaveImage`, `SaveAudio`, video latent nodes. | Most workflows. |
| ComfyUI-GGUF | `city96/ComfyUI-GGUF` | `UnetLoaderGGUF`, `UnetLoaderGGUFAdvanced`, `CLIPLoaderGGUF`, `DualCLIPLoaderGGUF`, `TripleCLIPLoaderGGUF`, `QuadrupleCLIPLoaderGGUF`. | Q5 GGUF Qwen, FLUX.2 Dev, Wan2.2 GGUF workflows. |
| ComfyUI-VideoHelperSuite | `Kosinkadink/ComfyUI-VideoHelperSuite` | `VHS_LoadVideo`, `VHS_VideoCombine`, audio+video combine behavior. | Video IO, video output, interpolation, video-to-audio workflows. |
| ComfyUI-Frame-Interpolation | `Fannovel16/ComfyUI-Frame-Interpolation` | `RIFE VFI`, `FILM VFI`, `AMT VFI`, `Make Interpolation State List`, `VFI FloatToInt`. | 16 fps to 24 fps interpolation and general VFI. |
| comfyui_controlnet_aux | `Fannovel16/comfyui_controlnet_aux` | `AIO Aux Preprocessor`, `CannyEdgePreprocessor`, `DepthAnythingV2Preprocessor`. | FLUX Canny/Depth and control workflows. |
| ComfyUI-Advanced-ControlNet | `Kosinkadink/ComfyUI-Advanced-ControlNet` | Advanced ControlNet application/scheduling nodes. | FLUX control workflows requiring scheduled strength. |
| ComfyUI-Florence2 | `kijai/ComfyUI-Florence2` | `DownloadAndLoadFlorence2Model`, `Florence2Run`. | Florence2 image caption/OCR/object detection plugin. |
| ComfyUI-MMAudio | `kijai/ComfyUI-MMAudio` | `MMAudioModelLoader`, `MMAudioFeatureUtilsLoader`, `MMAudioSampler`, `MMAudioVoCoderLoader`. | MMAudio video-to-audio plugin. |
| audio-separation-nodes-comfyui | `christian-byrne/audio-separation-nodes-comfyui` | `Audio Separation`, `Audio Combine`, `Audio Crop`, `Audio Tempo Match`, `Audio Speed Shift`, `Audio Get Tempo`, `Audio Video Combine`. | Stem splitting. |
| ComfyUI Chatterbox | `filliptm/ComfyUI_Fill-ChatterBox` or `wildminder/ComfyUI-Chatterbox`, pinned by commit after smoke test | `FL Chatterbox TTS`, `FL Chatterbox Turbo TTS`, `FL Chatterbox Multilingual TTS`, `FL Chatterbox VC`, `FL Chatterbox Dialog TTS` or equivalent class names exposed by the pinned node pack. | Current Chatterbox, Chatterbox Turbo, Chatterbox Multilingual TTS/VC plugins. |
| ACE-Step native/templates | Comfy core templates and/or `ace-step/ACE-Step-ComfyUI` local mode | ACE-Step 1.5 music nodes/templates. Cloud mode is forbidden. | ACE-Step music plugin. |
| ComfyUI-Foundation-1 | `Saganaki22/ComfyUI-Foundation-1` | Foundation-1 structured text-to-sample nodes. | Foundation Music plugin. |
| Comfy RMBG/BiRefNet workflow | Comfy utility workflow and/or `1038lab/ComfyUI-RMBG` | Background-removal node using BiRefNet/RMBG. | BiRefNet background removal. |
| Slopperly Comfy Nodes | new in repo | `SlopperlyDiffusersImageGenerate`, `SlopperlyDiffusersImageEdit`, `SlopperlyDiffusersVideoGenerate`, `SlopperlyDiffusersAudioGenerate`, `SlopperlyArtifactSave`. | Current local models that lack native Comfy/core support. This is how existing local models are migrated without random model swaps. |

Every custom node pack must be pinned in `slopperly/runtime/comfy/nodes.lock.yaml` with URL, commit SHA, install command, required Python extras, and `/object_info` class names to assert.

## 7. Q5/GGUF policy for main image/video models

Q5 GGUF is a target for main local image/video/edit models where actual GGUF artifacts exist and a ComfyUI-GGUF loader can load them. The model registry must be explicit; no code may claim Q5 support without a real model file and a passing workflow artifact test Preffered ggufs from unsloth repos, but others can be used if unsloth doesnt have them.

| Task | Default production model/profile | Q5/GGUF target | Loader/node requirement | Dropdown exposure rule |
|---|---|---|---|---|
| Image generation | Qwen-Image-2512 native/FP8 or GGUF profile | `unsloth/Qwen-Image-2512-GGUF`, `qwen-image-2512-Q5_K_M.gguf` | `UnetLoaderGGUF` or `UnetLoaderGGUFAdvanced`; Qwen text encoder and VAE in Comfy model folders. | Show after 1024 and supported aspect-ratio artifact tests pass. |
| Image editing | Qwen-Image-Edit-2511 native/FP8 or GGUF profile | `unsloth/Qwen-Image-Edit-2511-GGUF`, `qwen-image-edit-2511-Q5_K_M.gguf` | `UnetLoaderGGUF`; multi-image loader patch points; Qwen VAE/text encoder. | Show after one-ref and three-ref edit tests pass. |
| FLUX cloud replacement / quality edit | FLUX.2 Klein 4B for 16GB profile; FLUX.2 Dev for quality profile | `city96/FLUX.2-dev-gguf`, `flux2-dev-Q5_K_M.gguf` is a 24.1GB artifact | `UnetLoaderGGUF`; Mistral-Small FLUX.2 text encoder; FLUX.2 VAE. | FLUX.2 Dev Q5 is not a 16GB default. Show only on certified device profile after artifact test. |
| Video default T2V/I2V | Wan2.2 TI2V-5B | `QuantStack/Wan2.2-TI2V-5B-GGUF`, `Wan2.2-TI2V-5B-Q5_K_M.gguf` is 3.81GB | `UnetLoaderGGUF`; UMT5 text encoder; Wan VAE; Wan latent nodes. | 16GB default after 720P-family/24fps artifact test passes. |
| Video quality T2V | Wan2.2 T2V-A14B | `QuantStack/Wan2.2-T2V-A14B-GGUF`, high-noise and low-noise Q5_K_M pair | Two `UnetLoaderGGUF` nodes or matching workflow loaders; UMT5; Wan VAE; two-stage high/low sampler. | Show after 720P-family/16fps generation and 24fps interpolation artifact test passes on target device. |
| Video quality I2V | Wan2.2 I2V-A14B | `QuantStack/Wan2.2-I2V-A14B-GGUF`, high-noise and low-noise Q5_K_M pair; I2V Q5 high/low files are 10.8GB each | Two `UnetLoaderGGUF` nodes; UMT5; Wan VAE; input image loader. | Show after image-conditioned 720P-family/16fps generation and 24fps interpolation artifact test passes. |

## 8. Model/plugin migration matrix

Legend:

- `MIGRATE_NATIVE_COMFY`: use official/native Comfy workflow or established Comfy node pack.
- `MIGRATE_GGUF_COMFY`: use ComfyUI-GGUF and named Q5 GGUF assets recorded in `models.yaml`.
- `MIGRATE_SLOPPERLY_NODE`: move current direct local code into Slopperly-owned Comfy custom node; do not replace model.
- `REMOVED_CLOUD`: delete the old cloud provider plugin from production. Equivalent local functionality must be a direct local model entry with its own workflow and passing artifact test, not a cloud-branded alias.
- `REMOVE_CLOUD`: remove external/cloud backend logic from production.

### 8.1 Image functions

| Current plugin | Current model ID | Action | Local workflow ID | Required backend/nodes | UI contract |
|---|---|---|---|---|---|
| `image/_krea2_base.py` | `ethanfel/Krea-2-Base-Diffusers` | `MIGRATE_NATIVE_COMFY` using the Krea 2 RAW/base family | `krea2_base_t2i` | Krea 2 Comfy workflow/template; model loader, prompt subgraph, resolution selector, sampler, VAE decode, `SaveImage`. | Keep prompt, negative, resolution, frames, steps, guidance, seed, LoRA. |
| `image/krea2_turbo.py` | `OzzyGT/Krea_2_Turbo_sdnq_dynamic_8bit` | `MIGRATE_NATIVE_COMFY` using Krea 2 Turbo | `krea2_turbo_t2i` | Krea 2 Turbo Comfy workflow; prompt subgraph, resolution selector, sampler, VAE decode, `SaveImage`. | Same as current. |
| `image/anima.py` | `mrfatso/anima-preview3-diffusers` | `MIGRATE_NATIVE_COMFY` using Anima Comfy workflow/template | `anima_t2i_i2i` | Anima Subgraph workflow; prompt/negative, model loader, sampler, VAE decode, `SaveImage`; image-strip path is patched for I2I mode. | Keep prompt, negative, image strip, resolution, frames, steps, guidance, strength, seed, LoRA. |
| `image/birefnet.py` | `ZhengPeng7/BiRefNet_HR` | `MIGRATE_NATIVE_COMFY` | `birefnet_rmbg` | BiRefNet/RMBG workflow: `LoadImage` -> RMBG/BiRefNet node -> `SaveImage`. | Keep selected image behavior; output must be PNG with alpha. |
| `image/ernie.py` | `baidu/ERNIE-Image` | `MIGRATE_NATIVE_COMFY` | `ernie_image_t2i` | ERNIE-Image Comfy template. | Keep prompt, negative, resolution, frames, steps, guidance, seed. |
| `image/ernie_turbo.py` | `baidu/ERNIE-Image-Turbo` | `MIGRATE_NATIVE_COMFY` | `ernie_image_turbo_t2i` | ERNIE Turbo Comfy template. | Same as current; default steps remain 8. |
| `image/flux2_dev.py` | `diffusers/FLUX.2-dev-bnb-4bit` | `MIGRATE_GGUF_COMFY` for quality profile; use FP8/GGUF workflow, not cloud | `flux2_dev_gguf_quality` | `UnetLoaderGGUF` or `Load Diffusion Model`; FLUX.2 text encoder; FLUX.2 VAE; multi-reference image nodes. | Keep prompt, multi-images, resolution, frames, steps, guidance, seed. Remove HF token UI from normal runtime; gated-download auth belongs in model manager only. |
| `image/flux2_klein_4b.py` | `black-forest-labs/FLUX.2-klein-4B` | `MIGRATE_NATIVE_COMFY` | `flux2_klein_4b_t2i_edit` | Official FLUX.2 Klein 4B Comfy workflow; supports T2I and edit. | Keep prompt, image strip, resolution, frames, steps, guidance, strength, seed, LoRA. This is the 16GB FLUX-family default. |
| `image/flux2_klein_9b.py` | `ModelsLab/FLUX.2-klein-9B` | `MIGRATE_NATIVE_COMFY` | `flux2_klein_9b_t2i_edit` | Official FLUX.2 Klein 9B workflow. | Same fields; show only after device profile certification. |
| `image/flux2_klein_9b_schematic.py` | `nomadoor/flux-2-klein-9B-schematic-lora` | `MIGRATE_NATIVE_COMFY` | `flux2_klein_9b_schematic_lora` | FLUX.2 Klein 9B + schematic LoRA loader. | Keep prompt, image strip, frames, steps, guidance, seed. |
| `image/flux_canny.py` | `fuliucansheng/FLUX.1-Canny-dev-diffusers-lora` | `MIGRATE_NATIVE_COMFY` | `flux1_canny_control` | `LoadImage`; `CannyEdgePreprocessor`/preprocessed image; FLUX Canny model or LoRA; `DualCLIPLoader`; `Load VAE`; sampler; `SaveImage`. | Keep current control image strip, resolution, frames, steps, guidance, strength, seed, LoRA. |
| `image/flux_depth.py` | `romanfratric234/FLUX.1-Depth-dev-lora` | `MIGRATE_NATIVE_COMFY` | `flux1_depth_control` | `LoadImage`; `DepthAnythingV2Preprocessor` or supplied depth; FLUX Depth LoRA; `DualCLIPLoader`; `Load VAE`; sampler; `SaveImage`. | Same UI fields as current. |
| `image/flux_kontext.py` | `yuvraj108c/FLUX.1-Kontext-dev` | `MIGRATE_NATIVE_COMFY` | `flux_kontext_edit` | FLUX Kontext Comfy workflow; image edit path. | Keep prompt, image strip, resolution, frames, steps, guidance, strength, seed, LoRA. |
| `image/flux_redux.py` | `Runware/FLUX.1-Redux-dev` | `MIGRATE_NATIVE_COMFY` | `flux_redux_restyle` | FLUX Redux Comfy workflow/reference-image path. | Keep image strip, resolution, frames, steps, guidance, seed. |
| `image/google_nano_banana.py` | `google/nano-banana` | `REMOVED_CLOUD` | None | No Google API and no production alias. | Remove from production. Local Qwen edit must stand on its own direct entry after certification. |
| `image/ideogram4.py` | `ideogram-ai/ideogram-4-nf4-diffusers` | `MIGRATE_NATIVE_COMFY` using Ideogram 4 Comfy workflow/template | `ideogram4_t2i` | Ideogram 4 workflow/template; prompt/structured-prompt controls, model loader, sampler, VAE decode, `SaveImage`. | Keep prompt, resolution, frames, steps, guidance, seed, LoRA. Remove HF token from main UI; gated auth goes to model manager. |
| `image/kontext_relight.py` | `kontext-community/relighting-kontext-dev-lora-v3` | `MIGRATE_NATIVE_COMFY` | `kontext_relight` | FLUX Kontext/Relight LoRA workflow; illumination controls patched into workflow params. | Keep prompt, image strip, resolution, frames, steps, guidance, illumination, seed. |
| `image/lumina2.py` | `Alpha-VLLM/Lumina-Image-2.0` | `MIGRATE_NATIVE_COMFY` | `lumina2_t2i` | Lumina-Image 2.0 Comfy support/workflow; checkpoint in `models/checkpoints`. | Keep prompt, negative, resolution, frames, steps, guidance, seed. |
| `image/maxine_vsr.py` | `nvidia/maxine-vsr` | Replace backend function with local Comfy super-resolution workflow; do not use NVIDIA Maxine runtime | `local_image_vsr_upscale` | `LoadImage`; `UpscaleModelLoader`; `ImageUpscaleWithModel`; resize/crop node; `SaveImage`. | Keep resolution, frames, seed; display name must become Local Super Resolution, not Maxine. |
| `image/nucleus_moe.py` | `NucleusAI/Nucleus-Image` | `MIGRATE_SLOPPERLY_NODE` using same model | `nucleus_image_t2i` | Slopperly Comfy diffusers node until upstream Comfy support exists. | Keep prompt, negative, resolution, frames, steps, guidance, seed. Do not substitute Qwen/Flux. |
| `image/omnigen.py` | `Shitao/OmniGen-v1-diffusers` | `MIGRATE_NATIVE_COMFY` via `1038lab/ComfyUI-OmniGen` | `omnigen_v1_multi_image` | OmniGen Comfy node pack; multi-image inputs and per-image prompts preserved; `SaveImage`. | Keep triple prompt/image UI, resolution, frames, steps, guidance, seed. |
| `image/qwen_image.py` | `Qwen/Qwen-Image-2512` | `MIGRATE_GGUF_COMFY` and native Comfy profile | `qwen_image_2512_t2i_gguf` | Qwen Image 2512 Comfy native workflow or Q5 GGUF through `UnetLoaderGGUF`; Qwen text encoder; Qwen VAE. | Keep prompt, image strip, resolution, frames, steps, strength, seed, LoRA. |
| `image/qwen_image_edit.py` | `Qwen/Qwen-Image-Edit-2511` | `MIGRATE_GGUF_COMFY` and native Comfy profile | `qwen_image_edit_2511_multi_gguf` | Qwen Image Edit 2511 Comfy native workflow or Q5 GGUF; multi-image reference loader; Qwen VAE/text encoder. | Keep prompt, negative, multi-images, resolution, frames, steps, seed, LoRA. |
| `image/zimage.py` | `Tongyi-MAI/Z-Image` | `MIGRATE_NATIVE_COMFY` using Z-Image Comfy template/workflow | `zimage_t2i_i2i` | Z-Image workflow: model loader, prompt/negative, sampler, VAE decode, image edit path, `SaveImage`. | Keep prompt, negative, image strip, resolution, frames, steps, guidance, strength, seed. |
| `image/zimage.py` | `Tongyi-MAI/Z-Image-Turbo` | `MIGRATE_NATIVE_COMFY` using Z-Image Turbo workflow | `zimage_turbo_t2i_i2i` | Z-Image Turbo workflow; 8-step default path, sampler, VAE decode, `SaveImage`. | Same fields; default steps remain 8. |

### 8.2 Video functions

| Current plugin | Current model ID | Action | Local workflow ID | Required backend/nodes | UI contract |
|---|---|---|---|---|---|
| `video/google_veo.py` | `google/veo` | `REMOVED_CLOUD` | None | No Google API and no production alias. | Remove from production. Direct local video entries must be certified independently. |
| `video/minimax.py` txt2vid | `Hailuo/MiniMax/txt2vid` | `REMOVED_CLOUD` | None | No MiniMax API and no production alias. | Remove from production. Direct local T2V entries must be certified independently. |
| `video/minimax.py` img2vid | `Hailuo/MiniMax/img2vid` | `REMOVED_CLOUD` | None | No MiniMax API and no production alias. | Remove from production. Direct local I2V entries must be certified independently. |
| `video/minimax.py` subject2vid | `Hailuo/MiniMax/subject2vid` | `REMOVED_CLOUD` | None | No MiniMax API and no production alias. | Remove from production. Subject/reference video must be a direct local workflow after certification. |
| `video/ltx2.py` | `rootonchair/LTX-2-19b-distilled` | `MIGRATE_NATIVE_COMFY` | `ltx2_19b_distilled_t2v_i2v` | LTX workflow using same 19B distilled family; model loader, text encoder, VAE, video sampler, `VHS_VideoCombine`. | Keep prompt, negative, video/image strip, resolution, frames, seed, LoRA. |
| `video/ltx23_extend.py` | `LTX-2.3 Extend Staged` | `MIGRATE_NATIVE_COMFY` | `ltx23_extend_staged` | LTX-2.3 extend template; input video strip path patched; SaveVideo/VHS output. | Keep current extend UI. Duration/frame count must derive from input clip and requested extension. |
| `video/ltx23_lipsync.py` | `LTX-2.3 Lip Sync` | `MIGRATE_NATIVE_COMFY` | `ltx23_lipsync_dialogue` | LTX-2.3 lipsync/reference workflow; audio ref path; target frame count from audio. | Keep prompt, negative, video strip, image strip/audio ref behavior, resolution, frames, seed, LoRA. |
| `video/ltx23_multi.py` | `LTX-2.3 Multi-Input Staged` | `MIGRATE_NATIVE_COMFY` | `ltx23_multi_staged` | LTX-2.3 multimodal workflow; middle anchors patched from `ModelInputs.middle_images_paths`. | Keep current multi/staged UI. |
| `video/ltx23_multi_ic_lora.py` | `LTX-2.3 IC-LoRA Staged` | `MIGRATE_NATIVE_COMFY` | `ltx23_ic_lora_staged` | LTX-2.3 IC-LoRA workflow; LoRA loader and image refs. | Keep current UI. |
| `video/skyreels.py` | `Skywork/SkyReels-V1-Hunyuan-T2V` | `MIGRATE_NATIVE_COMFY` using Kijai SkyReels/Hunyuan Comfy conversion | `skyreels_hunyuan_t2v_i2v` | Kijai SkyReels/Hunyuan Comfy conversion; Hunyuan wrapper/native workflow nodes; `VHS_VideoCombine`. | Keep prompt, negative, video strip, resolution, frames, steps, guidance, seed. |
| `video/wan_t2v.py` | `Wan-AI/Wan2.2-T2V-A14B-Diffusers` | `MIGRATE_GGUF_COMFY` and native FP8 profile | `wan22_t2v_a14b_720p16_to24_gguf` | Two high/low-noise loaders; UMT5; Wan VAE; `EmptyHunyuanLatentVideo`; sampler; interpolation workflow; `VHS_VideoCombine`. | Keep prompt, negative, resolution, frames, seed, LoRA. Slopperly default: 720P-family, 16fps generation, 24fps final. |
| `video/wan_i2v.py` | `Wan-AI/Wan2.2-I2V-A14B-Diffusers` | `MIGRATE_GGUF_COMFY` and native FP8 profile | `wan22_i2v_a14b_720p16_to24_gguf` | Two high/low-noise loaders; image input; UMT5; Wan VAE; sampler; interpolation; `VHS_VideoCombine`. | Keep prompt, negative, video/image strip, resolution, frames, seed, LoRA. |
| new local default | `Wan-AI/Wan2.2-TI2V-5B` | Add dropdown entry as local default, not replacement for existing Wan A14B | `wan22_ti2v_5b_720p24_gguf` | `Wan22ImageToVideoLatent`; Q5 GGUF loader; UMT5; Wan VAE; `VHS_VideoCombine`. | Standard 24fps local default for T2V/I2V. |
| `video/maxine_vsr_video.py` | `nvidia/maxine-vsr-video` | Replace backend function with Comfy video super-resolution/restoration workflow | `local_video_vsr_upscale` | `VHS_LoadVideo`; per-frame `UpscaleModelLoader` + `ImageUpscaleWithModel`; `VHS_VideoCombine`; preserve audio when present. | Keep video strip, resolution, seed. Display name must become Local Video Super Resolution. |

### 8.3 Audio, TTS, music, and STT functions

| Current plugin | Current model ID | Action | Local workflow/runtime ID | Required backend/nodes | UI contract |
|---|---|---|---|---|---|
| `audio/_stable_audio_3.py` | `cocktailpeanut/stable-audio-3-medium-base` | `MIGRATE_NATIVE_COMFY` | `stable_audio_3_medium_base` | Stable Audio 3 Comfy template; checkpoints in `models/checkpoints`; text encoder in `models/text_encoders`; `SaveAudio`. | Keep prompt, negative, audio duration, steps, guidance, seed. |
| `audio/ace_step.py` | `ACE-Step/acestep-v15-xl-turbo-diffusers` | `MIGRATE_NATIVE_COMFY` | `ace_step_15_music` | ACE-Step 1.5 Comfy native/template or local-mode node; cloud mode forbidden. | Keep prompt, duration, steps, guidance, music params, seed. |
| `audio/foundation_music.py` | `tintwotin/Foundation-1-Diffusers` | `MIGRATE_NATIVE_COMFY` | `foundation1_music_loop` | `ComfyUI-Foundation-1` structured text-to-sample nodes. | Keep prompt, negative, duration, steps, seed. BPM/key/time controls are mapped to Foundation-1 loop parameters in the workflow schema. |
| `audio/mmaudio.py` | `MMAudio` | `MIGRATE_NATIVE_COMFY` | `mmaudio_video_to_audio` | `MMAudioModelLoader`, `MMAudioFeatureUtilsLoader`, `MMAudioSampler`, `MMAudioVoCoderLoader`; `SaveAudio` or video+audio combine. | Keep prompt, negative, video strip, duration, steps, guidance, seed. |
| `audio/stem_split.py` | `StemSplitter` | `MIGRATE_NATIVE_COMFY` | `audio_stem_split_demucs` | `Audio Separation` node outputs bass/drums/other/vocals; `SaveAudio` per stem. | Keep selected audio behavior; output four stem artifacts. |
| `audio/chatterbox.py` | `Chatterbox` | `MIGRATE_NATIVE_COMFY` using a pinned Chatterbox Comfy node pack; keep the Chatterbox model family | `chatterbox_tts_vc_comfy` | `FL Chatterbox TTS` or `Chatterbox TTS`; reference-audio input; `SaveAudio`. | Keep prompt, duration, audio ref, chat params, seed. Parameters not exposed by the selected node are recorded in the workflow schema as deliberately unmapped. |
| `audio/chatterbox_multilingual.py` | `ChatterboxMultilingual` | `MIGRATE_NATIVE_COMFY` using Chatterbox multilingual Comfy node | `chatterbox_multilingual_tts_comfy` | `FL Chatterbox Multilingual TTS`; language/ref-audio inputs; `SaveAudio`. | Keep prompt, audio ref, chat params, seed. |
| `audio/chatterbox_turbo.py` | `ChatterboxTurbo` | `MIGRATE_NATIVE_COMFY` using Chatterbox Turbo Comfy node | `chatterbox_turbo_tts_comfy` | `FL Chatterbox Turbo TTS`; reference-audio input; speed/expression controls recorded in schema; `SaveAudio`. | Keep prompt, duration, audio ref, chat params, seed. |
| `audio/moss_tts.py` | `MOSS-TTS` | `MIGRATE_VLLM_OMNI` | `vllm_omni_moss_tts_nano` | `OpenMOSS-Team/MOSS-TTS-Nano` through vLLM-Omni. | Keep prompt and seed. Clone controls are shown only in plugins whose current UI already exposes reference audio. |
| `audio/omnivoice.py` | `OmniVoice` | `MIGRATE_VLLM_OMNI` | `vllm_omni_omnivoice` | `k2-fsa/OmniVoice` through vLLM-Omni; ref audio/ref text mapping. | Keep prompt, speed, steps, guidance, seed; wire audio/text ref fields correctly. |
| `text/faster_whisper_transcribe.py` | `faster-whisper-transcribe` | `MIGRATE_VLLM` | `vllm_whisper_large_v3_turbo_stt` | vLLM `vllm[audio]`; OpenAI-compatible transcription endpoint. | Preserve current transcription output file/text strip behavior. |

### 8.4 Text, caption, VLM, prompt-rewrite functions

| Current plugin | Current model ID | Action | Local runtime/workflow ID | Required backend/nodes | UI contract |
|---|---|---|---|---|---|
| `text/moviigen_rewriter.py` | `ZuluVision/MoviiGen1.1_Prompt_Rewriter` | `MIGRATE_LLAMACPP`; keep the function as a local prompt-rewriter service | `llamacpp_prompt_rewriter` | llama.cpp server; 60k context, 30k max new token defaults; model registry controls the tested Q5 GGUF. | Keep prompt field and result insertion behavior. |
| `text/florence2.py` | `florence-community/Florence-2-large` | `MIGRATE_NATIVE_COMFY` | `florence2_caption_ocr` | `DownloadAndLoadFlorence2Model`, `Florence2Run`; image input patched. | Preserve text/caption output. |
| `text/marlin_video_captions.py` | `_MODEL_ID` / Marlin local captioning | `MIGRATE_VLLM`; serve a pinned local video-capable VLM recorded in `models.yaml` | `vllm_video_caption_vlm` | vLLM multimodal chat completions with video/image inputs and pinned chat template. | Preserve caption output shape and timeline placement. Do not call cloud VLM. |

## 9. Required Comfy workflow packs

Every workflow pack must have this exact structure:

```text
slopperly/workflows/comfy/<workflow_id>/
  workflow.editable.json
  workflow.api.json
  params.schema.json
  models.yaml
  test_payload.json
  README.md
```

The `params.schema.json` must map Slopperly `ModelInputs` fields to exact Comfy node IDs and input names. Node IDs must not be discovered by fuzzy title matching at runtime, except during a developer conversion tool that writes the schema once.

### 9.1 Image workflows

| Workflow ID | Purpose | Core patch nodes/params | Required artifact test |
|---|---|---|---|
| `qwen_image_2512_t2i_gguf` | Qwen text-to-image default. | prompt, negative prompt, width, height, steps, seed, guidance, LoRA; `UnetLoaderGGUF` or native loader; VAE; text encoder; `SaveImage`. | 1024 image and every supported aspect-ratio preset from UI mapping. |
| `qwen_image_edit_2511_multi_gguf` | Qwen multi-reference image editing. | prompt, negative, 1-3 reference image loaders, width/height, steps, seed, LoRA, `SaveImage`. | One-ref edit and three-ref edit; output dimensions match request. |
| `flux2_klein_4b_t2i_edit` | 16GB FLUX-family T2I/edit. | prompt, image input, width/height, steps, guidance, strength, seed, LoRA. | 1024 T2I and image edit. |
| `flux2_klein_9b_t2i_edit` | Higher quality FLUX Klein. | Same as 4B. | 1024 T2I and image edit on certified device profile. |
| `flux2_dev_gguf_quality` | Local FLUX.2 Dev Q5 quality profile. | `UnetLoaderGGUF`, FLUX.2 text encoder, VAE, multi-image refs. | Multi-ref edit and T2I; not shown until certified. |
| `flux1_canny_control` | FLUX Canny control. | image loader, canny preprocessor or supplied canny image, model/LoRA loader, strength, prompt, seed. | Input edge preservation smoke image. |
| `flux1_depth_control` | FLUX depth control. | image loader, depth preprocessor or supplied depth image, model/LoRA loader, strength, prompt, seed. | Input layout preservation smoke image. |
| `flux_kontext_edit` | Kontext image edit. | prompt, input image, strength, LoRA, seed, output. | Semantic edit smoke. |
| `flux_redux_restyle` | Redux restyle/reference. | image input, seed, steps, guidance. | Style transfer smoke. |
| `kontext_relight` | Relight. | image input, illumination style, light direction, prompt, seed. | Lighting direction smoke. |
| `birefnet_rmbg` | Background removal. | image input, model, alpha output. | PNG with alpha, same dimensions as input. |
| `local_image_vsr_upscale` | Image super-resolution. | image input, upscale model, target width/height. | Input low-res image -> target resolution output. |
| `lumina2_t2i` | Lumina-Image 2.0. | checkpoint, prompt, negative, size, seed, steps, guidance. | PNG artifact. |
| `ideogram4_t2i` | Ideogram 4. | prompt/structured prompt mode, size, seed, steps. | PNG artifact and text rendering prompt smoke. |
| `omnigen_v1_multi_image` | OmniGen v1 multi-image. | 1-3 input images, image prompt placeholders, output size, seed. | Triple prompt/image test. |
| `zimage_t2i_i2i`, `zimage_turbo_t2i_i2i` | Z-Image family. | prompt, image input, strength, steps, seed. | T2I and I2I smoke. |
| `nucleus_image_t2i` | Nucleus Image via Slopperly node. | prompt, negative, size, steps, guidance, seed. | PNG smoke. |

### 9.2 Video workflows

The Slopperly display may say 720p, but the backend must map to model-supported dimensions. For Wan2.2 TI2V-5B, the safe documented 720P-family examples include 1280×704 and 704×1280. Exact 1280×720 is accepted only after the Comfy workflow test proves it.

| Workflow ID | Purpose | Core patch nodes/params | Default | Required artifact test |
|---|---|---|---|---|
| `wan22_ti2v_5b_720p24_gguf` | Default local T2V/I2V. | prompt, negative, source image for I2V mode, width/height mapped to supported 720P family, frames, fps=24, seed, steps, guidance; `Wan22ImageToVideoLatent`; `UnetLoaderGGUF`; `VHS_VideoCombine`. | 720P-family, 24fps. | MP4 width/height matches supported mapping; fps=24; duration/frame count match request. |
| `wan22_t2v_a14b_720p16_to24_gguf` | Quality T2V. | two high/low-noise Q5 loaders, UMT5, VAE, latent video, seed, two-stage sampler, interpolation to 24fps. | 720P-family, native 16fps, final 24fps. | Native intermediate and final MP4 validated; duration preserved. |
| `wan22_i2v_a14b_720p16_to24_gguf` | Quality I2V. | image input, high/low-noise Q5 loaders, UMT5, VAE, latent video, interpolation. | 720P-family, native 16fps, final 24fps. | Source image affects first frames; final fps=24. |
| `wan22_flf2v_a14b_720p16_to24` | First/last-frame video. | first image, last image, `WanFirstLastFrameToVideo`, high/low loaders, interpolation. | 720P-family. | First and last frame correspondence smoke. |
| `ltx23_t2v` | LTX-2.3 text-to-video. | prompt, negative, width/height, frames/duration, seed, steps, LoRA, save video. | 720P/24fps first target. | MP4 24fps short clip. |
| `ltx23_i2v` | LTX-2.3 image-to-video. | source image, prompt, negative, width/height, duration/fps, seed. | 720P/24fps first target. | MP4 24fps with source-frame coherence. |
| `ltx23_extend_staged` | Extend selected video. | video input, prompt, negative, extension duration, seed. | Preserve input fps unless UI overrides. | Output duration > input duration. |
| `ltx23_multi_staged` | Multi-anchor/staged video. | video/image refs, anchor fractions, prompt, seed. | Existing plugin defaults. | Anchor smoke with middle-image timing. |
| `ltx23_ic_lora_staged` | IC-LoRA/reference video. | image refs, LoRA loader, prompt, seed. | Existing plugin defaults. | Subject/reference consistency smoke. |
| `ltx23_lipsync_dialogue` | Dialogue/lipsync video. | audio ref, prompt, source image/video, target frame count from audio duration. | 24fps final. | Audio length drives frame count; final video duration equals audio within tolerance. |
| `skyreels_hunyuan_t2v_i2v` | SkyReels/Hunyuan workflow. | prompt, negative, source image for I2V mode, width/height, frames, seed. | Existing plugin defaults adjusted by device profile. | MP4 smoke. |
| `local_video_vsr_upscale` | Video super-resolution. | input video, target resolution, upscale model, audio passthrough. | UI-selected target size. | MP4 output target size; fps/duration preserved. |
| `frame_interpolation_16_to24` | General 16fps to 24fps interpolation. | input frames/video, generated fps, target fps, VFI node, combine node. | 16 -> 24. | ffprobe fps=24; duration preserved; frame count approx ceil(duration*24). |

### 9.3 Audio workflows

| Workflow ID | Purpose | Core patch nodes/params | Required artifact test |
|---|---|---|---|
| `stable_audio_3_medium_base` | Text-to-audio/music/SFX. | prompt, negative, duration, seed, steps/guidance where exposed; checkpoint and text encoder. | WAV/FLAC with requested duration tolerance, non-silent waveform. |
| `ace_step_15_music` | Music with lyrics/BPM/key. | prompt, lyrics, BPM, key, time signature, duration, seed, steps, guidance. | WAV with duration, non-silent, metadata log includes music params. |
| `foundation1_music_loop` | Structured loop generation. | prompt, negative, BPM, bar count, key, duration. | Loop WAV duration matches BPM/bar mapping. |
| `mmaudio_video_to_audio` | Generate audio from video + prompt. | video frames/images, prompt, negative, duration, steps, cfg, seed; `MMAudioSampler`. | WAV 44.1kHz or model sample rate, duration matches requested/source. |
| `audio_stem_split_demucs` | Stem split. | audio input. | Four files: vocals, drums, bass, other; durations match source. |

## 10. vLLM/vLLM-Omni runtime mapping

### 10.1 STT through vLLM

`text/faster_whisper_transcribe.py` must stop using direct faster-whisper runtime in production and use the vLLM STT provider.

Required local server profile:

```yaml
id: vllm_whisper_large_v3_turbo_stt
runtime: vllm
model: openai/whisper-large-v3-turbo
task: transcription
install: pip install 'vllm[audio]'
endpoint: http://127.0.0.1:${VLLM_STT_PORT}/v1/audio/transcriptions
```

Test:

```text
Call FasterWhisperTranscribePlugin.generate() with a known WAV fixture.
Assert text contains expected words.
Assert no cloud network call occurs.
```

### 10.2 TTS and voice cloning through vLLM-Omni

vLLM-Omni provides the Qwen/Fish/OmniVoice/MOSS local speech profiles. Existing Chatterbox plugins remain Chatterbox-family implementations through Comfy nodes, not Qwen replacements. The speech dropdown shows local models, not cloud/provider names.

Required local model profiles:

| Profile ID | vLLM-Omni model | Task | Used for |
|---|---|---|---|
| `qwen3_tts_customvoice_1_7b` | `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` | predefined voices + style instructions | Default local TTS. |
| `qwen3_tts_based_clone_1_7b` | `Qwen/Qwen3-TTS-12Hz-1.7B-Base` | voice cloning via `ref_audio` + `ref_text` | Voice clone mode. |
| `qwen3_tts_voicedesign_1_7b` | `Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign` | natural-language voice design | Voice design UI/settings. |
| `qwen3_tts_customvoice_06b` | `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` | smaller/faster TTS | Low-memory/fast profile. |
| `qwen3_tts_base_06b` | `Qwen/Qwen3-TTS-12Hz-0.6B-Base` | smaller/faster voice clone | Low-memory clone profile. |
| `fish_speech_s2_pro` | `fishaudio/s2-pro` | TTS + reference-audio voice clone | High-quality local TTS/clone profile. |
| `omnivoice_vllm_omni` | `k2-fsa/OmniVoice` | voice clone via ref audio/text | Replacement for current OmniVoice plugin. |
| `moss_tts_nano_vllm_omni` | `OpenMOSS-Team/MOSS-TTS-Nano` | voice cloning only | Replacement for current MOSS plugin. |

Request mapping:

| ModelInputs field | vLLM-Omni field |
|---|---|
| `prompt` | `input` |
| `audio_ref` | `ref_audio` or voice upload sample |
| `text_ref` | `ref_text` |
| `speed` | `speed` |
| `temperature`/chat params | `instructions` only when semantically valid; otherwise logged as unmapped |
| `audio_length` | not forced for TTS unless server/model supports duration; use generated duration for downstream video timing |

Voice-clone test:

```text
1. Start Qwen3-TTS Base server.
2. Upload reference WAV through /v1/audio/voices or send file:// ref_audio with allowed-local-media-path.
3. Generate a 2-sentence WAV.
4. Validate file exists, sample rate is expected, duration > 1s, waveform is non-silent.
```

## 11. llama.cpp runtime mapping

Use the requested release family and Ubuntu x64 CUDA 13 artifact. The installer must verify driver/runtime compatibility and refuse to claim CUDA success without launching the binary.

Default config:

```yaml
runtime: llamacpp
context_length_default: 60000
max_new_tokens_default: 30000
host: 127.0.0.1
port: 8092
model_profile_default: qwen_long_context_prompt_q5
```

The model registry must include at least one 16GB-friendly Q5 GGUF prompt model and one quality prompt model. The exact model file is not hardcoded in UI. The implementation agent must select, record, and test the model in `config/models.yaml`.

Required llama.cpp plugin uses:

| Slopperly function | Current plugin/UI | Runtime behavior |
|---|---|---|
| Prompt enhancement/rewrite | `text/moviigen_rewriter.py` and any prompt-enhance buttons | Call llama.cpp chat/completions endpoint with local prompt-rewriter system prompt. |
| Chat/planning/script metadata | Current text/chat helpers where present | Call llama.cpp. |
| Comfy workflow prompt expansion | Stable Audio/Qwen/Flux prompt expansion when local LLM is needed | Call llama.cpp or embedded Comfy local Qwen prompt node only when it runs locally. |

Acceptance:

```text
- Launch llama.cpp server with configured GGUF.
- Send prompt rewrite request through plugin/service path.
- Assert response text is non-empty and does not exceed max token policy.
- Request n_ctx=60000 and max_new_tokens=30000.
- If the selected model/binary refuses those settings, the service must log the supported fallback and show diagnostics; it must not silently truncate.
```

## 12. UI preservation contract

For each plugin file, preserve these class-level contracts unless a cloud-only entry is being removed from production dropdown:

```text
MODEL_TYPE
INPUTS except InputSpec.API_KEY/HF_TOKEN moved to model manager
UI_SECTIONS except API key sections
PARAMS defaults where model-compatible
supports_batch behavior where current output mapping supports it
generate() return shape
```

`InputSpec.API_KEY` must disappear from production plugins. `InputSpec.HF_TOKEN` must not render in normal generation UI. Gated-download auth belongs in the model manager/install command, not in the generation panel.

Production dropdown policy:

| Entry type | Dropdown behavior |
|---|---|
| Current local model migrated to Comfy/vLLM/llama | Keep or rename only to clarify local runtime; no UI function removed. |
| Current cloud-only model | Remove cloud-branded entry. Do not keep a production saved-project alias. |
| Local model without a passing workflow artifact test | Do not show in production dropdown. Keep code under development profile only. |
| Q5/GGUF quality model too large for current device profile | Hide until `slopperly doctor --certify-profile` passes artifact tests. |

## 13. Resolution and fps rules

Default Slopperly video fps is 24fps.

| Model/workflow | Generation default | Final output default | Notes |
|---|---|---|---|
| Wan2.2 TI2V-5B | 720P-family, 24fps | 24fps | Use model-supported 720P dimensions; do not force unsupported 1280×720. |
| Wan2.2 T2V-A14B | 720P-family, 16fps | 24fps after interpolation | Use high/low-noise pair; final output must preserve duration. |
| Wan2.2 I2V-A14B | 720P-family, 16fps | 24fps after interpolation | Same as T2V with image conditioning. |
| LTX-2.3 | 720p/24fps first production target | 24fps | 1080p profile is shown only after artifact certification. |
| FLUX/Qwen image | Model-supported aspect ratios, UI-size mapping | PNG image | Qwen-Image-2512 supports named aspect-ratio presets; map UI sizes to supported dimensions. |

Dialogue/audio-driven video duration:

```text
audio_duration_seconds = measured duration from generated/supplied audio
target_fps = UI fps or default 24
target_frames = ceil(audio_duration_seconds * target_fps)
workflow_native_fps = model native fps, e.g. 16 for Wan A14B quality profile
native_frames = ceil(audio_duration_seconds * workflow_native_fps)
run video workflow for native_frames
interpolate/resample to target_frames at target_fps
trim or pad final video to audio duration
combine audio and video
log duration, native fps, target fps, native frames, target frames
```

This is mandatory for LTX lipsync/dialogue and any workflow that generates video from speech/dialogue.

## 14. Artifact acceptance tests

A feature is not migrated because a server starts. It is migrated only when the same plugin backend path produces a real artifact.

### 14.1 Test call pattern

```text
pytest tests/gpu/test_<plugin_id>.py --device cuda
  -> imports existing plugin class
  -> constructs ModelInputs with realistic parameters
  -> calls plugin.load(prefs, scene)
  -> calls plugin.generate(pipe_obj, inputs, scene, prefs)
  -> validates returned artifact and metadata
```

Do not test only `ComfyClient.run()` directly. Direct runtime tests are necessary but not sufficient.

### 14.2 Per-output validators

| Output | Validator |
|---|---|
| Image | PIL open succeeds; dimensions equal requested/model-mapped dimensions; alpha exists for background removal; file size > 0. |
| Video | `ffprobe` width/height/fps/duration/frame count; duration tolerance ±1 frame; final fps 24 where required; audio track presence when expected. |
| Audio | `ffprobe` or `soundfile`; duration tolerance; sample rate; non-zero waveform/RMS. |
| Text | Non-empty; expected schema; no provider error string; saved to current text output path. |

### 14.3 Required GPU test matrix

| Test ID | Plugin/workflow | Payload | Required artifact |
|---|---|---|---|
| `test_qwen_image_2512_t2i` | `QwenImagePlugin` | prompt, 1:1 preset, seed | PNG. |
| `test_qwen_image_edit_2511_one_ref` | `QwenImageEditPlugin` | one reference image + edit prompt | PNG. |
| `test_qwen_image_edit_2511_three_ref` | `QwenImageEditPlugin` | three references + edit prompt | PNG. |
| `test_flux2_klein_4b_edit` | `Flux2Klein4BPlugin` | image strip + prompt | PNG. |
| `test_cloud_provider_removed` | old cloud provider ID | direct removal check | Production plugin/model registry rejects the cloud ID; no alias path. |
| `test_birefnet_rmbg` | `BiRefNetPlugin` | image strip | PNG with alpha. |
| `test_wan22_ti2v_5b_t2v_720p24` | Wan TI2V workflow/default video dropdown | prompt, 24fps, short duration | MP4, 24fps. |
| `test_wan22_ti2v_5b_i2v_720p24` | Wan TI2V workflow | image + prompt | MP4, 24fps. |
| `test_wan22_t2v_a14b_16_to24` | `WanT2VPlugin` | prompt, 16fps native, 24fps final | MP4 final fps 24. |
| `test_wan22_i2v_a14b_16_to24` | `WanI2VPlugin` | image + prompt | MP4 final fps 24. |
| `test_ltx23_i2v_existing_workflow` | Current LTX 2.3 I2V workflow | image + prompt | MP4. |
| `test_ltx23_lipsync_audio_duration` | `LTX2_3LipSyncPlugin` | audio + prompt + source | MP4 duration equals audio. |
| `test_frame_interpolation` | `frame_interpolation_16_to24` | 16fps fixture | MP4 24fps same duration. |
| `test_mmaudio` | `MMAudioPlugin` | source video + prompt | WAV or MP4 with audio. |
| `test_stable_audio_3` | `StableAudio3Plugin` | prompt, duration | WAV. |
| `test_ace_step` | `AceStepPlugin` | prompt, lyrics/BPM | WAV. |
| `test_foundation_music` | `FoundationMusicPlugin` | prompt/BPM/key | WAV. |
| `test_stem_split` | `StemSplitterPlugin` | WAV fixture | four stem files. |
| `test_vllm_stt` | `FasterWhisperTranscribePlugin` | known WAV | text transcript. |
| `test_vllm_omni_tts` | TTS plugin wrapper | prompt only | WAV. |
| `test_vllm_omni_voice_clone` | TTS/VC wrapper | prompt + ref audio + ref text | WAV. |
| `test_llamacpp_prompt_rewrite` | `MoviiGenRewriterPlugin` | prompt | rewritten text. |
| `test_florence2_caption` | `Florence2Plugin` | image | caption text. |
| `test_video_caption_vlm` | `MarlinVideoCaptionsPlugin` | MP4 fixture | caption text/markers. |

### 14.4 No-cloud network audit

Run artifact tests with network restricted after model downloads are complete. During generation, allowed outbound targets are only:

```text
127.0.0.1
localhost
configured local LAN runtime only when explicitly marked as local/self-hosted
```

CI/test harness must fail on any DNS or HTTP request to cloud inference providers during generation.

## 15. Implementation order

1. Create `/reference/palladium` and `/slopperly` separation.
2. Add runtime config/model registry.
3. Replace remote backend preferences with local runtime preferences.
4. Implement Comfy owned runtime supervisor and API client.
5. Convert the existing `remote_backends/comfyui_adapter.py` logic into the Slopperly Comfy runner; keep its useful output mapping, but remove “user starts Comfy first” as the production assumption.
6. Add Comfy workflow pack schema and validation tool.
7. Port existing `ltx-2.3-i2v.json` into the new workflow pack format.
8. Add Qwen, FLUX Klein, Wan, BiRefNet, interpolation, MMAudio, Stable Audio, ACE-Step, Foundation, Florence workflow packs.
9. Add Slopperly Comfy custom nodes for current models without native Comfy node support.
10. Add vLLM STT supervisor/client.
11. Add vLLM-Omni TTS/VC supervisor/client.
12. Add llama.cpp install/supervisor/client.
13. Rewrite plugins as thin local-runtime wrappers while preserving UI contracts.
14. Remove cloud adapters/manifests/API-key UI from production.
15. Add GPU artifact tests per plugin.
16. Add no-cloud grep and runtime network audit.
17. Certify dropdown entries by device profile.

## 16. Device profile and acceptance command set

Target hardware profile:

```yaml
os: Ubuntu x64
gpu: NVIDIA Ampere or newer
vram_minimum: 16GB
cuda_runtime_target: CUDA 13-compatible environment
primary_test_card: RTX 4090 or equivalent
```

Acceptance commands to implement:

```bash
python -m slopperly.runtime.comfy.install --profile cuda13 --pin slopperly/runtime/comfy/nodes.lock.yaml
python -m slopperly.runtime.vllm.install --venv .slopperly/vllm-venv --extras audio
python -m slopperly.runtime.vllm_omni.install --venv .slopperly/vllm-omni-venv
python -m slopperly.runtime.llamacpp.install --release b9803 --artifact ubuntu-x64-cuda13
python -m slopperly.models.download --profile smoke_16gb --accept-licenses
python -m slopperly.doctor --local-only --cuda --runtimes all
pytest tests/unit
pytest tests/integration
pytest tests/gpu --device cuda --profile smoke_16gb
python -m slopperly.audit.no_cloud
python -m slopperly.audit.dropdown_certification --profile smoke_16gb
```

A dropdown entry is production-visible only when `dropdown_certification` finds a passing plugin artifact test for that entry on the target profile.

## 17. Source notes

The following upstream sources are the factual basis for this spec:

- ComfyUI workflow API format docs: https://docs.comfy.org/development/api-development/workflow-api-format
- llama.cpp release b9803: https://github.com/openresearchtools/llama-cpp-arm64-builds/releases/tag/b9803 (or newer) ubuntu x64 build
- vLLM STT docs: https://docs.vllm.ai/en/latest/serving/online_serving/speech_to_text/
- vLLM multimodal docs: https://docs.vllm.ai/en/latest/features/multimodal_inputs/
- vLLM-Omni speech API: https://docs.vllm.ai/projects/vllm-omni/en/latest/serving/speech_api/
- Comfy Wan2.2 docs: https://docs.comfy.org/tutorials/video/wan/wan2_2
- Wan2.2 TI2V-5B model card: https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B
- QuantStack Wan2.2 TI2V 5B GGUF: https://huggingface.co/QuantStack/Wan2.2-TI2V-5B-GGUF
- QuantStack Wan2.2 I2V A14B GGUF: https://huggingface.co/QuantStack/Wan2.2-I2V-A14B-GGUF
- QuantStack Wan2.2 T2V A14B GGUF: https://huggingface.co/QuantStack/Wan2.2-T2V-A14B-GGUF
- Comfy LTX-2.3 docs: https://docs.comfy.org/tutorials/video/ltx/ltx-2-3
- LTX-2.3 model card: https://huggingface.co/Lightricks/LTX-2.3
- Comfy Qwen-Image-2512 docs: https://docs.comfy.org/tutorials/image/qwen/qwen-image-2512
- Comfy Qwen-Image-Edit-2511 docs: https://docs.comfy.org/tutorials/image/qwen/qwen-image-edit-2511
- Unsloth Qwen-Image-2512 GGUF: https://huggingface.co/unsloth/Qwen-Image-2512-GGUF
- Unsloth Qwen-Image-Edit-2511 GGUF: https://huggingface.co/unsloth/Qwen-Image-Edit-2511-GGUF
- Comfy FLUX.2 Klein docs: https://docs.comfy.org/tutorials/flux/flux-2-klein
- city96 FLUX.2 Dev GGUF: https://huggingface.co/city96/FLUX.2-dev-gguf
- city96 ComfyUI-GGUF nodes: https://github.com/city96/ComfyUI-GGUF
- Comfy FLUX.1 ControlNet docs: https://docs.comfy.org/tutorials/flux/flux-1-controlnet
- Comfy Stable Audio 3 docs: https://docs.comfy.org/tutorials/audio/stable-audio/stable-audio-3
- Comfy ACE-Step 1.5 docs: https://docs.comfy.org/tutorials/audio/ace-step/ace-step-v1-5
- ACE-Step-ComfyUI: https://github.com/ace-step/ACE-Step-ComfyUI
- ComfyUI-Foundation-1: https://github.com/Saganaki22/ComfyUI-Foundation-1
- ComfyUI-MMAudio: https://github.com/kijai/ComfyUI-MMAudio
- ComfyUI-Frame-Interpolation: https://github.com/Fannovel16/ComfyUI-Frame-Interpolation
- ComfyUI-VideoHelperSuite: https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite
- ComfyUI-Florence2 registry/GitHub: https://registry.comfy.org/nodes/comfyui-florence2 and https://github.com/kijai/ComfyUI-Florence2
- audio-separation-nodes-comfyui: https://github.com/christian-byrne/audio-separation-nodes-comfyui
- Lumina Image 2.0 Comfy support: https://github.com/Alpha-VLLM/Lumina-Image-2.0
- SkyReels/Hunyuan Comfy conversion: https://huggingface.co/Kijai/SkyReels-V1-Hunyuan_comfy
- OmniGen Comfy node: https://github.com/1038lab/ComfyUI-OmniGen

- Comfy Krea-2 docs: https://docs.comfy.org/tutorials/image/krea/krea-2
- Comfy ERNIE-Image docs: https://docs.comfy.org/tutorials/image/ernie-image/ernie-image
- Comfy Anima docs: https://docs.comfy.org/tutorials/image/anima/anima
- ComfyUI Chatterbox node packs: https://github.com/filliptm/ComfyUI_Fill-ChatterBox and https://github.com/wildminder/ComfyUI-Chatterbox
- Comfy Z-Image docs: https://docs.comfy.org/tutorials/image/z-image/z-image and https://docs.comfy.org/tutorials/image/z-image/z-image-turbo

## 18. Implementation work log

This work log is historical scaffold evidence only. It does not override the current code-derived parity report at the top of this file. Every block below remains **not done on spec** until the matching function row above is updated with real `ModelPlugin.generate()` artifact proof from the required local runtime.

### 2026-06-27 Comfy model cache reuse block

- Current parity status: CACHE PREP ONLY, NOT DONE ON SPEC. This copied/reused local model files but certifies zero UI functions; every affected model still needs registry reconciliation, owned runtime startup, full UI-to-workflow mapping, and real `ModelPlugin.generate()` artifact tests.

- Cache preparation only: copied missing model artifacts from `/home/user/Documents/Comfy/ComfyUI/models/` into the owned Slopperly Comfy cache at `.slopperly/runtimes/ComfyUI/models/` with `rsync -a --ignore-existing --partial`.
- Evidence: rsync copied 76 regular files and 4 symlinks, `204.25G` literal data, preserving equivalent Comfy model subfolders.
- Evidence: a follow-up `rsync -a --ignore-existing --dry-run --stats` reported 0 created files and 0 regular files transferred.
- Evidence: owned cache size after copy is `202G`; key copied assets include LTX 2.3 GGUF/FP8/NVFP4, LTX LoRA/VAE/text assets, and Wan2.2 I2V A14B high/low Q5 files.
- Not done - install/test required: this copy does not certify any dropdown entry or workflow. Each model still needs model-registry reconciliation where missing plus real `ModelPlugin.generate()` artifact tests through owned ComfyUI.

### 2026-06-27 indexed Comfy media schema block

- Current parity status: SCAFFOLD ONLY, NOT DONE ON SPEC. Indexed patching is required by Qwen edit, OmniGen, and LTX staged/multi workflows, but none counts until real UI selectors map to real Comfy uploads and produce real RTX artifacts.

- Scaffold only: Comfy workflow-pack schemas can now patch indexed scalar fields such as `image_prompts[1]`.
- Scaffold only: Comfy workflow-pack schemas can now upload indexed media fields such as `images[0]`, `images[1]`, and `middle_images_paths[0].path`.
- Evidence: `tests/integration/test_comfy_workflow_runner.py` covers the indexed field path against a local fake Comfy server under the runtime network guard.
- Not done - install/test required: real Qwen/OmniGen/LTX multi-reference workflow packs, owned Comfy runtime execution, model downloads, and GPU artifact certification.

### 2026-06-27 GPU certification harness block

- Current parity status: TEST INFRASTRUCTURE ONLY, NOT DONE ON SPEC. The harness records evidence but does not make a model done; each function needs its own real local-runtime PASS artifact, and stale or alias-tainted records must be marked non-PASS.

- Scaffold only: `tests/gpu/` now contains pytest GPU artifact tests for the currently registered validation commands.
- Scaffold only: GPU tests write JSON certification records under `.slopperly/certification/<profile>/`; only `PASS` with a real artifact certifies a dropdown entry, every non-PASS record means action is still required.
- Scaffold only: Dropdown certification now requires a PASS record for the exact logical model/profile and a real artifact file.
- Evidence: unit coverage validates discovered PASS records and rejected non-PASS records.
- Not done - install/test required: tests have not been run against live RTX 4090 runtimes in this block; Qwen/Wan workflow packs and plugin-path migrations remain incomplete.

### 2026-06-27 Comfy upload endpoint schema block

- Current parity status: SCAFFOLD ONLY, NOT DONE ON SPEC. Upload endpoint support is only plumbing for image/video/audio strip inputs; it proves no button until each plugin uploads real media to owned ComfyUI and returns a validated artifact.

- Scaffold only: Comfy workflow upload schema targets can declare `endpoint`, `form_field`, and `type_field` for image/audio/video-style upload routes.
- Scaffold only: Workflow validation rejects absolute upload endpoint URLs; endpoints must be relative Comfy paths.
- Evidence: `tests/integration/test_comfy_workflow_runner.py` covers video-file upload through Comfy's real `/upload/image` endpoint with multipart field `image`; `tests/unit/test_comfy_workflow_security.py` covers invalid upload endpoints.
- Not done - install/test required: real audio/video Comfy workflow packs and GPU artifact tests have not run against owned ComfyUI.

### 2026-06-27 Faster Whisper vLLM STT block

- Current parity status: `text/faster_whisper_transcribe.py` is DONE ON SPEC for the `smoke_16gb` profile. The existing transcribe UI/plugin path has real local `FasterWhisperTranscribePlugin.generate()` evidence through a local vLLM server, exact local Whisper large-v3-turbo model files, a known-speech fixture with expected-word validation, dropdown PASS certification, and no remaining production blocker for that certified profile.

- Implemented: `slopperly/runtime/vllm/stt_client.py` now resolves a single local vLLM served model ID from `/v1/models` for the default `openai/whisper-large-v3-turbo` profile, preserving explicit non-default model IDs.
- Implemented: `slopperly/runtime/vllm/supervisor.py` can now reproduce the certified Whisper launch profile with `--max-num-batched-tokens`; the first direct launch failed with `Chunked MM input disabled but max_tokens_per_mm_item (1500) is larger than max_num_batched_tokens (448)`, and the implemented `2048` budget fixed that codable vLLM configuration issue.
- Implemented: `slopperly/config/models.yaml` records `vllm_whisper_large_v3_turbo_stt` defaults for `served_model_name=openai/whisper-large-v3-turbo`, `max_num_batched_tokens=2048`, `gpu_memory_utilization=0.35`, `max_num_seqs=1`, and eager mode.
- Implemented: `tests/fixtures/vllm_stt_hello_local_world.wav` is a real local speech WAV fixture generated with ffmpeg `flite`, 16 kHz mono, 2.760000s, with the spoken phrase `Hello local world. This is a whisper test.`
- Implemented: `tests/gpu/test_vllm_stt.py` now uses the committed known-speech fixture, calls `FasterWhisperTranscribePlugin.generate()`, validates the source audio, validates non-empty text, and asserts the expected words `hello`, `local`, `world`, `whisper`, and `test` appear in the VSE text-strip transcript.
- Evidence: `.slopperly/vllm-venv/bin/python -m slopperly.models.download --model vllm_whisper_large_v3_turbo_stt --cache-root .slopperly/runtimes/vllm --profile smoke_16gb --accept-licenses` downloaded the Whisper snapshot into `.slopperly/runtimes/vllm/models/vllm/openai/whisper-large-v3-turbo`.
- Evidence: owned Whisper model files are present under that snapshot (`1.6G`), including `config.json`, `generation_config.json`, `preprocessor_config.json`, tokenizer files, and `model.safetensors` (`1617824864` bytes).
- Evidence: local vLLM was started on `http://127.0.0.1:8090` with `python -m vllm.entrypoints.openai.api_server --model /home/user/Documents/Slopperly/.slopperly/runtimes/vllm/models/vllm/openai/whisper-large-v3-turbo --served-model-name openai/whisper-large-v3-turbo --allowed-local-media-path /home/user/Documents/Slopperly --download-dir /home/user/Documents/Slopperly/.slopperly/runtimes/vllm --max-num-batched-tokens 2048 --gpu-memory-utilization 0.35 --max-num-seqs 1 --enforce-eager`.
- Evidence: vLLM logs showed architecture `WhisperForConditionalGeneration`, task `transcription`, max model length 448, checkpoint size `1.51 GiB`, model loading at `1.51 GiB` GPU memory, encoder cache budget 2048 tokens, `35,716` GPU KV-cache tokens, and `/v1/models` reporting `openai/whisper-large-v3-turbo` with `max_model_len` 448.
- Evidence: a direct `VllmSttClient.transcribe()` probe for `tests/fixtures/vllm_stt_hello_local_world.wav` returned text `Hello, local world, this is a whisper test.` with one segment spanning 2.760000s.
- Evidence: `SLOPPERLY_VLLM_URL=http://127.0.0.1:8090 python -m pytest tests/gpu/test_vllm_stt.py --device cuda --profile smoke_16gb --runtime-timeout 30 -s` passed 1 test through `FasterWhisperTranscribePlugin.generate()`, inserting one subtitle strip on channel 2 with transcript `Hello, local world, this is a whisper test.`
- Evidence: `.slopperly/certification/smoke_16gb/vllm_whisper_large_v3_turbo_stt.json` is PASS for `.slopperly/gpu-artifacts/smoke_16gb/vllm_whisper_large_v3_turbo_stt/transcript.txt`; the record includes source-audio validation as WAV mono 16 kHz, 2.760000s, RMS `4883.239675826595`, and expected-word text validation.
- Evidence: focused tests passed with `python -m pytest tests/unit/test_local_runtime_clients.py tests/integration/test_local_plugin_paths.py::LocalPluginPathTests::test_faster_whisper_generate_uses_vllm_plugin_path -q` reporting 9 passed.
- Evidence: `python -m slopperly.audit.model_registry`, `python -m slopperly.audit.workflow_packs`, `python -m pytest tests/unit tests/integration`, and `python -m slopperly.audit.no_cloud` passed after this certification; the full unit/integration suite reports 132 passed, and workflow-pack audit validates 47 packs.
- Evidence: `python -m slopperly.audit.dropdown_certification --profile smoke_16gb --report-only` reports `PASS vllm_whisper_large_v3_turbo_stt`; dropdown certification now reports 13 passed and 27 blocked entries.

### 2026-06-27 Marlin video caption vLLM block

- Current parity status: `text/marlin_video_captions.py` is DONE ON SPEC for the `smoke_16gb` profile. Caption mode and Find mode have real local `MarlinVideoCaptionsPlugin.generate()` evidence through a local vLLM server, exact local Qwen2.5-VL model files, dropdown PASS certification, and no remaining production blocker for that certified profile.

- Implemented: `.slopperly/vllm-venv` was installed with `vllm==0.23.0`, `torch==2.11.0`, CUDA 13 dependencies, `av==17.1.0`, and the `vllm[audio]` install target using `python -m slopperly.runtime.vllm.install --venv .slopperly/vllm-venv --extras audio`.
- Implemented: `vllm_video_caption_vlm` is registered in `slopperly/config/models.yaml` with local runtime settings for `Qwen/Qwen2.5-VL-7B-Instruct`: served model name, `max_model_len=16384`, `gpu_memory_utilization=0.82`, `cpu_offload_gb=6`, `max_num_seqs=1`, two sampled video frames, `backend=pyav`, zero multimodal processor cache, and eager mode.
- Implemented: `slopperly/runtime/vllm/supervisor.py` can now reproduce the certified multimodal launch profile, including `--served-model-name`, `--download-dir`, max length, CPU offload, media IO kwargs, multimodal limits, and eager mode.
- Implemented: `slopperly/runtime/vllm/vlm_client.py` resolves a single served model ID from `/v1/models` when the default Qwen model is served from a local path, preserving explicit user-configured model IDs.
- Implemented: `MarlinVideoCaptionsPlugin.generate()` keeps the existing Blender UI and output behavior while using a smaller real FAST token budget (`160`) for short local vLLM caption runs.
- Implemented: `tests/fixtures/video_caption_smoke.mp4` is a real 3.000000s H.264 MP4 fixture, 320x240, 8fps, 24 frames, with visible `SLOPPERLY VIDEO`, red block, and green block content for caption/find validation.
- Implemented: `tests/gpu/test_video_caption_vlm.py` now exercises both Marlin Caption mode and Find mode through the plugin path, validating VSE text-strip output plus `MARLIN:` timeline marker insertion.
- Evidence: `.slopperly/vllm-venv/bin/python -m slopperly.models.download --model vllm_video_caption_vlm --cache-root .slopperly/runtimes/vllm --profile smoke_16gb --accept-licenses` downloaded the Qwen2.5-VL snapshot into `.slopperly/runtimes/vllm/models/vllm/Qwen/Qwen2.5-VL-7B-Instruct`.
- Evidence: owned Qwen2.5-VL model files are present under that snapshot (`16G`), including `config.json`, `chat_template.json`, `preprocessor_config.json`, tokenizer files, `model.safetensors.index.json`, and five safetensors shards with sizes `3900233256`, `3864726320`, `3864726424`, `3864733680`, and `1089994880` bytes.
- Evidence: local vLLM was started on `http://127.0.0.1:8090` with `python -m vllm.entrypoints.openai.api_server --model /home/user/Documents/Slopperly/.slopperly/runtimes/vllm/models/vllm/Qwen/Qwen2.5-VL-7B-Instruct --served-model-name Qwen/Qwen2.5-VL-7B-Instruct --allowed-local-media-path /home/user/Documents/Slopperly --max-model-len 16384 --gpu-memory-utilization 0.82 --cpu-offload-gb 6 --max-num-seqs 1 --limit-mm-per-prompt '{"video":{"count":1,"num_frames":2,"width":448,"height":448},"image":0}' --media-io-kwargs '{"video":{"num_frames":2,"backend":"pyav"}}' --mm-processor-cache-gb 0 --enforce-eager`.
- Evidence: vLLM logs showed architecture `Qwen2_5_VLForConditionalGeneration`, dtype `torch.bfloat16`, `max_model_len=16384`, checkpoint size `15.45 GiB`, model loading at `9.55 GiB` GPU memory, `6.08` GiB CPU-offloaded parameters, `53,856` GPU KV cache tokens, and `/v1/models` reporting `Qwen/Qwen2.5-VL-7B-Instruct` with `max_model_len` 16384.
- Evidence: `SLOPPERLY_VLLM_URL=http://127.0.0.1:8090 python -m pytest tests/gpu/test_video_caption_vlm.py --device cuda --profile smoke_16gb --runtime-timeout 30 -s` passed 1 test in 85.51s through `MarlinVideoCaptionsPlugin.generate()`.
- Evidence: the passing run logged a real caption request for `tests/fixtures/video_caption_smoke.mp4` with `max_new_tokens=160`, inserted two event text strips plus the scene overview strip, then ran Find mode for `the SLOPPERLY VIDEO title text` and inserted a marker at frame 129.
- Evidence: `.slopperly/certification/smoke_16gb/vllm_video_caption_vlm.json` is PASS for `.slopperly/gpu-artifacts/smoke_16gb/vllm_video_caption_vlm/video_captions.txt`; the artifact contains caption text for the red and green blocks and `MARLIN: the SLOPPERLY VIDEO title text @ 129`.
- Evidence: focused tests passed with `python -m pytest tests/unit/test_local_runtime_clients.py tests/unit/test_runtime_supervisors.py tests/unit/test_model_download_and_doctor.py -q` reporting 20 passed, plus `python -m pytest tests/integration/test_local_plugin_paths.py::LocalPluginPathTests::test_marlin_video_captions_uses_vllm_vlm_plugin_path -q` reporting 1 passed.
- Evidence: `python -m slopperly.audit.model_registry`, `python -m slopperly.audit.workflow_packs`, `python -m pytest tests/unit tests/integration`, `python -m slopperly.audit.no_cloud`, and `python -m slopperly.audit.dropdown_certification --profile smoke_16gb --report-only` passed after this certification; dropdown certification reports 12 passed and 28 blocked entries.

### 2026-06-27 MoviiGen llama.cpp prompt rewrite block

- Current parity status: `text/moviigen_rewriter.py` is DONE ON SPEC for the `smoke_16gb` profile. The existing prompt-rewrite UI/plugin path has real local `MoviiGenRewriterPlugin.generate()` evidence through a local llama.cpp server, exact local Qwen2.5 7B Q5 GGUF model file, dropdown PASS certification, and no remaining production blocker for that certified prompt-rewriter profile.

- Implemented: `slopperly/runtime/llamacpp/install.py` now selects the actual release asset name `llama-b9803-bin-ubuntu-cuda13-x64.tar.gz` for the requested `ubuntu-x64-cuda13` artifact by matching the requested platform/CUDA tokens instead of requiring one fixed substring order.
- Implemented: `slopperly/runtime/llamacpp/supervisor.py` can reproduce the certified CUDA launch profile with `--ctx-size 60000`, `--n-predict 30000`, `--n-gpu-layers 999`, `--flash-attn on`, and `--parallel 1`.
- Implemented: `slopperly/runtime/llamacpp/client.py` now probes llama.cpp `/props`, records the served context length, and adds an explicit `context_fallback` diagnostic when the server caps the requested 60k context instead of silently claiming the request was honored.
- Implemented: `models_plugins/text/moviigen_rewriter.py` preserves the existing prompt field and text output path while including llama.cpp usage and context-fallback diagnostics in `inputs.usage_note`.
- Implemented: `slopperly/config/models.yaml` records the certified `llamacpp_prompt_rewriter` defaults: Qwen2.5 7B Instruct Q5 GGUF, temperature `0.7`, context length `60000`, max new tokens `30000`, GPU layers `999`, flash attention `on`, and one parallel slot.
- Evidence: `python -m slopperly.runtime.llamacpp.install --release b9803 --artifact ubuntu-x64-cuda13` installed the owned llama.cpp runtime after the asset-selection fix, launched the binary with `--help`, and wrote `.slopperly/runtimes/llamacpp-install-manifest.json` with the exact release asset URL.
- Evidence: `.slopperly/vllm-venv/bin/python -m slopperly.models.download --model llamacpp_prompt_rewriter --cache-root .slopperly/runtimes --profile smoke_16gb --accept-licenses` installed `.slopperly/runtimes/models/llamacpp/Qwen2.5-7B-Instruct-Q5_K_M.gguf` from `bartowski/Qwen2.5-7B-Instruct-GGUF`.
- Evidence: owned runtime files are present: `.slopperly/runtimes/llama.cpp` is `249M`, `.slopperly/runtimes/llama.cpp/llama-b9803/llama-server` passed its launch check, and `.slopperly/runtimes/models/llamacpp/Qwen2.5-7B-Instruct-Q5_K_M.gguf` is `5.1G`.
- Evidence: local llama.cpp was started on `http://127.0.0.1:8092` with `/home/user/Documents/Slopperly/.slopperly/runtimes/llama.cpp/llama-b9803/llama-server --model /home/user/Documents/Slopperly/.slopperly/runtimes/models/llamacpp/Qwen2.5-7B-Instruct-Q5_K_M.gguf --ctx-size 60000 --n-predict 30000 --n-gpu-layers 999 --flash-attn on --parallel 1`.
- Evidence: llama.cpp loaded on CUDA with the NVIDIA RTX 4090 Laptop GPU, served `/health`, `/props`, `/slots`, and `/v1/models`, and runtime GPU use after load was 8926 MiB of 16376 MiB.
- Evidence: the Qwen GGUF reports `n_ctx_train=32768`; llama.cpp warned that the requested slot context exceeded the training context and capped the served slot to `n_ctx=32768`. This is recorded by the plugin diagnostics as the required supported fallback, not treated as an unresolved blocker for the certified Qwen2.5 Q5 profile.
- Evidence: a direct local `LlamaCppClient.chat()` probe returned a non-empty rewrite for `a quiet train station at midnight with one service robot` and diagnostics containing `requested_context_length: 60000`, `requested_max_new_tokens: 30000`, `served_context_length: 32768`, and token usage.
- Evidence: `SLOPPERLY_LLAMACPP_URL=http://127.0.0.1:8092 python -m pytest tests/gpu/test_llamacpp_prompt_rewrite.py --device cuda --profile smoke_16gb --runtime-timeout 30 -s` passed 1 test through `MoviiGenRewriterPlugin.generate()`, producing a real prompt rewrite that preserved the expected concepts `train`, `station`, and `robot`.
- Evidence: `.slopperly/certification/smoke_16gb/llamacpp_prompt_rewriter.json` is PASS for `.slopperly/gpu-artifacts/smoke_16gb/llamacpp_prompt_rewriter/prompt_rewrite.txt`; the record includes `context_fallback_recorded: true` and the plugin usage note says llama.cpp served `n_ctx=32768` after Slopperly requested `n_ctx=60000`.
- Evidence: focused tests passed for llama.cpp installer asset selection, client diagnostics, supervisor launch defaults, and MoviiGen plugin-path integration.
- Evidence: `python -m pytest tests/unit tests/integration -q` reports 133 passed after this certification.
- Evidence: `python -m slopperly.audit.model_registry`, `python -m slopperly.audit.workflow_packs`, and `python -m slopperly.audit.no_cloud` passed after this certification; model registry validates 40 entries and workflow-pack audit validates 47 packs.
- Evidence: `python -m slopperly.audit.dropdown_certification --profile smoke_16gb --report-only` reports `PASS llamacpp_prompt_rewriter`; dropdown certification now reports 14 passed and 26 blocked entries.

### 2026-06-27 Florence2 Comfy workflow block

- Current parity status: `text/florence2.py` is DONE ON SPEC for the `smoke_16gb` profile. Caption mode and IDEOGRAM4 JSON mode have real owned-Comfy `Florence2Plugin.generate()` artifacts, exact Florence-2 Large local model files, dropdown PASS certification, and no remaining production blocker for that certified caption/OCR profile.

- Implemented: `text/florence2.py` routes Florence task inference through the local Comfy workflow pack instead of direct Transformers/PyTorch loading, while preserving the existing image input, task-mode behavior, and text return shape.
- Implemented: `florence2_caption_ocr` workflow pack now routes `Florence2Run` caption and JSON outputs through `PreviewAny` output nodes so owned Comfy accepts the graph as a real output-producing workflow.
- Implemented: Comfy workflow output collection recursively reads nested `ui`/`result` history payloads, which matches the real `PreviewAny` output shape for text and JSON.
- Implemented: `models_plugins/text/florence2.py` normalizes real Florence bbox and quad JSON variants, including nested single-box lists, before IDEOGRAM4 geometry conversion; the first real IDEOGRAM4 attempt exposed this as a codable plugin data-shape issue.
- Implemented: IDEOGRAM4 palette extraction no longer requires `numpy`; it uses the image/Pillow data already available to the plugin path.
- Evidence: `.slopperly/runtimes/ComfyUI/custom_nodes/florence2` is installed and owned Comfy `/object_info` on `http://127.0.0.1:8190` exposes `LoadImage`, `DownloadAndLoadFlorence2Model`, `Florence2Run`, and `PreviewAny`.
- Evidence: local Florence-2 Large files are present under `.slopperly/runtimes/ComfyUI/models/LLM/Florence-2-large/`, including `model.safetensors` (`1.5G`), `config.json`, local modeling/processing files, tokenizer files, and processor files.
- Evidence: `tests/fixtures/florence2_caption.png` is a real 512x320 RGB fixture with visible `SLOPPERLY LOCAL TEST` text, a red block, a green circle, and colored local test shapes.
- Evidence: `SLOPPERLY_COMFYUI_URL=http://127.0.0.1:8190 python -m pytest tests/gpu/test_florence2_caption.py --device cuda --profile smoke_16gb --runtime-timeout 30 -s` passed 1 test in 12.57s through `Florence2Plugin.generate()`, running both caption mode and IDEOGRAM4 mode against owned Comfy.
- Evidence: the passing caption artifact says the image contains a red block, green circle, yellow pencil, white background, and the blue text `SLOPPERLY LOCAL TEST`.
- Evidence: `.slopperly/certification/smoke_16gb/florence2_caption_ocr.json` is PASS for `.slopperly/gpu-artifacts/smoke_16gb/florence2_caption_ocr/florence2_manifest.json`; the manifest points to `caption.txt` and `ideogram4.json`.
- Evidence: certification validation matched caption concepts `block`, `blue`, `circle`, `green`, `local`, `red`, `slopperly`, `test`, and `text`; IDEOGRAM4 JSON validated required keys, two compositional elements, and text/OCR evidence from `local`, `slopperly`, `test`, and `text`.
- Evidence: focused integration coverage now verifies the real output-node contract and the plugin path against loopback Comfy: `test_comfy_workflow_runner.py::ComfyWorkflowRunnerIntegrationTests::test_florence_pack_collects_text_and_json_history_outputs` and `test_local_plugin_paths.py::LocalPluginPathTests::test_florence2_caption_uses_comfy_plugin_path`.
- Evidence: `python -m slopperly.audit.dropdown_certification --profile smoke_16gb --report-only` reports `PASS florence2_caption_ocr`; dropdown certification now reports 15 passed and 25 blocked entries.

### 2026-06-27 BiRefNet Comfy workflow block

- Current parity status: `image/birefnet.py` is NOT DONE ON SPEC. Needs owned ComfyUI with RMBG/BiRefNet nodes/model files, selected-image UI mapping, and a real same-size PNG with alpha from `BiRefNetPlugin.generate()`.

- Scaffold only: `image/birefnet.py` now routes background removal through the local Comfy workflow gateway instead of direct Torch/Transformers inference in the add-on process.
- Scaffold only: `birefnet_rmbg` workflow pack is committed with API/editable workflow JSON, schema, model manifest, test payload, and README.
- Scaffold only: `comfyui_rmbg` is pinned in `slopperly/runtime/comfy/nodes.lock.yaml` with exact `BiRefNetRMBG`/`RMBG` node classes from `1038lab/ComfyUI-RMBG`.
- Scaffold only: `birefnet_rmbg` is registered in `slopperly/config/models.yaml` with legacy alias `ZhengPeng7/BiRefNet_HR`.
- Evidence: integration coverage calls `BiRefNetPlugin.load()` and `generate()` against a loopback fake Comfy server under the local-network guard and verifies the patched `LoadImage -> BiRefNetRMBG -> SaveImage` graph.
- Not done - install/test required: real RTX 4090 BiRefNet artifact certification requires owned ComfyUI, downloaded `BiRefNet-HR` artifacts, and the pinned RMBG node pack installed.

### 2026-06-27 Local image VSR Comfy workflow block

- Current parity status: `image/maxine_vsr.py` / Local Image VSR is NOT DONE ON SPEC. Needs owned Comfy upscale nodes and model files, selected-image and target-resolution UI mapping, and a real upscaled PNG with expected dimensions.

- Scaffold only: `image/maxine_vsr.py` now routes the legacy image super-resolution plugin through the local Comfy workflow gateway instead of NVIDIA Maxine/nvvfx in the add-on process.
- Scaffold only: `local_image_vsr_upscale` workflow pack is committed with API/editable workflow JSON, schema, model manifest, smoke payload, README, and an 8x6 PPM input fixture.
- Scaffold only: Comfy core upscale node classes `UpscaleModelLoader`, `ImageUpscaleWithModel`, and `ImageScale` are asserted in `slopperly/runtime/comfy/nodes.lock.yaml`.
- Scaffold only: `local_image_vsr_upscale` is registered in `slopperly/config/models.yaml` with legacy alias `nvidia/maxine-vsr` and artifact source `ai-forever/Real-ESRGAN`, file `RealESRGAN_x4.pth`.
- Evidence: integration coverage calls `MaxineVSRPlugin.load()` and `generate()` against a loopback fake Comfy server under the local-network guard and verifies the patched `LoadImage -> UpscaleModelLoader -> ImageUpscaleWithModel -> ImageScale -> SaveImage` graph.
- Evidence: `python -m slopperly.models.download --profile smoke_16gb --dry-run --report-only` plans 10 local artifact entries with 0 download-plan blockers, including `ai-forever/Real-ESRGAN/RealESRGAN_x4.pth`.
- Not done - install/test required: real RTX 4090 local image VSR artifact certification requires owned ComfyUI running with core upscale nodes and `RealESRGAN_x4.pth` installed in `models/upscale_models/`.

### 2026-06-27 Local video VSR Comfy workflow block

- Current parity status: `video/maxine_vsr_video.py` / Local Video VSR is NOT DONE ON SPEC. Needs owned Comfy VideoHelperSuite/upscale model install, video-strip and target-resolution UI mapping, audio passthrough verification, and a real MP4 with size/fps/duration validated.

- Scaffold only: `video/maxine_vsr_video.py` now routes the legacy video super-resolution plugin through the local Comfy workflow gateway instead of NVIDIA Maxine/nvvfx in the add-on process.
- Scaffold only: `local_video_vsr_upscale` workflow pack is committed with API/editable workflow JSON, schema, model manifest, smoke payload, README, and a 1-second MP4 fixture with audio.
- Scaffold only: Comfy workflow artifact collection now recognizes VideoHelperSuite `gifs` outputs, which are used for MP4 results from `VHS_VideoCombine`.
- Scaffold only: `local_video_vsr_upscale` is registered in `slopperly/config/models.yaml` with legacy alias `nvidia/maxine-vsr-video` and artifact source `ai-forever/Real-ESRGAN`, file `RealESRGAN_x4.pth`.
- Scaffold only: `pytest.ini` now keeps pytest collection rooted at `tests`, allowing the acceptance command `python -m pytest tests/unit` to run outside Blender without importing `bpy`.
- Evidence: integration coverage calls `MaxineVSRVideoPlugin.load()` and `generate()` against a loopback fake Comfy server under the local-network guard and verifies video upload through Comfy's `/upload/image` endpoint, source-fps patching, `VHS_LoadVideo -> UpscaleModelLoader -> ImageUpscaleWithModel -> ImageScale -> VHS_VideoCombine`, H.264 MP4 format, and source-audio wiring.
- Evidence: `python -m pytest tests/unit` passes 40 tests.
- Evidence: `python -m slopperly.audit.workflow_packs` validates 5 committed Comfy workflow packs including `local_video_vsr_upscale`.
- Not done - install/test required: real RTX 4090 local video VSR artifact certification requires owned ComfyUI running with VideoHelperSuite, core upscale nodes, and `RealESRGAN_x4.pth` installed in `models/upscale_models/`.

### 2026-06-27 Stem Splitter Comfy workflow block

- Current parity status: the certified four-stem path of `audio/stem_split.py` is DONE ON SPEC for the `smoke_16gb` profile. It has a real owned-Comfy `StemSplitterPlugin.generate()` multi-stem artifact, exact Hybrid Demucs checkpoint cache, dropdown PASS certification, and no remaining production blocker for the certified four-stem profile. The old six-stem `htdemucs_6s` option remains blocked with a concrete diagnostic until a separate pinned six-stem local workflow passes artifact certification.

- Implemented: `audio/stem_split.py` routes the legacy `StemSplitter` plugin through the local Comfy workflow gateway instead of direct `demucs_onnx` execution in the add-on process.
- Implemented: the dedicated `sequencer.stem_split` operator renders the selected strip to WAV and calls `StemSplitterPlugin.generate()`, preserving the existing stem insertion behavior while using the same local runtime path.
- Implemented: `audio_stem_split_demucs` workflow pack is committed with API/editable workflow JSON, schema, model manifest, smoke payload, README, and a 1-second 44.1 kHz stereo WAV fixture.
- Implemented: the workflow uses `LoadAudio -> AudioSeparation -> SaveAudio` x4, preserving selected audio/video strip input, chunk fade shape, chunk length, chunk overlap, selected-stem filtering, and the existing `MULTI_STEM` return shape.
- Implemented: Comfy core audio nodes `LoadAudio` and `SaveAudio` are asserted in `slopperly/runtime/comfy/nodes.lock.yaml`, and the audio-separation node pack lock records exact Comfy class keys such as `AudioSeparation`.
- Implemented: `audio_stem_split_demucs` is registered in `slopperly/config/models.yaml` with legacy alias `StemSplitter` and artifact source `paobukaidecha/hdemucs_high_trained`, file `hdemucs_high_trained.pt`.
- Implemented: `slopperly.models.download` mirrors model entries with `torchaudio_asset_key` into Torchaudio's hub cache, so generation does not need a network download when `HDEMUCS_HIGH_MUSDB_PLUS.get_model()` runs inside the Comfy node.
- Evidence: `/home/user/Documents/Slopperly/.slopperly/runtimes/comfy-venv/bin/python -m slopperly.models.download --model audio_stem_split_demucs --cache-root .slopperly/runtimes/ComfyUI --accept-licenses` downloaded `hdemucs_high_trained.pt` into `.slopperly/runtimes/ComfyUI/models/torchaudio/` and mirrored it to `/home/user/.cache/torch/hub/torchaudio/models/hdemucs_high_trained.pt`.
- Evidence: both Hybrid Demucs files are present and `320M`: `.slopperly/runtimes/ComfyUI/models/torchaudio/hdemucs_high_trained.pt` and `/home/user/.cache/torch/hub/torchaudio/models/hdemucs_high_trained.pt`.
- Evidence: owned Slopperly ComfyUI on `http://127.0.0.1:8190` exposes `LoadAudio`, `AudioSeparation`, `AudioCombine`, and `SaveAudio` in `/object_info`.
- Evidence: `SLOPPERLY_COMFYUI_URL=http://127.0.0.1:8190 python -m pytest tests/gpu/test_stem_split.py --device cuda --profile smoke_16gb --runtime-timeout 30 -s` passed 1 test in 2.22s through `StemSplitterPlugin.generate()`.
- Evidence: Comfy/Torchaudio logged `The local file (/home/user/.cache/torch/hub/torchaudio/models/hdemucs_high_trained.pt) exists. Skipping the download.` and executed the prompt in 1.10s.
- Evidence: `.slopperly/certification/smoke_16gb/audio_stem_split_demucs.json` is PASS for `.slopperly/gpu-artifacts/smoke_16gb/audio_stem_split_demucs/stems_manifest.json` with bass, drums, other, and vocals artifacts.
- Evidence: `ffprobe` validates all four generated stem artifacts as FLAC stereo 44.1 kHz, 1.000000s: `bass_stem_split_source.flac` (`38557` bytes), `drums_stem_split_source.flac` (`38266` bytes), `other_stem_split_source.flac` (`43981` bytes), and `vocals_stem_split_source.flac` (`29550` bytes).
- Evidence: integration coverage calls `StemSplitterPlugin.load()` and `generate()` against a loopback fake Comfy server under the local-network guard and verifies `LoadAudio -> AudioSeparation -> SaveAudio`, four audio outputs, and the existing `MULTI_STEM` result shape.
- Evidence: workflow-runner integration coverage verifies the committed audio pack uploads the WAV fixture and collects four Comfy audio artifacts.
- Evidence: `python -m slopperly.audit.model_registry`, `python -m slopperly.audit.workflow_packs`, `python -m pytest tests/unit tests/integration`, `python -m slopperly.audit.no_cloud`, and `python -m slopperly.audit.dropdown_certification --profile smoke_16gb --report-only` passed after this certification; dropdown certification reports 6 passed and 34 blocked entries.

### 2026-06-27 MMAudio Comfy workflow block

- Current parity status: `audio/mmaudio.py` is DONE ON SPEC for the `smoke_16gb` profile. It has a real owned-Comfy `MMAudioPlugin.generate()` WAV artifact, exact MMAudio model files, local BigVGAN cache, dropdown PASS certification, and no remaining production blocker for that certified profile.

- Implemented: `audio/mmaudio.py` routes the legacy `MMAudio` plugin through the local Comfy workflow gateway instead of direct Torch/Torchaudio/Librosa/MMAudio execution in the add-on process.
- Implemented: `mmaudio_video_to_audio` workflow pack is committed with API/editable workflow JSON, schema, model manifest, smoke payload, and README.
- Implemented: the workflow uses `VHS_LoadVideo -> MMAudioModelLoader -> MMAudioFeatureUtilsLoader -> MMAudioSampler -> SaveAudio`, preserving prompt, negative prompt, selected video strip, duration, steps, guidance, seed, mask-away-CLIP, and force-offload controls.
- Implemented: `MMAudioPlugin.generate()` patches a per-invocation `SaveAudio.filename_prefix` so repeated identical prompts still save a fresh Comfy output, then converts Comfy's FLAC save to a real `.wav` UI artifact before returning.
- Implemented: `mmaudio_video_to_audio` is registered in `slopperly/config/models.yaml` with legacy alias `MMAudio`, the four required `Kijai/MMAudio_safetensors` files, and an auxiliary source for the NVIDIA BigVGAN 44k snapshot.
- Implemented: `slopperly.models.download` and `slopperly.audit.model_registry` support `auxiliary_sources` so workflow-required local artifacts from a second Hugging Face repo can be planned without adding a fake dropdown entry.
- Implemented: MMAudio and Local Video VSR video uploads now use Comfy's real `/upload/image` endpoint with the `image` multipart field. Owned Comfy 0.26.0 does not expose a core `/upload/video` route, and direct testing confirmed `/upload/image` accepts MP4 inputs for VideoHelperSuite.
- Evidence: `/home/user/Documents/Slopperly/.slopperly/runtimes/comfy-venv/bin/python -m slopperly.models.download --model mmaudio_video_to_audio --cache-root .slopperly/runtimes/ComfyUI --accept-licenses` installed the MMAudio and BigVGAN files into the owned Comfy model folder.
- Evidence: owned model files are present at `.slopperly/runtimes/ComfyUI/models/mmaudio/mmaudio_large_44k_v2_fp16.safetensors` (`2061198424` bytes), `mmaudio_vae_44k_fp16.safetensors` (`610966060` bytes), `mmaudio_synchformer_fp16.safetensors` (`474981098` bytes), `apple_DFN5B-CLIP-ViT-H-14-384_fp16.safetensors` (`1973509450` bytes), and `models/mmaudio/nvidia/bigvgan_v2_44khz_128band_512x/bigvgan_generator.pt` (`489041291` bytes).
- Evidence: owned Slopperly ComfyUI was restarted on `http://127.0.0.1:8190` with API nodes disabled, CUDA 13 PyTorch, dynamic VRAM, `VHS_LoadVideo`, `MMAudioModelLoader`, `MMAudioFeatureUtilsLoader`, `MMAudioSampler`, `MMAudioVoCoderLoader`, and `SaveAudio` available in `/object_info`; the loader model lists included the exact committed MMAudio filenames.
- Evidence: `SLOPPERLY_COMFYUI_URL=http://127.0.0.1:8190 python -m pytest tests/gpu/test_mmaudio.py --device cuda --profile smoke_16gb --runtime-timeout 30 -s` passed 1 test in 3.18s through `MMAudioPlugin.generate()`.
- Evidence: Comfy loaded MotionFormer, BigVGAN, CLIP, MMAudio model weights, encoded 12 clip frames and 37 sync frames from the generated local 3s MP4 source, ran 8 flow-matching steps, and executed the prompt in 2.67s.
- Evidence: `.slopperly/certification/smoke_16gb/mmaudio_video_to_audio.json` is PASS for `.slopperly/gpu-artifacts/smoke_16gb/mmaudio_video_to_audio/2468_subtle_cloth_movement_quiet_room_tone_small_mechanical_hum_mmaudio.wav`, WAV mono 44.1 kHz, 1.509297s, 133198 bytes, non-silent RMS `151.36270703356507`.
- Evidence: integration coverage calls `MMAudioPlugin.load()` and `generate()` against a loopback fake Comfy server under the local-network guard and verifies Comfy `/upload/image` media upload, exact node/input patching, per-run save prefix patching, and WAV artifact return.
- Evidence: workflow-runner integration coverage verifies the committed `mmaudio_video_to_audio` pack uploads an MP4 fixture through Comfy's real upload endpoint and collects one Comfy audio artifact.
- Evidence: `python -m slopperly.audit.model_registry`, `python -m slopperly.audit.workflow_packs`, `python -m pytest tests/unit tests/integration`, `python -m slopperly.audit.no_cloud`, and `python -m slopperly.audit.dropdown_certification --profile smoke_16gb --report-only` passed after this MMAudio certification; at that point dropdown certification reported 5 passed and 35 blocked entries. The current certification summary above supersedes this historical count.

### 2026-06-27 Stable Audio 3 Comfy workflow block

- Current parity status: `audio/_stable_audio_3.py` is DONE ON SPEC for the `smoke_16gb` profile. It has a real owned-Comfy `StableAudio3Plugin.generate()` FLAC artifact, exact Stable Audio 3 Medium Base files, dropdown PASS certification, and no remaining production blocker for that certified profile.

- Implemented: `audio/_stable_audio_3.py` routes the legacy Stable Audio 3 plugin through the local Comfy workflow gateway instead of direct Torch/Torchaudio/stable-audio-tools execution and generation-time Hugging Face downloads in the add-on process.
- Implemented: `stable_audio_3_medium_base` workflow pack is committed with API/editable workflow JSON, schema, model manifest, smoke payload, and README.
- Implemented: the workflow uses `CheckpointLoaderSimple -> CLIPLoader -> CLIPTextEncode -> ConditioningStableAudio -> EmptyLatentAudio -> KSampler -> VAEDecodeAudio -> SaveAudio`, preserving prompt, negative prompt, duration, steps, guidance, seed, sampler, scheduler, and denoise.
- Implemented: `stable_audio_3_medium_base` is registered in `slopperly/config/models.yaml` with legacy alias `cocktailpeanut/stable-audio-3-medium-base`, exact `hf_file` downloads from `Comfy-Org/stable-audio-3`, and Comfy-visible target paths under `models/checkpoints` and `models/text_encoders`.
- Implemented: `slopperly/runtime/comfy/nodes.lock.yaml` asserts core Stable Audio node classes including `ConditioningStableAudio`, `EmptyLatentAudio`, and `VAEDecodeAudio`.
- Evidence: `/home/user/Documents/Slopperly/.slopperly/runtimes/comfy-venv/bin/python -m slopperly.models.download --model stable_audio_3_medium_base --cache-root .slopperly/runtimes/ComfyUI --accept-licenses` downloaded `stable_audio_3_medium_base.safetensors` and `t5gemma_b_b_ul2.safetensors` into the owned Comfy model folders.
- Evidence: owned Slopperly ComfyUI was restarted on `http://127.0.0.1:8190` with API nodes disabled, CUDA 13 PyTorch, dynamic VRAM, and Stable Audio nodes available in `/object_info`.
- Evidence: `SLOPPERLY_COMFYUI_URL=http://127.0.0.1:8190 python -m pytest tests/gpu/test_stable_audio_3.py --device cuda --profile smoke_16gb --runtime-timeout 30 -s` passed 1 test in 4.27s through `StableAudio3Plugin.generate()`.
- Evidence: Comfy loaded `SAT5GemmaModel`, `StableAudio3`, and `SA3AudioVAE` from the owned cache and executed the prompt in 3.99s.
- Evidence: `.slopperly/certification/smoke_16gb/stable_audio_3_medium_base.json` is PASS for `.slopperly/gpu-artifacts/smoke_16gb/stable_audio_3_medium_base/31415_warm_lo-fi_electric_piano_chords_soft_brushed_drums_rounded_bass_stable_audio_3.flac`.
- Evidence: `ffprobe` validates the generated artifact as FLAC, stereo, 44100 Hz, 2.043356s, 159996 bytes; the certification validator also recorded non-silent audio.
- Evidence: integration coverage calls `StableAudio3Plugin.load()` and `generate()` against a loopback fake Comfy server under the local-network guard and verifies exact node/input patching plus FLAC artifact collection.
- Evidence: workflow-runner integration coverage verifies the committed `stable_audio_3_medium_base` pack patches the graph and collects one Comfy audio artifact.

### 2026-06-27 ACE-Step 1.5 Comfy workflow block

- Current parity status: `audio/ace_step.py` is DONE ON SPEC for the `smoke_16gb` profile. It has a real owned-Comfy `AceStepPlugin.generate()` FLAC artifact, exact ACE-Step 1.5 XL Turbo model files, dropdown PASS certification, and no remaining production blocker for that certified profile.

- Implemented: `audio/ace_step.py` routes the legacy ACE-Step plugin through the local Comfy workflow gateway instead of direct Torch/Diffusers/Accelerate execution and generation-time Hugging Face model loading in the add-on process.
- Implemented: `ace_step_15_music` workflow pack is committed with API/editable workflow JSON, schema, model manifest, smoke payload, and README.
- Implemented: the workflow uses `UNETLoader -> ModelSamplingAuraFlow -> KSampler -> VAEDecodeAudio -> SaveAudio` plus `DualCLIPLoader -> TextEncodeAceStepAudio1.5`, preserving prompt/tags, lyrics, duration, steps, guidance, BPM, key, time signature, and seed.
- Implemented: `ace_step_15_music` is registered in `slopperly/config/models.yaml` with legacy alias `ACE-Step/acestep-v15-xl-turbo-diffusers`, exact `hf_file` downloads from `Comfy-Org/ace_step_1.5_ComfyUI_files`, and the production diffusion default `acestep_v1.5_xl_turbo_bf16.safetensors`.
- Implemented: `slopperly/runtime/comfy/nodes.lock.yaml` asserts core ACE-Step 1.5 node classes including `TextEncodeAceStepAudio1.5`, `EmptyAceStep1.5LatentAudio`, and `ModelSamplingAuraFlow`.
- Evidence: `/home/user/Documents/Slopperly/.slopperly/runtimes/comfy-venv/bin/python -m slopperly.models.download --model ace_step_15_music --cache-root .slopperly/runtimes/ComfyUI --accept-licenses` downloaded `acestep_v1.5_xl_turbo_bf16.safetensors`, `ace_1.5_vae.safetensors`, `qwen_0.6b_ace15.safetensors`, and `qwen_4b_ace15.safetensors` into the owned Comfy model folders.
- Evidence: owned Slopperly ComfyUI was restarted on `http://127.0.0.1:8190` with API nodes disabled, CUDA 13 PyTorch, dynamic VRAM, and the ACE nodes available in `/object_info`.
- Evidence: `SLOPPERLY_COMFYUI_URL=http://127.0.0.1:8190 python -m pytest tests/gpu/test_ace_step.py --device cuda --profile smoke_16gb --runtime-timeout 30 -s` passed 1 test in 9.14s through `AceStepPlugin.generate()`.
- Evidence: Comfy loaded `ACE15TEModel_`, `ACEStep15`, and `AudioOobleckVAE` from the owned cache and executed the prompt in 8.82s.
- Evidence: `.slopperly/certification/smoke_16gb/ace_step_15_music.json` is PASS for `.slopperly/gpu-artifacts/smoke_16gb/ace_step_15_music/24680_bright_indie_pop_loop_clean_g_ace_step_15.flac`.
- Evidence: `ffprobe` validates the generated artifact as FLAC, stereo, 48000 Hz, 2.000000s, 233644 bytes; the certification validator also recorded non-silent audio.
- Evidence: integration coverage calls `AceStepPlugin.load()` and `generate()` against a loopback fake Comfy server under the local-network guard and verifies exact node/input patching plus FLAC artifact collection.
- Evidence: workflow-runner integration coverage verifies the committed `ace_step_15_music` pack patches the graph and collects one Comfy audio artifact.

### 2026-06-27 Foundation-1 Comfy workflow block

- Current parity status: `audio/foundation_music.py` is DONE ON SPEC for the `smoke_16gb` profile. It has a real owned-Comfy `FoundationMusicPlugin.generate()` WAV artifact, exact Foundation-1 model files, pinned node dependencies, dropdown PASS certification, and no remaining production blocker for that certified profile.

- Implemented: `audio/foundation_music.py` routes the legacy Foundation-1 plugin through the local Comfy workflow gateway instead of direct Torch/SciPy/Diffusers execution and generation-time Hugging Face model loading in the add-on process.
- Implemented: `foundation1_music_loop` workflow pack is committed with API/editable workflow JSON, schema, model manifest, smoke payload, and README.
- Implemented: the workflow uses `Foundation1ModelLoader -> Foundation1Generate -> SaveAudio`, preserving prompt, negative prompt as an avoidance tag, requested duration through BPM/bar mapping, BPM, bars, key, steps, seed, sampler, cfg, sigma controls, and returned artifact path.
- Implemented: `FoundationMusicPlugin.generate()` patches a per-invocation `SaveAudio.filename_prefix` so repeated identical prompts still save a fresh Comfy output, then converts Comfy's FLAC save to a real `.wav` UI artifact before returning.
- Implemented: `foundation1_music_loop` is registered in `slopperly/config/models.yaml` with legacy alias `tintwotin/Foundation-1-Diffusers` and artifact source `RoyalCities/Foundation-1`.
- Implemented: `slopperly/runtime/comfy/nodes.lock.yaml` asserts `Foundation1ModelLoader` and `Foundation1Generate` from pinned `Saganaki22/ComfyUI-Foundation-1`.
- Evidence: `/home/user/Documents/Slopperly/.slopperly/runtimes/comfy-venv/bin/python -m slopperly.models.download --model foundation1_music_loop --cache-root .slopperly/runtimes/ComfyUI --accept-licenses` downloaded the Foundation-1 snapshot into the owned Comfy model folder.
- Evidence: owned model files are present at `.slopperly/runtimes/ComfyUI/models/stable_audio/Foundation-1/Foundation_1.safetensors` (`2426992388` bytes) and `.slopperly/runtimes/ComfyUI/models/stable_audio/Foundation-1/model_config.json`.
- Evidence: `/home/user/Documents/Slopperly/.slopperly/runtimes/comfy-venv/bin/python .slopperly/runtimes/ComfyUI/custom_nodes/foundation_1/install.py` installed the Foundation node dependencies plus private `k-diffusion==0.1.1` into the owned Comfy venv/runtime.
- Evidence: owned Slopperly ComfyUI was restarted on `http://127.0.0.1:8190` with API nodes disabled, CUDA 13 PyTorch, dynamic VRAM, and `Foundation1ModelLoader`, `Foundation1Generate`, and `SaveAudio` available in `/object_info`; the loader model list included `Foundation-1/Foundation_1.safetensors`.
- Evidence: `SLOPPERLY_COMFYUI_URL=http://127.0.0.1:8190 python -m pytest tests/gpu/test_foundation_music.py --device cuda --profile smoke_16gb --runtime-timeout 30 -s` passed 1 test in 9.25s after a fresh Comfy restart through `FoundationMusicPlugin.generate()`.
- Evidence: Comfy loaded Foundation-1 on CUDA from the owned cache, injected private k-diffusion `VDenoiser`, generated a 100 BPM / 4 bars loop with 20 steps, and executed the prompt in 8.90s.
- Evidence: `.slopperly/certification/smoke_16gb/foundation1_music_loop.json` is PASS for `.slopperly/gpu-artifacts/smoke_16gb/foundation1_music_loop/424242_warm_analog_bass_clipped_hous_foundation1.wav`.
- Evidence: `ffprobe` validates the generated artifact as WAV PCM s16le, stereo, 44100 Hz, 9.984580s, 1761358 bytes; the certification validator also recorded non-silent audio.
- Evidence: integration coverage calls `FoundationMusicPlugin.load()` and `generate()` against a loopback fake Comfy server under the local-network guard and verifies exact node/input patching, per-run save prefix patching, and WAV artifact return.
- Evidence: workflow-runner integration coverage verifies the committed `foundation1_music_loop` pack patches the graph and collects one Comfy audio artifact.
- Evidence: `python -m slopperly.audit.model_registry`, `python -m slopperly.audit.workflow_packs`, `python -m pytest tests/unit`, `python -m pytest tests/integration`, `python -m slopperly.audit.no_cloud`, and `python -m slopperly.audit.dropdown_certification --profile smoke_16gb --report-only` all passed after this Foundation certification; at that point dropdown certification reported 4 passed and 36 blocked entries. The current certification summary above supersedes this historical count.

### 2026-06-27 Chatterbox Comfy workflow block

- Current parity status: `audio/chatterbox.py` is DONE ON SPEC for the `smoke_16gb` profile. Plain TTS, reference TTS, and the current one-audio VC compatibility path have real owned-Comfy `ChatterboxPlugin.generate()` WAV artifacts, exact Chatterbox model files, dropdown PASS certification, and no remaining production blocker for that certified profile. True cross-speaker VC remains blocked until the existing UI exposes a second target voice selector and that two-audio graph passes artifact certification.

- Implemented: `audio/chatterbox.py` routes the legacy Chatterbox plugin through the local Comfy workflow gateway instead of direct Torch/Torchaudio/Chatterbox package execution in the add-on process.
- Implemented: `ChatterboxPlugin.generate()` now asks Comfy to save FLAC internally, patches a per-invocation `SaveAudio.filename_prefix`, converts/copies the result to a real `.wav` UI artifact, and returns that WAV path.
- Implemented: `chatterbox_tts_comfy`, `chatterbox_tts_vc_comfy`, and `chatterbox_vc_comfy` workflow packs are committed with API/editable workflow JSON, schemas, model manifests, smoke payloads, and READMEs.
- Implemented: the TTS workflows use `FL_ChatterboxTTS -> SaveAudio`, with optional `LoadAudio` feeding `audio_prompt` for reference voice generation, preserving prompt, reference audio, chat params, seed, use-CPU, keep-loaded, and returned artifact path.
- Implemented: the VC compatibility workflow uses `LoadAudio -> FL_ChatterboxVC -> SaveAudio` and wires the current one audio path to both VC audio inputs, with the true two-audio target-voice limitation recorded in schema and `usage_note`.
- Implemented: `chatterbox_tts_vc_comfy` is registered in `slopperly/config/models.yaml` with legacy alias `Chatterbox`, artifact source `ResembleAI/chatterbox`, and an auxiliary VC source for `s3gen.pt`/`conds.pt`.
- Implemented: `slopperly/runtime/comfy/nodes.lock.yaml` asserts exact Chatterbox `/object_info` class keys from pinned `filliptm/ComfyUI_Fill-ChatterBox`.
- Evidence: `/home/user/Documents/Slopperly/.slopperly/runtimes/comfy-venv/bin/python -m slopperly.models.download --model chatterbox_tts_vc_comfy --cache-root .slopperly/runtimes/ComfyUI --accept-licenses` downloaded/cached the standard and auxiliary VC Chatterbox snapshots into the owned Comfy model folder.
- Evidence: owned model files are present under `.slopperly/runtimes/ComfyUI/models/chatterbox/chatterbox/` and `.slopperly/runtimes/ComfyUI/models/chatterbox/chatterbox_vc/`, including `ve.safetensors`, `t3_cfg.safetensors`, `s3gen.safetensors`, `s3gen.pt`, `tokenizer.json`, and `conds.pt`.
- Evidence: owned Slopperly ComfyUI on `http://127.0.0.1:8190` exposes `FL_ChatterboxTTS`, `FL_ChatterboxVC`, `FL_ChatterboxTurboTTS`, `FL_ChatterboxMultilingualTTS`, `LoadAudio`, and `SaveAudio` in `/object_info`.
- Evidence: `SLOPPERLY_COMFYUI_URL=http://127.0.0.1:8190 python -m pytest tests/gpu/test_chatterbox.py --device cuda --profile smoke_16gb --runtime-timeout 30 -s` passed 1 test in 19.44s through `ChatterboxPlugin.generate()`, generating plain TTS, reference TTS using the first artifact as the reference voice, and VC using the same generated speech sample as the legacy single audio input.
- Evidence: Comfy logged cached local Chatterbox file use for `ve.safetensors`, `t3_cfg.safetensors`, `s3gen.safetensors`, `tokenizer.json`, `conds.pt`, `s3gen.pt`, cached TTS/VC models on CUDA, and executed the three prompts in 6.91s, 9.34s, and 2.00s.
- Evidence: `.slopperly/certification/smoke_16gb/chatterbox_tts_vc_comfy.json` is PASS for `.slopperly/gpu-artifacts/smoke_16gb/chatterbox_tts_vc_comfy/chatterbox_manifest.json`.
- Evidence: `ffprobe` validates the generated WAV artifacts as PCM s16le mono 24 kHz: `9090_A_calm_local_Chatterbox_voice_confirms_the_Slopp_chatterbox.wav` is 3.480000s and 167118 bytes, `9091_This_second_local_Chatterbox_line_uses_the_gener_chatterbox.wav` is 3.200000s and 153678 bytes, and `9092_chatterbox_voice_clone_chatterbox.wav` is 3.480000s and 167118 bytes; the certification validator recorded non-silent RMS values for all three.
- Evidence: the certification manifest records the compatibility note: `Chatterbox VC used the legacy single audio picker for both source and target voice; cross-speaker VC needs a future second target selector.`
- Evidence: integration coverage calls `ChatterboxPlugin.load()` and `generate()` against a loopback fake Comfy server under the local-network guard and verifies plain TTS, reference TTS, and VC compatibility graph patching plus WAV artifact return.
- Evidence: workflow-runner integration coverage verifies the committed Chatterbox packs upload audio, patch exact node inputs, and collect one Comfy audio artifact.
- Evidence: `python -m slopperly.audit.model_registry`, `python -m slopperly.audit.workflow_packs`, `python -m pytest tests/unit tests/integration`, `python -m slopperly.audit.no_cloud`, and `python -m slopperly.audit.dropdown_certification --profile smoke_16gb --report-only` passed after this certification; dropdown certification reports 7 passed and 33 blocked entries.

### 2026-06-27 Chatterbox Turbo and Multilingual Comfy workflow block

- Current parity status: `audio/chatterbox_turbo.py` and `audio/chatterbox_multilingual.py` are DONE ON SPEC for the `smoke_16gb` profile. Turbo prompt-only/ref-audio and Multilingual prompt-only/ref-audio each have real owned-Comfy `ModelPlugin.generate()` WAV artifacts, exact local Chatterbox-family model files, dropdown PASS certification, and no remaining production blocker for those certified profiles. True two-audio speech-to-speech VC remains covered only by the standard Chatterbox VC compatibility profile until a second target voice selector exists and a two-audio graph passes artifact certification.

- Implemented: `audio/chatterbox_turbo.py` routes the legacy Chatterbox Turbo plugin through the local Comfy workflow gateway instead of direct Torch/Torchaudio/Chatterbox package execution and runtime conditional patching in the add-on process.
- Implemented: `ChatterboxTurboPlugin.generate()` now asks Comfy to save FLAC internally, patches a per-invocation `SaveAudio.filename_prefix`, converts/copies the result to a real `.wav` UI artifact, and returns that WAV path.
- Implemented: `audio/chatterbox_multilingual.py` routes the legacy Chatterbox Multilingual plugin through the local Comfy workflow gateway instead of direct Torch/Torchaudio/Chatterbox package execution in the add-on process.
- Implemented: `chatterbox_turbo_tts_comfy` and `chatterbox_turbo_ref_tts_comfy` workflow packs are committed with API/editable workflow JSON, schemas, model manifests, smoke payloads, and READMEs.
- Implemented: `chatterbox_multilingual_tts_comfy` and `chatterbox_multilingual_ref_tts_comfy` workflow packs are committed with API/editable workflow JSON, schemas, model manifests, smoke payloads, and READMEs and now have real RTX artifact certification through the plugin path.
- Implemented: Turbo workflows use `FL_ChatterboxTurboTTS -> SaveAudio`, with optional `LoadAudio` feeding `audio_prompt`, preserving prompt, reference audio, temperature, top_k, top_p, repetition_penalty, seed, use-CPU, keep-loaded, per-run save prefix, and returned WAV artifact path; unsupported old chat params are recorded as unmapped.
- Implemented: Multilingual workflows use `FL_ChatterboxMultilingualTTS -> SaveAudio`, with optional `LoadAudio` feeding `audio_prompt`, preserving prompt, reference audio, language, exaggeration, cfg/pace, temperature, repetition_penalty, min_p, top_p, seed, use-CPU, keep-loaded, per-run save prefix, and returned WAV artifact path.
- Implemented: `chatterbox_turbo_tts_comfy` is registered in `slopperly/config/models.yaml` with legacy alias `ChatterboxTurbo` and exact `ResembleAI/chatterbox-turbo` local artifact files.
- Implemented: `chatterbox_multilingual_tts_comfy` is registered in `slopperly/config/models.yaml` with legacy alias `ChatterboxMultilingual` and exact local `ResembleAI/chatterbox` multilingual artifact files.
- Evidence: `/home/user/Documents/Slopperly/.slopperly/runtimes/comfy-venv/bin/python -m slopperly.models.download --model chatterbox_turbo_tts_comfy --cache-root .slopperly/runtimes/ComfyUI --accept-licenses` downloaded/cached the Turbo snapshot into the owned Comfy model folder.
- Evidence: owned Turbo model files are present at `.slopperly/runtimes/ComfyUI/models/chatterbox/chatterbox_turbo/`: `ve.safetensors` (`5695784` bytes), `t3_turbo_v1.safetensors` (`1915480052` bytes), `s3gen_meanflow.safetensors` (`1064875036` bytes), `tokenizer_config.json`, `special_tokens_map.json`, `vocab.json`, `merges.txt`, `added_tokens.json`, and `conds.pt`.
- Evidence: owned Slopperly ComfyUI on `http://127.0.0.1:8190` exposes `FL_ChatterboxTurboTTS`, `LoadAudio`, and `SaveAudio` in `/object_info`.
- Evidence: `SLOPPERLY_COMFYUI_URL=http://127.0.0.1:8190 python -m pytest tests/gpu/test_chatterbox_turbo.py --device cuda --profile smoke_16gb --runtime-timeout 30 -s` passed 1 test in 8.29s through `ChatterboxTurboPlugin.generate()`, generating prompt-only Turbo TTS and reference-audio Turbo TTS. The prompt-only Turbo WAV was 11.280s, so it directly satisfied the pinned node's >5s reference-audio requirement and no padding was needed.
- Evidence: Comfy logged cached local Turbo file use for `ve.safetensors`, `t3_turbo_v1.safetensors`, `s3gen_meanflow.safetensors`, tokenizer files, and `conds.pt`, cached the Turbo model on CUDA, then executed the prompt-only and ref-audio prompts in 6.37s and 0.84s.
- Evidence: `.slopperly/certification/smoke_16gb/chatterbox_turbo_tts_comfy.json` is PASS for `.slopperly/gpu-artifacts/smoke_16gb/chatterbox_turbo_tts_comfy/chatterbox_turbo_manifest.json`.
- Evidence: `ffprobe` validates the generated Turbo WAV artifacts as PCM s16le mono 24 kHz: `9191_A_quick_local_Chatterbox_Turbo_voice_confirms_th_chatterbox_turbo.wav` is 11.280000s and 541518 bytes, and `9192_This_Chatterbox_Turbo_line_uses_a_local_generate_chatterbox_turbo.wav` is 4.160000s and 199758 bytes; the certification validator recorded non-silent RMS values for both generated outputs.
- Evidence: owned Multilingual model files are present at `.slopperly/runtimes/ComfyUI/models/chatterbox/chatterbox_multilingual/`: `ve.pt` (`5698626` bytes), `t3_mtl23ls_v2.safetensors` (`2143989752` bytes), `s3gen.pt` (`1057165844` bytes), `grapheme_mtl_merged_expanded_v1.json`, `conds.pt`, and `Cangjie5_TC.json`; these were hardlinked from the already-installed `ResembleAI/chatterbox` local artifact snapshot to avoid duplicate downloads.
- Evidence: owned Slopperly ComfyUI on `http://127.0.0.1:8190` exposes `FL_ChatterboxMultilingualTTS`, `LoadAudio`, and `SaveAudio` in `/object_info`, including the exact Comfy language enum entries for French and Spanish plus `audio_prompt`.
- Evidence: `SLOPPERLY_COMFYUI_URL=http://127.0.0.1:8190 python -m pytest tests/gpu/test_chatterbox_multilingual.py --device cuda --profile smoke_16gb --runtime-timeout 30 -s` passed 1 test in 11.50s through `ChatterboxMultilingualPlugin.generate()`, generating French prompt-only multilingual TTS and Spanish reference-audio multilingual TTS.
- Evidence: Comfy logged cached local multilingual file use for `ve.pt`, `t3_mtl23ls_v2.safetensors`, `s3gen.pt`, `grapheme_mtl_merged_expanded_v1.json`, `conds.pt`, and `Cangjie5_TC.json`, cached the multilingual model on CUDA, then executed the prompt-only and ref-audio prompts in 8.00s and 2.96s.
- Evidence: `.slopperly/certification/smoke_16gb/chatterbox_multilingual_tts_comfy.json` is PASS for `.slopperly/gpu-artifacts/smoke_16gb/chatterbox_multilingual_tts_comfy/chatterbox_multilingual_manifest.json`.
- Evidence: `ffprobe` validates the generated Multilingual WAV artifacts as PCM s16le mono 24 kHz: `9292_French_fr__Bonjour_cette_voix_Chatterbox_multilingue_local_chatterbox_mtl.wav` is 7.270000s and 349038 bytes, and `9293_Spanish_es__Esta_segunda_voz_multilingue_usa_una_referencia__chatterbox_mtl.wav` is 9.030000s and 433518 bytes; the certification validator recorded non-silent RMS values for both generated outputs.
- Evidence: integration coverage calls both plugin `load()`/`generate()` paths against a loopback fake Comfy server under the local-network guard and verifies plain/ref graph patching plus WAV artifact return for Turbo and Multilingual.
- Evidence: workflow-runner integration coverage verifies the committed Turbo and Multilingual reference packs upload audio, patch exact node inputs, and collect one Comfy audio artifact.
- Evidence: `python -m slopperly.audit.model_registry`, `python -m slopperly.audit.workflow_packs`, `python -m pytest tests/unit tests/integration`, `python -m slopperly.audit.no_cloud`, and `python -m slopperly.audit.dropdown_certification --profile smoke_16gb --report-only` passed after the Multilingual certification; dropdown certification reports 9 passed and 31 blocked entries.
- Not done - UI/workflow required: Turbo and Multilingual reference-audio paths are zero-shot TTS conditioning; true two-audio speech-to-speech VC remains covered only by the standard Chatterbox VC compatibility profile until a second target voice selector is wired and a two-audio workflow passes artifact certification.

### 2026-06-27 OmniVoice vLLM-Omni block

- Current parity status: `audio/omnivoice.py` is DONE ON SPEC for the `smoke_16gb` profile. Prompt-only TTS and reference-audio voice-clone TTS have real local `OmniVoicePlugin.generate()` WAV artifacts through a local vLLM-Omni server, exact local OmniVoice model files, dropdown PASS certification, and no remaining production blocker for that certified profile.

- Implemented: `.slopperly/vllm-omni-venv` was installed with matching `vllm-omni==0.22.0` and `vllm==0.22.0`; the installer manifest records both packages and the Slopperly OmniVoice sampling-controls patch.
- Implemented: `slopperly/runtime/vllm_omni/supervisor.py` launches the current CLI shape, `vllm-omni serve <model> --omni`, with localhost host/port, local-media path, and Slopperly download directory instead of the stale module entrypoint.
- Implemented: `slopperly/runtime/vllm_omni/tts_client.py` keeps the local URL guard, posts to `/v1/audio/speech`, omits bogus `voice="default"` for OmniVoice, maps `language`, `seed`, and `extra_params`, and encodes local reference audio files as `data:` URIs so pure-diffusion vLLM-Omni clone mode can consume them without relying on server-side file loading.
- Implemented: `audio/omnivoice.py` now maps prompt, reference audio, reference text, language, instruction text, speed, seed, steps, and guidance into the local speech request. Steps/guidance are sent as `extra_params: {"num_step": ..., "guidance_scale": ...}`.
- Implemented: the vLLM-Omni installer applies a deterministic local patch to `vllm_omni/diffusion/models/omnivoice/pipeline_omnivoice.py`, making the installed OmniVoice pipeline honor request-time `num_step` and `guidance_scale` instead of hardcoding the config defaults for those existing UI controls.
- Implemented: `operators/main_ops.py` now preserves `scene.ref_text` as transcript text instead of treating it as a path via `bpy.path.abspath`, so the existing reference-text UI field reaches TTS/voice-clone plugins correctly.
- Evidence: `.slopperly/vllm-omni-venv/bin/python -m slopperly.models.download --model omnivoice_vllm_omni --cache-root .slopperly/runtimes/vllm-omni --accept-licenses` downloaded the local `k2-fsa/OmniVoice` snapshot into `.slopperly/runtimes/vllm-omni/models/vllm_omni/k2-fsa/OmniVoice`.
- Evidence: owned OmniVoice model files are present in that snapshot: `config.json`, `model.safetensors` (`2450344112` bytes), `tokenizer.json`, tokenizer config, and `audio_tokenizer/model.safetensors` (`805665628` bytes); snapshot size is `3.1G`.
- Evidence: local vLLM-Omni was started on `http://127.0.0.1:8091` with `vllm-omni serve /home/user/Documents/Slopperly/.slopperly/runtimes/vllm-omni/models/vllm_omni/k2-fsa/OmniVoice --omni --host 127.0.0.1 --port 8091 --allowed-local-media-path /home/user/Documents/Slopperly --download-dir /home/user/Documents/Slopperly/.slopperly/runtimes/vllm-omni`.
- Evidence: server health at `/v1/models` reported the local OmniVoice model path, and vLLM-Omni logs showed the OmniVoice pipeline and HiggsAudioV2 tokenizer loaded on CUDA with about 4.8 GiB in the diffusion worker.
- Evidence: the first GPU certification attempt produced a real prompt-only WAV, then clone mode failed because pure-diffusion vLLM-Omni returned `Cannot load local files without --allowed-local-media-path` for a `file://` reference even though the server was launched with that flag. This was fixed by data-URI encoding local reference audio in the client, not documented as a final blocker.
- Evidence: `SLOPPERLY_VLLM_OMNI_URL=http://127.0.0.1:8091 python -m pytest tests/gpu/test_vllm_omni_tts.py --device cuda --profile smoke_16gb --runtime-timeout 30 -s` passed 1 test in 1.47s through `OmniVoicePlugin.generate()`, generating prompt-only and clone WAV artifacts.
- Evidence: `.slopperly/certification/smoke_16gb/omnivoice_vllm_omni.json` is PASS for `.slopperly/gpu-artifacts/smoke_16gb/omnivoice_vllm_omni/omnivoice_manifest.json`.
- Evidence: the manifest validates `omnivoice_plain.wav` as WAV mono 24 kHz, 2.960s, RMS 3985.2982825841727, and `omnivoice_clone.wav` as WAV mono 24 kHz, 4.920s, RMS 2472.5453814020925.
- Evidence: focused vLLM-Omni client/supervisor/plugin integration tests passed with `python -m pytest tests/unit/test_runtime_supervisors.py tests/unit/test_runtime_installers.py tests/unit/test_local_runtime_clients.py tests/integration/test_local_plugin_paths.py -q` after the implementation.
- Evidence: `python -m slopperly.audit.model_registry`, `python -m slopperly.audit.workflow_packs`, `python -m pytest tests/unit tests/integration`, `python -m slopperly.audit.no_cloud`, and `python -m slopperly.audit.dropdown_certification --profile smoke_16gb --report-only` passed after the OmniVoice certification; dropdown certification reports 10 passed and 30 blocked entries.

### 2026-06-27 MOSS-TTS vLLM-Omni block

- Current parity status: `audio/moss_tts.py` is DONE ON SPEC for the `smoke_16gb` profile. Voice-clone TTS has a real local `MossTTSPlugin.generate()` WAV artifact through a local vLLM-Omni server, exact local MOSS-TTS-Nano and MOSS audio tokenizer files, dropdown PASS certification, and no remaining production blocker for that certified profile.

- Implemented: `audio/moss_tts.py` now declares and consumes `InputSpec.AUDIO_REF` while preserving the existing custom MOSS reference-audio picker. It uses `ModelInputs.audio_ref` first and falls back to `scene.moss_ref_audio_path`.
- Implemented: MOSS-TTS-Nano no longer sends bogus `voice="default"` or decorative generation settings in `instructions`; it sends a real clone request with local reference audio, normalized language, seed, `max_new_tokens`, and `extra_params` for `max_new_frames`, text/audio temperature, top-p, and top-k.
- Implemented: `slopperly/runtime/vllm_omni/tts_client.py` now supports the OpenAI-compatible `max_new_tokens` speech field while preserving the local URL guard and local reference-audio `data:` URI encoding.
- Implemented: the vLLM-Omni installer applies a deterministic local patch to `vllm_omni/entrypoints/openai/serving_speech.py`, making the MOSS-TTS-Nano path forward request-time `max_new_frames`, seed, text/audio sampling controls, and repetition penalty into per-request runtime information read by `MossTTSNanoForGeneration`.
- Implemented: `MossTTSPlugin.generate()` resolves the actual single served model ID from `/v1/models` when the local vLLM-Omni server advertises the local snapshot path instead of the Hugging Face repo ID, which keeps local-path serving compatible with the plugin request path.
- Implemented: `slopperly/config/models.yaml` now records the auxiliary `OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano` snapshot required by the MOSS-TTS-Nano model, and `slopperly.models.download` rewrites the local cached MOSS `config.json` to point at that local tokenizer path after both snapshots are present.
- Evidence: `.slopperly/vllm-omni-venv/bin/python -m slopperly.models.download --model moss_tts_nano_vllm_omni --cache-root .slopperly/runtimes/vllm-omni --accept-licenses` installed the local MOSS-TTS-Nano snapshot and the auxiliary MOSS audio tokenizer snapshot into `.slopperly/runtimes/vllm-omni/models/vllm_omni/`; a repeat run reported the main snapshot cached, the tokenizer snapshot cached, and `MOSS config already points at local audio tokenizer`.
- Evidence: owned MOSS files are present under `.slopperly/runtimes/vllm-omni/models/vllm_omni/OpenMOSS-Team/MOSS-TTS-Nano` (`227M`) and `.slopperly/runtimes/vllm-omni/models/vllm_omni/OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano` (`85M`), with `model-00001-of-00001.safetensors` at `87922568` bytes for the tokenizer.
- Evidence: the local cached MOSS `config.json` points `audio_tokenizer_pretrained_name_or_path` to `/home/user/Documents/Slopperly/.slopperly/runtimes/vllm-omni/models/vllm_omni/OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano`, so server startup loads the codec locally rather than resolving a hosted repo.
- Evidence: local vLLM-Omni was started on `http://127.0.0.1:8091` with `vllm-omni serve /home/user/Documents/Slopperly/.slopperly/runtimes/vllm-omni/models/vllm_omni/OpenMOSS-Team/MOSS-TTS-Nano --omni --host 127.0.0.1 --port 8091 --allowed-local-media-path /home/user/Documents/Slopperly --download-dir /home/user/Documents/Slopperly/.slopperly/runtimes/vllm-omni`.
- Evidence: server logs showed `MOSS-TTS-Nano LM loaded on cuda` from the local MOSS snapshot and `MOSS-Audio-Tokenizer-Nano loaded on cuda` from the local tokenizer snapshot, with the MOSS worker using about 628 MiB VRAM after load.
- Evidence: the first GPU certification attempt was not final evidence because the local server rejected the Hugging Face repo ID while serving the snapshot path. This was fixed in code by resolving the single served model ID from `/v1/models`, then the same plugin-path test was rerun successfully.
- Evidence: `SLOPPERLY_VLLM_OMNI_URL=http://127.0.0.1:8091 python -m pytest tests/gpu/test_vllm_omni_voice_clone.py --device cuda --profile smoke_16gb --runtime-timeout 30 -s` passed 1 test in 2.43s through `MossTTSPlugin.generate()`.
- Evidence: server logs for the passing request showed `TTS speech request ... model=moss_tts_nano`, `Applied extra_params: {'max_new_frames': 128, 'text_temperature': 1.1, 'text_top_p': 0.8, 'text_top_k': 25, 'audio_temperature': 1.1, 'audio_top_p': 0.8, 'audio_top_k': 25}`, and a 200 OK WAV response.
- Evidence: `.slopperly/certification/smoke_16gb/moss_tts_nano_vllm_omni.json` is PASS for `.slopperly/gpu-artifacts/smoke_16gb/moss_tts_nano_vllm_omni/moss_tts_nano_manifest.json`.
- Evidence: `ffprobe` validates `.slopperly/gpu-artifacts/smoke_16gb/moss_tts_nano_vllm_omni/moss_tts_nano.wav` as WAV PCM s16le mono 48 kHz, 4.800000s, 460844 bytes; the artifact validator recorded non-silent RMS `4441.058497322528`.
- Evidence: focused MOSS/vLLM-Omni tests passed with `python -m pytest tests/unit/test_runtime_installers.py tests/unit/test_local_runtime_clients.py tests/integration/test_local_plugin_paths.py -q` reporting 60 passed.
- Evidence: `python -m slopperly.audit.model_registry`, `python -m slopperly.audit.workflow_packs`, `python -m pytest tests/unit tests/integration`, `python -m slopperly.audit.no_cloud`, and `python -m slopperly.audit.dropdown_certification --profile smoke_16gb --report-only` passed after the MOSS certification; dropdown certification reports 11 passed and 29 blocked entries.

### 2026-06-27 OmniGen Comfy workflow block

- Current parity status: `image/omnigen.py` is NOT DONE ON SPEC. Needs owned Comfy OmniGen nodes/model files, all selected image slots and per-image prompt placeholders mapped, optional-slot pruning verified with real uploads, and a real multi-reference PNG.

- Scaffold only: `image/omnigen.py` now routes the legacy `Shitao/OmniGen-v1-diffusers` plugin through the local Comfy workflow gateway instead of direct Torch/Diffusers `OmniGenPipeline` execution in the add-on process.
- Scaffold only: the existing triple prompt/image UI is preserved; the wrapper resolves the same scene strip pickers to local paths, composes the prompt placeholders, preserves the old `img_guidance_scale` default, and returns the existing PNG artifact path shape.
- Scaffold only: `omnigen_v1_multi_image` workflow pack is committed with API/editable workflow JSON, schema, model manifest, smoke payload, and README.
- Scaffold only: Comfy workflow upload schemas can now mark media slots optional and declare disconnect/prune targets, so empty OmniGen reference slots are removed before `/object_info` and queueing.
- Scaffold only: `omnigen_v1_multi_image` is registered in `slopperly/config/models.yaml` with legacy alias `Shitao/OmniGen-v1-diffusers` and artifact source `Shitao/OmniGen-v1`.
- Scaffold only: `slopperly/runtime/comfy/nodes.lock.yaml` now asserts `ailab_OmniGen` from pinned `1038lab/ComfyUI-OmniGen`.
- Evidence: integration coverage calls `OmniGenPlugin.load()` and `generate()` against a loopback fake Comfy server under the local-network guard and verifies selected strip uploads, prompt placeholders, optional slot pruning, and PNG artifact collection.
- Evidence: workflow-runner integration coverage verifies `omnigen_v1_multi_image` indexed image uploads, exact node/input patching, optional third-slot pruning, and single image-output collection.
- Not done - install/test required: real RTX 4090 OmniGen artifact certification requires owned ComfyUI running with `ailab_OmniGen`, core image nodes, `Shitao/OmniGen-v1` files installed under `models/LLM/OmniGen-v1/`, and the OmniGen node's code dependency available before generation so the node does not use its first-run downloader.

### 2026-06-27 Qwen Image Edit Comfy workflow block

- Current parity status: `image/qwen_image_edit.py` is NOT DONE ON SPEC. Needs owned Comfy GGUF/Qwen edit files, one-reference and three-reference UI image mapping, prompt/negative/resolution/frames/steps/seed/LoRA mapping, and real edit PNGs; dynamic arbitrary LoRA injection remains not mapped.

- Scaffold only: `image/qwen_image_edit.py` now routes `Qwen/Qwen-Image-Edit-2511` through the local Comfy workflow gateway instead of direct Torch/Transformers/Diffusers/SDNQ execution and Hugging Face runtime downloads in the add-on process.
- Scaffold only: the existing input-strip selector, three Qwen reference pickers, prompt, negative prompt, resolution, frames, steps, seed, and LoRA UI sections remain present; the wrapper resolves local reference strips, uses the first three references, and returns the existing PNG artifact path shape.
- Scaffold only: `qwen_image_edit_2511_multi_gguf` workflow pack is committed with API/editable workflow JSON, schema, model manifest, smoke payload, and README.
- Scaffold only: the workflow uses Comfy core Qwen/Kontext edit nodes plus ComfyUI-GGUF `UnetLoaderGGUF` for `qwen-image-edit-2511-Q5_K_M.gguf`, and applies the local Lightning 4-step LoRA profile.
- Scaffold only: `slopperly/config/models.yaml` now records the Qwen GGUF plus auxiliary Comfy text encoder, Qwen VAE, and Lightning LoRA artifacts; the downloader/registry audit now supports exact Hugging Face source-path-to-target mappings for `split_files/...` assets.
- Evidence: integration coverage calls `QwenImageEditPlugin.load()` and `generate()` against a loopback fake Comfy server under the local-network guard and verifies image uploads, prompt/negative patching, optional reference-slot pruning, and PNG artifact collection.
- Evidence: workflow-runner integration coverage verifies the committed Qwen pack directly, and `tests/gpu/test_qwen_image_edit_2511.py` now performs one-reference and three-reference plugin-path certification attempts instead of reporting an unwired-test block.
- Not done - install/test required: real RTX 4090 certification requires owned ComfyUI with ComfyUI-GGUF, Comfy core Qwen/Kontext edit nodes, and the Qwen GGUF/text encoder/VAE/Lightning LoRA files installed locally.
- Not done - install/test required: arbitrary project LoRA injection is not dynamically mapped in this workflow pack yet; the committed graph applies the certified Lightning adapter and records custom LoRA injection as a follow-up rather than loading placeholder filenames.

### 2026-06-27 Qwen Image 2512 Comfy workflow block

- Current parity status: `image/qwen_image.py` is NOT DONE ON SPEC. Needs owned Comfy GGUF/Qwen image files, T2I and I2I UI mapping for prompt/image/resolution/frames/steps/strength/seed/LoRA, all supported aspect presets tested, and real PNG artifacts; dynamic arbitrary LoRA injection remains not mapped.

- Scaffold only: `image/qwen_image.py` now routes `Qwen/Qwen-Image-2512` through the local Comfy workflow gateway instead of direct Torch/Transformers/Diffusers execution and generation-time Hugging Face downloads in the add-on process.
- Scaffold only: the existing prompt, negative prompt, image strip, resolution, frames, steps, image strength, seed, and LoRA UI sections remain present; the wrapper selects text-to-image or img2img workflow packs from the existing `ModelInputs.mode` and `ModelInputs.image` values.
- Scaffold only: `qwen_image_2512_t2i_gguf` and `qwen_image_2512_i2i_gguf` workflow packs are committed with API/editable workflow JSON, schemas, model manifests, smoke payloads, and READMEs.
- Scaffold only: the workflows use ComfyUI-GGUF `UnetLoaderGGUF` for `qwen-image-2512-Q5_K_M.gguf`, Comfy core Qwen image nodes, and the local Lightning 4-step LoRA profile.
- Scaffold only: `slopperly/config/models.yaml` now records the Qwen Image 2512 GGUF plus auxiliary Comfy text encoder, Qwen VAE, and Lightning LoRA artifacts; `slopperly/runtime/comfy/nodes.lock.yaml` now asserts `EmptySD3LatentImage`.
- Evidence: integration coverage calls `QwenImagePlugin.load()` and `generate()` against a loopback fake Comfy server under the local-network guard and verifies text-to-image graph patching, img2img image upload, and the preserved `denoise = 1.0 - strength` mapping.
- Evidence: workflow-runner integration coverage verifies both committed Qwen Image 2512 packs directly, and `tests/gpu/test_qwen_image_2512.py` now performs text-to-image and img2img plugin-path certification attempts instead of reporting an unwired-test block.
- Not done - install/test required: real RTX 4090 certification requires owned ComfyUI with ComfyUI-GGUF, Comfy core Qwen image nodes, and the Qwen GGUF/text encoder/VAE/Lightning LoRA files installed locally.
- Not done - install/test required: arbitrary project LoRA injection is not dynamically mapped in these workflow packs yet; the committed graph applies the certified Lightning adapter and records custom LoRA injection as a follow-up rather than loading placeholder filenames.

### 2026-06-27 Z-Image Comfy workflow block

- Current parity status: `image/zimage.py` and Turbo are NOT DONE ON SPEC. Base T2I, base I2I, Turbo T2I, and Turbo I2I each need owned Comfy model files, prompt/image/resolution/frames/steps/guidance/strength/seed mapping, and real PNGs; Turbo negative prompt remains deliberately unmapped by the official graph.

- Scaffold only: `image/zimage.py` now routes `Tongyi-MAI/Z-Image` and `Tongyi-MAI/Z-Image-Turbo` through the local Comfy workflow gateway instead of direct Torch/Diffusers execution and generation-time Hugging Face downloads in the add-on process.
- Scaffold only: the existing prompt, negative prompt, image strip, resolution, frames, steps, guidance, image strength, and seed UI sections remain present; the wrapper selects text-to-image or img2img workflow packs from the existing `ModelInputs.mode` and `ModelInputs.image` values.
- Scaffold only: `zimage_t2i_i2i`, `zimage_t2i_i2i_img2img`, `zimage_turbo_t2i_i2i`, and `zimage_turbo_t2i_i2i_img2img` workflow packs are committed with API/editable workflow JSON, schemas, model manifests, smoke payloads, and READMEs.
- Scaffold only: the workflows use official Comfy core Z-Image template nodes: `UNETLoader`, `ModelSamplingAuraFlow`, `CLIPLoader`, `VAELoader`, `CLIPTextEncode`, `KSampler`, `VAEDecode`, and `SaveImage`; img2img adds `LoadImage`, `ImageScale`, and `VAEEncode`; Turbo uses `ConditioningZeroOut` for the official no-CFG negative path.
- Scaffold only: `slopperly/config/models.yaml` now records exact local artifact sources for `z_image_bf16.safetensors`, `z_image_turbo_bf16.safetensors`, `qwen_3_4b.safetensors`, and `ae.safetensors`.
- Evidence: integration coverage calls `ZImagePlugin.load()`/`generate()` and `ZImageTurboPlugin.load()`/`generate()` against a loopback fake Comfy server under the local-network guard and verifies text-to-image graph patching, img2img image upload, Turbo negative-prompt usage note, and preserved `denoise = 1.0 - strength` mapping.
- Evidence: workflow-runner integration coverage verifies all four committed Z-Image packs directly, and `tests/gpu/test_zimage.py` now performs base/Turbo text-to-image and img2img plugin-path certification attempts instead of reporting an unwired-test block.
- Not done - install/test required: real RTX 4090 certification requires owned ComfyUI with core Z-Image node classes and the Z-Image diffusion/text encoder/VAE files installed locally.
- Not done - install/test required: Z-Image Turbo negative prompts are deliberately unmapped because the official Comfy Turbo graph uses `ConditioningZeroOut`; the wrapper records this in `inputs.usage_note` when a negative prompt is supplied.

### 2026-06-27 Anima Comfy workflow block

- Current parity status: `image/anima.py` is NOT DONE ON SPEC. Needs owned Comfy Anima files, T2I and I2I UI mapping for prompt/negative/image/resolution/frames/steps/guidance/strength/seed/LoRA, real PNG artifacts, and dynamic arbitrary LoRA mapping remains unfinished.

- Scaffold only: `image/anima.py` now routes `mrfatso/anima-preview3-diffusers` through the local Comfy workflow gateway instead of direct Torch/Diffusers `AnimaAutoBlocks` execution and generation-time Hugging Face downloads in the add-on process.
- Scaffold only: the existing prompt, negative prompt, image strip, resolution, frames, steps, guidance, image strength, seed, and LoRA UI sections remain present; the wrapper selects text-to-image or img2img workflow packs from the existing `ModelInputs.mode` and `ModelInputs.image` values.
- Scaffold only: `anima_t2i_i2i` and `anima_t2i_i2i_img2img` workflow packs are committed with API/editable workflow JSON, schemas, model manifests, smoke payloads, and READMEs.
- Scaffold only: the workflows use official Comfy core Anima Preview template nodes: `UNETLoader`, `CLIPLoader`, `VAELoader`, `CLIPTextEncode`, `KSampler`, `VAEDecode`, and `SaveImage`; text-to-image uses `EmptyLatentImage`; img2img adds `LoadImage`, `ImageScale`, and `VAEEncode`.
- Scaffold only: `slopperly/config/models.yaml` now records exact local artifact sources for `anima-preview3-base.safetensors`, `qwen_3_06b_base.safetensors`, and `qwen_image_vae.safetensors`.
- Scaffold only: `slopperly/runtime/comfy/nodes.lock.yaml` now asserts the core `EmptyLatentImage` node used by the Anima text-to-image workflow.
- Evidence: integration coverage calls `AnimaPlugin.load()`/`generate()` against a loopback fake Comfy server under the local-network guard and verifies text-to-image graph patching, img2img image upload, and preserved `denoise = 1.0 - strength` mapping.
- Evidence: workflow-runner integration coverage verifies both committed Anima packs directly, and `tests/gpu/test_anima.py` now performs text-to-image and img2img plugin-path certification attempts instead of reporting an unwired-test block.
- Not done - install/test required: real RTX 4090 certification requires owned ComfyUI with core Anima node classes and the Anima diffusion/text encoder/VAE files installed locally.
- Not done - install/test required: arbitrary project LoRA injection is not dynamically mapped in these workflow packs yet; the wrapper records custom LoRA injection as a follow-up rather than loading placeholder filenames.

### 2026-06-27 ERNIE-Image Comfy workflow block

- Current parity status: `image/ernie.py` and `image/ernie_turbo.py` are NOT DONE ON SPEC. Base and Turbo each need owned Comfy ERNIE files, prompt/negative/resolution/frames/steps/guidance/seed mapping, Turbo default-step parity, and real PNG artifacts.

- Scaffold only: `image/ernie.py` and `image/ernie_turbo.py` now route `baidu/ERNIE-Image` and `baidu/ERNIE-Image-Turbo` through the local Comfy workflow gateway instead of direct Torch/Diffusers/Transformers/SDNQ execution and generation-time Hugging Face loading in the add-on process.
- Scaffold only: the existing prompt, negative prompt, resolution, frames, steps, guidance, and seed UI sections remain present. Turbo preserves the negative prompt field in the UI and records it as deliberately unmapped because the official Turbo Comfy graph uses `ConditioningZeroOut`.
- Scaffold only: `ernie_image_t2i` and `ernie_image_turbo_t2i` workflow packs are committed with API/editable workflow JSON, schemas, model manifests, smoke payloads, and READMEs.
- Scaffold only: the workflows use official Comfy core ERNIE template nodes: `UNETLoader`, `CLIPLoader`, `VAELoader`, `TextGenerate`, `CLIPTextEncode`, `EmptyFlux2LatentImage`, `KSampler`, `VAEDecode`, and `SaveImage`; Turbo adds `ConditioningZeroOut`.
- Scaffold only: `slopperly/config/models.yaml` now records exact local artifact sources from `Comfy-Org/ERNIE-Image` for `ernie-image.safetensors`, `ernie-image-turbo.safetensors`, `ministral-3-3b.safetensors`, `ernie-image-prompt-enhancer.safetensors`, and `flux2-vae.safetensors`.
- Scaffold only: `slopperly/runtime/comfy/nodes.lock.yaml` now asserts the core `EmptyFlux2LatentImage` and `TextGenerate` nodes used by the ERNIE workflows.
- Evidence: integration coverage calls `ErniePlugin.load()`/`generate()` and `ErnieTurboPlugin.load()`/`generate()` against a loopback fake Comfy server under the local-network guard and verifies text-to-image graph patching and local `TextGenerate` prompt-enhancer wiring.
- Evidence: workflow-runner integration coverage verifies both committed ERNIE packs directly, and `tests/gpu/test_ernie.py` now performs base/Turbo text-to-image plugin-path certification attempts.
- Not done - install/test required: real RTX 4090 certification requires owned ComfyUI with core ERNIE node classes and the ERNIE diffusion/text encoder/prompt enhancer/VAE files installed locally.

### 2026-06-27 Krea 2 Comfy workflow block

- Current parity status: `image/_krea2_base.py` and `image/krea2_turbo.py` are NOT DONE ON SPEC. Base and Turbo each need owned Comfy Krea files, prompt/negative where supported/resolution/frames/steps/guidance/seed/LoRA UI mapping, Turbo default parity, and real PNG artifacts.

- Scaffold only: `image/_krea2_base.py` and `image/krea2_turbo.py` now route `ethanfel/Krea-2-Base-Diffusers` and `OzzyGT/Krea_2_Turbo_sdnq_dynamic_8bit` through the local Comfy workflow gateway instead of direct Torch/Diffusers/Transformers/BitsAndBytes/SDNQ execution in the add-on process.
- Scaffold only: the existing prompt, negative prompt, resolution, frames, steps, guidance, seed, and LoRA UI sections remain present. Turbo records the negative prompt field as deliberately unmapped because the official Comfy Turbo graph uses `ConditioningZeroOut`.
- Scaffold only: `krea2_base_t2i` and `krea2_turbo_t2i` workflow packs are committed with API/editable workflow JSON, schemas, model manifests, smoke payloads, and READMEs.
- Scaffold only: the workflows use official Comfy core Krea template node classes: `UNETLoader`, `CLIPLoader`, `VAELoader`, `TextGenerate`, `CLIPTextEncode`, `EmptyLatentImage`, `KSampler`, `VAEDecode`, and `SaveImage`; Turbo adds `ConditioningZeroOut`.
- Scaffold only: `slopperly/config/models.yaml` now records exact local artifact sources from `Comfy-Org/Krea-2` for `krea2_raw_fp8_scaled.safetensors`, `krea2_turbo_fp8_scaled.safetensors`, `qwen3vl_4b_fp8_scaled.safetensors`, and `qwen_image_vae.safetensors`.
- Evidence: integration coverage calls `Krea2BasePlugin.load()`/`generate()` and `Krea2TurboPlugin.load()`/`generate()` against a loopback fake Comfy server under the local-network guard and verifies text-to-image graph patching and local `TextGenerate` prompt-enhancer wiring.
- Evidence: workflow-runner integration coverage verifies both committed Krea packs directly, and `tests/gpu/test_krea2.py` now performs base/Turbo text-to-image plugin-path certification attempts.
- Not done - install/test required: real RTX 4090 certification requires owned ComfyUI with core Krea node classes and the Krea diffusion/text encoder/VAE files installed locally.
- Not done - install/test required: arbitrary project LoRA injection is not dynamically mapped in these workflow packs yet; the wrappers preserve the LoRA UI and record custom LoRA injection as a follow-up rather than loading placeholder filenames.

### 2026-06-27 Lumina Image 2.0 Comfy workflow block

- Current parity status: `image/lumina2.py` is NOT DONE ON SPEC. Needs owned Comfy Lumina checkpoint/files, prompt/negative/resolution/frames/steps/guidance/seed mapping, and a real PNG artifact.

- Scaffold only: `image/lumina2.py` now routes `Alpha-VLLM/Lumina-Image-2.0` through the local Comfy workflow gateway instead of direct Torch/Diffusers `Lumina2Pipeline` execution and generation-time Hugging Face loading in the add-on process.
- Scaffold only: the existing prompt, negative prompt, resolution, frames, steps, guidance, and seed UI sections remain present.
- Scaffold only: `lumina2_t2i` workflow pack is committed with API/editable workflow JSON, schema, model manifest, smoke payload, and README.
- Scaffold only: the workflow uses official Comfy core Lumina nodes/classes: `CheckpointLoaderSimple`, `ModelSamplingAuraFlow`, `CLIPTextEncodeLumina2`, `CLIPTextEncode`, `EmptySD3LatentImage`, `KSampler`, `VAEDecode`, and `SaveImage`.
- Scaffold only: `slopperly/config/models.yaml` now records exact local artifact source `Comfy-Org/Lumina_Image_2.0_Repackaged` with `all_in_one/lumina_2.safetensors` installed as `models/checkpoints/lumina_2.safetensors`.
- Scaffold only: `slopperly/runtime/comfy/nodes.lock.yaml` now asserts the pinned core `CLIPTextEncodeLumina2` node used by the Lumina workflow.
- Evidence: integration coverage calls `Lumina2Plugin.load()`/`generate()` against a loopback fake Comfy server under the local-network guard and verifies text-to-image graph patching.
- Evidence: workflow-runner integration coverage verifies the committed Lumina pack directly, and `tests/gpu/test_lumina2.py` now performs a text-to-image plugin-path certification attempt.
- Not done - install/test required: real RTX 4090 certification requires owned ComfyUI with core Lumina node classes and `lumina_2.safetensors` installed locally in `models/checkpoints/`.

### 2026-06-27 Ideogram 4 Comfy workflow block

- Current parity status: `image/ideogram4.py` is NOT DONE ON SPEC. Needs owned Comfy Ideogram files, prompt/structured-prompt/resolution/frames/steps/guidance/seed/LoRA mapping, text-rendering smoke proof, and real PNG output; prompt upsampling remains not certified until llama.cpp/local prompt builder is wired.

- Scaffold only: `image/ideogram4.py` now routes `ideogram-ai/ideogram-4-nf4-diffusers` through the local Comfy workflow gateway instead of direct Torch/Diffusers `Ideogram4Pipeline` execution and generation-time Hugging Face loading in the add-on process.
- Scaffold only: the existing prompt, resolution, frames, steps, guidance, seed, LoRA UI sections, and prompt-upsampling post-enhance toggle remain present; active LoRA or prompt-upsampling use records a usage note because those paths are not in the certified Comfy graph yet.
- Scaffold only: `ideogram4_t2i` workflow pack is committed with API/editable workflow JSON, schema, model manifest, smoke payload, and README.
- Scaffold only: the workflow uses official Comfy core Ideogram/custom sampling nodes: `UNETLoader`, `CLIPLoader`, `CLIPTextEncode`, `ConditioningZeroOut`, `CFGOverride`, `DualModelGuider`, `EmptyFlux2LatentImage`, `RandomNoise`, `KSamplerSelect`, `Ideogram4Scheduler`, `SamplerCustomAdvanced`, `VAELoader`, `VAEDecode`, and `SaveImage`.
- Scaffold only: `slopperly/config/models.yaml` now records exact local artifact source `Comfy-Org/Ideogram-4` with the conditional/unconditional diffusion files, Qwen3-VL text encoder, and `flux2-vae.safetensors`.
- Scaffold only: `slopperly/runtime/comfy/nodes.lock.yaml` now asserts the pinned core Ideogram/custom-sampler node classes used by the workflow.
- Evidence: integration coverage calls `Ideogram4Plugin.load()`/`generate()` against a loopback fake Comfy server under the local-network guard and verifies exact graph patching plus LoRA/prompt-upsampling usage notes.
- Evidence: workflow-runner integration coverage verifies the committed Ideogram pack directly, and `tests/gpu/test_ideogram4.py` now performs a text-to-image plugin-path certification attempt.
- Not done - install/test required: real RTX 4090 certification requires owned ComfyUI with core Ideogram node classes and `ideogram4_fp8_scaled.safetensors`, `ideogram4_unconditional_fp8_scaled.safetensors`, `qwen3vl_8b_fp8_scaled.safetensors`, and `flux2-vae.safetensors` installed locally.

### 2026-06-27 FLUX.2 Klein 4B Comfy workflow block

- Current parity status: `image/flux2_klein_4b.py` is NOT DONE ON SPEC. It is native/FP8 Comfy scaffold, not GGUF; it needs owned Comfy Klein 4B files, T2I and edit UI mapping for prompt/image refs/resolution/frames/steps/guidance/strength/seed/LoRA, real PNG artifacts, and dynamic LoRA/mask/strength parity is not complete.

- Scaffold only: `image/flux2_klein_4b.py` now routes `black-forest-labs/FLUX.2-klein-4B` through the local Comfy workflow gateway instead of direct Torch/Diffusers `Flux2KleinPipeline` execution and generation-time Hugging Face loading in the add-on process.
- Scaffold only: the existing prompt, image strip, three Klein reference selectors, resolution, frames, steps, guidance, image strength, seed, and LoRA UI sections remain present; the wrapper selects text-to-image or reference-edit workflow packs from `ModelInputs.mode` and `ModelInputs.image`.
- Scaffold only: `flux2_klein_4b_t2i_edit` and `flux2_klein_4b_t2i_edit_img2img` workflow packs are committed with API/editable workflow JSON, schemas, model manifests, smoke payloads, and READMEs.
- Scaffold only: the workflows use official Comfy core FLUX.2 Klein nodes and graph structure: `UNETLoader`, `CLIPLoader`, `VAELoader`, `CLIPTextEncode`, `ConditioningZeroOut`, `CFGGuider`, `RandomNoise`, `KSamplerSelect`, `Flux2Scheduler`, `EmptyFlux2LatentImage`, `SamplerCustomAdvanced`, `VAEDecode`, and `SaveImage`; edit adds `LoadImage`, `ImageScale`, `VAEEncode`, and `ReferenceLatent`.
- Scaffold only: `slopperly/config/models.yaml` now records exact local artifact sources for `flux-2-klein-4b-fp8.safetensors`, `qwen_3_4b.safetensors`, and `flux2-vae.safetensors`.
- Scaffold only: `slopperly/runtime/comfy/nodes.lock.yaml` now asserts `CFGGuider`, `Flux2Scheduler`, and `ReferenceLatent` from pinned Comfy core.
- Evidence: integration coverage calls `Flux2Klein4BPlugin.load()`/`generate()` against a loopback fake Comfy server under the local-network guard and verifies text-to-image graph patching, reference image uploads, optional reference-slot disconnects, and PNG artifact collection.
- Evidence: workflow-runner integration coverage verifies both committed FLUX.2 Klein packs directly, and `tests/gpu/test_flux2_klein_4b.py` now performs text-to-image and image-edit plugin-path certification attempts.
- Not done - install/test required: real RTX 4090 certification requires owned ComfyUI with core FLUX.2 Klein node classes and `flux-2-klein-4b-fp8.safetensors`, `qwen_3_4b.safetensors`, and `flux2-vae.safetensors` installed locally.
- Not done - install/test required: dynamic project LoRA injection, masked inpaint, and image-strength/denoise mapping are not dynamically mapped in these workflow packs yet; the wrapper preserves the UI and records usage notes rather than loading placeholder filenames or silently claiming unsupported behavior.

### 2026-06-27 FLUX.2 Klein 9B Comfy workflow block

- Current parity status: `image/flux2_klein_9b.py` is NOT DONE ON SPEC. It is native/FP8 Comfy scaffold, not GGUF; it needs owned Comfy Klein 9B files, T2I and edit UI mapping, real certified-device PNG artifacts, and dynamic LoRA/mask/strength parity is not complete.

- Scaffold only: `image/flux2_klein_9b.py` now routes `ModelsLab/FLUX.2-klein-9B` through the local Comfy workflow gateway instead of direct Torch/Diffusers/Transformers `Flux2KleinPipeline` execution and generation-time Hugging Face loading in the add-on process.
- Scaffold only: the existing prompt, image strip, three Klein reference selectors, resolution, frames, steps, guidance, image strength, seed, and LoRA UI sections remain present; the wrapper selects text-to-image or reference-edit workflow packs from `ModelInputs.mode` and `ModelInputs.image`.
- Scaffold only: `flux2_klein_9b_t2i_edit` and `flux2_klein_9b_t2i_edit_img2img` workflow packs are committed with API/editable workflow JSON, schemas, model manifests, smoke payloads, and READMEs.
- Scaffold only: the workflows use Comfy core FLUX.2 Klein nodes and graph structure: `UNETLoader`, `CLIPLoader`, `VAELoader`, `CLIPTextEncode`, `ConditioningZeroOut`, `CFGGuider`, `RandomNoise`, `KSamplerSelect`, `Flux2Scheduler`, `EmptyFlux2LatentImage`, `SamplerCustomAdvanced`, `VAEDecode`, and `SaveImage`; edit adds `LoadImage`, `ImageScale`, `VAEEncode`, and `ReferenceLatent`.
- Scaffold only: `slopperly/config/models.yaml` now records exact local artifact sources for `flux-2-klein-9b-fp8.safetensors`, `qwen_3_8b_fp8mixed.safetensors`, and `full_encoder_small_decoder.safetensors`.
- Evidence: integration coverage calls `Flux2Klein9BPlugin.load()`/`generate()` against a loopback fake Comfy server under the local-network guard and verifies text-to-image graph patching, reference image uploads, optional reference-slot disconnects, and PNG artifact collection.
- Evidence: workflow-runner integration coverage verifies both committed FLUX.2 Klein 9B packs directly, and `tests/gpu/test_flux2_klein_9b.py` now performs text-to-image and image-edit plugin-path certification attempts.
- Not done - install/test required: real RTX 4090 certification requires owned ComfyUI with core FLUX.2 Klein node classes and `flux-2-klein-9b-fp8.safetensors`, `qwen_3_8b_fp8mixed.safetensors`, and `full_encoder_small_decoder.safetensors` installed locally.
- Not done - install/test required: dynamic project LoRA injection, masked inpaint, and image-strength/denoise mapping are not dynamically mapped in these workflow packs yet; the wrapper preserves the UI and records usage notes rather than loading placeholder filenames or silently claiming unsupported behavior.

### 2026-06-27 FLUX.2 Klein 9B Schematic LoRA Comfy workflow block

- Current parity status: `image/flux2_klein_9b_schematic.py` is NOT DONE ON SPEC. It is a native Klein 9B plus fixed LoRA scaffold, not GGUF; it needs owned Comfy base/text/VAE plus six schematic LoRAs, schematic mode/target/image/prompt/frames/steps/guidance/seed mapping, and a real schematic PNG.

- Scaffold only: `image/flux2_klein_9b_schematic.py` now routes `nomadoor/flux-2-klein-9B-schematic-lora` through the local Comfy workflow gateway instead of direct Torch/Diffusers/Transformers `Flux2KleinPipeline` execution and generation-time Hugging Face LoRA downloads in the add-on process.
- Scaffold only: the existing prompt, required image strip, schematic mode selector, segmentation target field, frames, steps, guidance, and seed UI sections remain present; the wrapper maps the selected schematic mode to one of six committed local LoRA filenames.
- Scaffold only: `flux2_klein_9b_schematic_lora` workflow pack is committed with API/editable workflow JSON, schema, model manifest, smoke payload, and README.
- Scaffold only: the workflow uses FLUX.2 Klein 9B base, matching the upstream schematic LoRA README, with Comfy core `LoadImage`, `ImageScale`, `UNETLoader`, `LoraLoaderModelOnly`, `CLIPLoader`, `VAELoader`, `CLIPTextEncode`, `VAEEncode`, `ReferenceLatent`, `CFGGuider`, `RandomNoise`, `KSamplerSelect`, `Flux2Scheduler`, `EmptyFlux2LatentImage`, `SamplerCustomAdvanced`, `VAEDecode`, and `SaveImage`.
- Scaffold only: `slopperly/config/models.yaml` now records exact local artifact sources for `flux-2-klein-base-9b-fp8.safetensors`, `qwen_3_8b.safetensors`, `flux2-vae.safetensors`, and all six `flux2-klein-schematic-*.safetensors` LoRA files.
- Evidence: integration coverage calls `Flux2Klein9BSchematicPlugin.load()`/`generate()` against a loopback fake Comfy server under the local-network guard and verifies selected LoRA patching, source image upload, fixed upstream negative prompt, source-dimension patching, and PNG artifact collection.
- Evidence: workflow-runner integration coverage verifies the committed schematic pack directly, and `tests/gpu/test_flux2_klein_schematic.py` now performs a plugin-path certification attempt.
- Not done - install/test required: real RTX 4090 certification requires owned ComfyUI with core FLUX.2 Klein/LoRA node classes and the base 9B diffusion, Qwen 3 8B text encoder, FLUX.2 VAE, and schematic LoRA files installed locally.
- Not done - install/test required: the upstream workflow uses fixed negative prompt text; the current schematic UI does not expose a negative prompt section, so this remains a workflow constant rather than a user-editable field.

### 2026-06-27 FLUX.1 Canny and Depth Comfy workflow block

- Current parity status: `image/flux_canny.py` and `image/flux_depth.py` are NOT DONE ON SPEC. Both need owned Comfy FLUX/control/depth files, input image/prompt/resolution/frames/steps/guidance/seed UI mapping, real edge/depth-control PNGs, and image-strength plus arbitrary LoRA mapping remains not implemented by the committed graphs.

- Scaffold only: `image/flux_canny.py` now routes `fuliucansheng/FLUX.1-Canny-dev-diffusers-lora` through the local Comfy workflow gateway instead of direct Torch/Diffusers/OpenCV execution in the add-on process.
- Scaffold only: `image/flux_depth.py` now routes `romanfratric234/FLUX.1-Depth-dev-lora` through the local Comfy workflow gateway instead of direct Torch/Diffusers/Transformers execution in the add-on process.
- Scaffold only: the existing prompt, image strip, resolution, frames, steps, guidance, image strength, seed, and LoRA UI sections remain present for both control plugins.
- Scaffold only: `flux1_canny_control` and `flux1_depth_control` workflow packs are committed with API/editable workflow JSON, schemas, model manifests, smoke payloads, and READMEs.
- Scaffold only: the Canny workflow uses Comfy core `LoadImage`, `ImageScale`, `UNETLoader`, `VAELoader`, `DualCLIPLoader`, `CLIPTextEncode`, `FluxGuidance`, `InstructPixToPixConditioning`, `KSampler`, `VAEDecode`, and `SaveImage`, plus `CannyEdgePreprocessor` from pinned `Fannovel16/comfyui_controlnet_aux`.
- Scaffold only: the Depth workflow uses the same FLUX control graph plus `LoraLoaderModelOnly` for `flux1-depth-dev-lora.safetensors` and `DepthAnythingV2Preprocessor` from pinned `Fannovel16/comfyui_controlnet_aux`.
- Scaffold only: `slopperly/config/models.yaml` now records exact local artifact sources for FLUX.1 Canny, FLUX.1 Depth, text encoders, VAE, depth LoRA, and the DepthAnything V2 Large checkpoint.
- Scaffold only: `slopperly/runtime/comfy/nodes.lock.yaml` now asserts `FluxGuidance` and `InstructPixToPixConditioning`.
- Evidence: integration coverage calls `FluxCannyPlugin.load()`/`generate()` and `FluxDepthPlugin.load()`/`generate()` against a loopback fake Comfy server under the local-network guard and verifies exact graph patching plus PNG artifact collection.
- Evidence: workflow-runner integration coverage verifies both committed FLUX.1 control packs directly, and `tests/gpu/test_flux1_control.py` now performs plugin-path certification attempts.
- Not done - install/test required: real RTX 4090 certification requires owned ComfyUI with core FLUX control node classes, `comfyui_controlnet_aux`, `flux1-canny-dev.safetensors`, `flux1-dev.safetensors`, `flux1-depth-dev-lora.safetensors`, `clip_l.safetensors`, `t5xxl_fp16.safetensors`, `ae.safetensors`, and `depth_anything_v2_vitl.pth` installed locally.
- Not done - install/test required: the official Comfy control graphs do not expose a separate conditioning-strength input, so image strength is preserved in the UI and recorded as deliberately unmapped. Arbitrary project LoRA injection is likewise preserved as UI and recorded as a follow-up rather than loaded from placeholder filenames.

### 2026-06-27 FLUX Redux Comfy workflow block

- Current parity status: `image/flux_redux.py` is NOT DONE ON SPEC. Needs owned Comfy Redux/style/vision files, image-strip/resolution/frames/steps/guidance/seed mapping, and a real style-transfer PNG artifact.

- Scaffold only: `image/flux_redux.py` now routes `Runware/FLUX.1-Redux-dev` through the local Comfy workflow gateway instead of direct Torch/Diffusers execution in the add-on process.
- Scaffold only: the existing image-strip, resolution, frames, steps, guidance, and seed UI sections remain present; the wrapper patches empty text conditioning because the current Redux UI intentionally has no prompt field.
- Scaffold only: `flux_redux_restyle` workflow pack is committed with API/editable workflow JSON, schema, model manifest, smoke payload, and README.
- Scaffold only: the workflow uses Comfy core FLUX Redux graph nodes: `LoadImage`, `UNETLoader`, `DualCLIPLoader`, `VAELoader`, `CLIPTextEncode`, `FluxGuidance`, `CLIPVisionLoader`, `CLIPVisionEncode`, `StyleModelLoader`, `StyleModelApply`, `BasicGuider`, `BasicScheduler`, `ModelSamplingFlux`, `EmptySD3LatentImage`, `RandomNoise`, `KSamplerSelect`, `SamplerCustomAdvanced`, `VAEDecode`, and `SaveImage`.
- Scaffold only: `slopperly/config/models.yaml` now records exact local artifact sources for FLUX.1 Dev diffusion, the Redux style model, SigCLIP vision model, FLUX text encoders, and VAE.
- Scaffold only: `slopperly/runtime/comfy/nodes.lock.yaml` now asserts the Redux-related core classes.
- Evidence: integration coverage calls `FluxReduxPlugin.load()`/`generate()` against a loopback fake Comfy server under the local-network guard and verifies exact graph patching plus PNG artifact collection.
- Evidence: workflow-runner integration coverage verifies the committed Redux pack directly, and `tests/gpu/test_flux_redux.py` now performs a plugin-path certification attempt.
- Not done - install/test required: real RTX 4090 certification requires owned ComfyUI with Redux-capable core node classes and `flux1-dev.safetensors`, `flux1-redux-dev.safetensors`, `sigclip_vision_patch14_384.safetensors`, `clip_l.safetensors`, `t5xxl_fp16.safetensors`, and `ae.safetensors` installed locally.

### 2026-06-27 FLUX Kontext Comfy workflow block

- Current parity status: `image/flux_kontext.py` is NOT DONE ON SPEC. Needs owned Comfy Kontext files, prompt/image/resolution/frames/steps/guidance/seed/LoRA mapping, a real semantic edit PNG, and separate certified graphs for old inpaint mask and image-strength controls.

- Scaffold only: `image/flux_kontext.py` now routes `yuvraj108c/FLUX.1-Kontext-dev` through the local Comfy workflow gateway instead of direct Torch/Diffusers execution in the add-on process.
- Scaffold only: the existing prompt, image strip, resolution, frames, steps, guidance, image strength, seed, LoRA, and inpaint-capable UI contract remains present. Direct `inputs.image`, `scene.kontext_strip_1`, and `scene.kontext_strip_1_path` still resolve to a local file upload.
- Scaffold only: `flux_kontext_edit` workflow pack is committed with API/editable workflow JSON, schema, model manifest, smoke payload, and README.
- Scaffold only: the workflow uses Comfy core `LoadImage`, `UNETLoader`, `DualCLIPLoader`, `VAELoader`, `CLIPTextEncode`, `FluxGuidance`, `FluxKontextImageScale`, `VAEEncode`, `ReferenceLatent`, `ConditioningZeroOut`, `EmptySD3LatentImage`, `KSampler`, `VAEDecode`, and `SaveImage`.
- Scaffold only: `slopperly/config/models.yaml` now records exact local artifact sources for `flux1-dev-kontext_fp8_scaled.safetensors`, `clip_l.safetensors`, `t5xxl_fp8_e4m3fn_scaled.safetensors`, and `ae.safetensors`.
- Evidence: integration coverage calls `FluxKontextPlugin.load()`/`generate()` against a loopback fake Comfy server under the local-network guard and verifies exact graph patching plus PNG artifact collection.
- Evidence: workflow-runner integration coverage verifies the committed Kontext pack directly, and `tests/gpu/test_flux_kontext.py` now performs a plugin-path certification attempt.
- Not done - install/test required: real RTX 4090 certification requires owned ComfyUI with FLUX Kontext-capable core node classes and `flux1-dev-kontext_fp8_scaled.safetensors`, `clip_l.safetensors`, `t5xxl_fp8_e4m3fn_scaled.safetensors`, and `ae.safetensors` installed locally.
- Not done - install/test required: the committed workflow is the official reference-latent edit path; the old inpaint mask and image strength controls remain non-breaking UI inputs and are recorded as unmapped until separate local Comfy graphs are certified for those controls.

### 2026-06-27 Kontext Relight Comfy workflow block

- Current parity status: `image/kontext_relight.py` is NOT DONE ON SPEC. Needs owned Comfy Kontext/relight LoRA files, prompt/image/resolution/frames/steps/guidance/illumination/direction/seed mapping, and a real relight PNG proving the requested lighting controls are applied.

- Scaffold only: `image/kontext_relight.py` now routes `kontext-community/relighting-kontext-dev-lora-v3` through the local Comfy workflow gateway instead of direct Torch/Diffusers execution in the add-on process.
- Scaffold only: the existing prompt, image strip, resolution, frames, steps, guidance, illumination style, light direction, and seed UI sections remain present; the wrapper preserves the legacy relight prompt builder using `ILLUMINATION_OPTIONS`.
- Scaffold only: `kontext_relight` workflow pack is committed with API/editable workflow JSON, schema, model manifest, smoke payload, and README.
- Scaffold only: the workflow uses Comfy core `LoadImage`, `UNETLoader`, `LoraLoaderModelOnly`, `DualCLIPLoader`, `VAELoader`, `CLIPTextEncode`, `FluxGuidance`, `FluxKontextImageScale`, `VAEEncode`, `ReferenceLatent`, `ConditioningZeroOut`, `EmptySD3LatentImage`, `KSampler`, `VAEDecode`, and `SaveImage`.
- Scaffold only: `slopperly/config/models.yaml` now records exact local artifact sources for `flux1-dev-kontext_fp8_scaled.safetensors`, `relighting-kontext-dev-lora-v3.safetensors`, `clip_l.safetensors`, `t5xxl_fp8_e4m3fn_scaled.safetensors`, and `ae.safetensors`.
- Evidence: integration coverage calls `KontextRelightPlugin.load()`/`generate()` against a loopback fake Comfy server under the local-network guard and verifies exact graph patching plus PNG artifact collection.
- Evidence: workflow-runner integration coverage verifies the committed Relight pack directly, and `tests/gpu/test_kontext_relight.py` now performs a plugin-path certification attempt.
- Not done - install/test required: real RTX 4090 certification requires owned ComfyUI with FLUX Kontext-capable core node classes and `flux1-dev-kontext_fp8_scaled.safetensors`, `relighting-kontext-dev-lora-v3.safetensors`, `clip_l.safetensors`, `t5xxl_fp8_e4m3fn_scaled.safetensors`, and `ae.safetensors` installed locally.

### 2026-06-27 Nucleus Image Slopperly node block

- Current parity status: `image/nucleus_moe.py` is NOT DONE ON SPEC. It is a Slopperly-owned Comfy diffusers-node scaffold, not native Comfy and not a Qwen/FLUX substitute; it needs owned `slopperly_nodes`, Nucleus snapshot/FP8 patch files, prompt/negative/resolution/frames/steps/guidance/seed mapping, and a real PNG.

- Scaffold only: `image/nucleus_moe.py` now routes `NucleusAI/Nucleus-Image` through the local Comfy workflow gateway instead of direct Torch/Diffusers execution in the add-on process.
- Scaffold only: the existing prompt, negative prompt, resolution, frames, steps, guidance, and seed UI sections remain present.
- Scaffold only: the repo-local `slopperly_nodes` Comfy custom node package now exposes `SlopperlyDiffusersImageGenerate`, which wraps the existing Nucleus diffusers pipeline and pinned FP8 patch/weights inside owned ComfyUI.
- Scaffold only: the Comfy installer and `slopperly/runtime/comfy/nodes.lock.yaml` now support a `source: local` custom-node entry so owned ComfyUI can install the in-repo node package.
- Scaffold only: `nucleus_image_t2i` workflow pack is committed with API/editable workflow JSON, schema, model manifest, smoke payload, and README.
- Scaffold only: `slopperly/config/models.yaml` now records exact local artifact sources for the `NucleusAI/Nucleus-Image` snapshot and `D-Squarius-Green-Jr/Nucleus-Image-FP8` patch, config, and weights.
- Evidence: integration coverage calls `NucleusMoEPlugin.load()`/`generate()` against a loopback fake Comfy server under the local-network guard and verifies custom-node parameter patching plus PNG artifact collection.
- Evidence: workflow-runner integration coverage verifies the committed Nucleus pack directly, and `tests/gpu/test_nucleus_image.py` now performs a plugin-path certification attempt.
- Not done - install/test required: real RTX 4090 certification requires owned ComfyUI installed with `slopperly_nodes`, Diffusers dependencies, the local Nucleus snapshot, and the FP8 patch/weights present in the Slopperly model cache.

### 2026-06-27 FLUX.2 Dev GGUF quality workflow block

- Current parity status: `image/flux2_dev.py` is NOT DONE ON SPEC. This is GGUF quality-profile scaffold, not 16GB default; it needs owned Comfy GGUF/FLUX.2 files, prompt/multi-ref/resolution/frames/steps/guidance/seed mapping, real T2I and three-ref PNG artifacts, and 9-slot UI excess refs remain usage-note-only.

- Scaffold only: `image/flux2_dev.py` now routes `diffusers/FLUX.2-dev-bnb-4bit` through the local Comfy workflow gateway instead of direct Torch/Diffusers/Transformers execution and the hosted `fal/FLUX.2-dev-Turbo` LoRA load.
- Scaffold only: the existing prompt, multi-image selectors, resolution, frames, steps, guidance, and seed UI sections remain present.
- Scaffold only: `flux2_dev_gguf_quality` and `flux2_dev_gguf_quality_refs` workflow packs are committed with API/editable workflow JSON, schemas, model manifests, smoke payloads, and READMEs.
- Scaffold only: the workflows use pinned `UnetLoaderGGUF` from `city96/ComfyUI-GGUF` plus Comfy core FLUX.2 nodes; the reference workflow adds `LoadImage`, `ImageScale`, `VAEEncode`, and `ReferenceLatent`.
- Scaffold only: `slopperly/config/models.yaml` now records exact local artifact sources for `flux2-dev-Q5_K_M.gguf`, `mistral_3_small_flux2_fp8.safetensors`, and `flux2-vae.safetensors`.
- Evidence: integration coverage calls `Flux2DevPlugin.load()`/`generate()` against a loopback fake Comfy server under the local-network guard and verifies T2I patching, three-reference upload/path mapping, local filenames, and PNG artifact collection.
- Evidence: workflow-runner integration coverage verifies both committed FLUX.2 Dev packs directly, and `tests/gpu/test_flux2_dev.py` now performs T2I and three-reference plugin-path certification attempts.
- Not done - install/test required: real RTX 4090 certification requires owned ComfyUI with `UnetLoaderGGUF`, core FLUX.2 node classes, `flux2-dev-Q5_K_M.gguf`, `mistral_3_small_flux2_fp8.safetensors`, and `flux2-vae.safetensors` installed locally.
- Not done - install/test required: FLUX.2 Dev Q5 is a heavy quality profile and remains hidden until dropdown certification has a PASS artifact record for the selected device profile; the old 9-slot reference UI submits the first three certified slots and records a usage note when additional refs are selected.

### 2026-06-27 Wan2.2 TI2V-5B local default workflow block

- Current parity status: `video/wan_ti2v_5b.py` is CERTIFIED AS A NEW DIRECT LOCAL DEFAULT for the `smoke_16gb` dropdown profile. This does not count as original Palladium baseline parity for `video/wan_t2v.py`, `video/wan_i2v.py`, LTX, or removed cloud providers; those rows remain not done until their own direct local plugin-path artifacts pass.

- Scaffold only: added `video/wan_ti2v_5b.py` as the production local default for `Wan-AI/Wan2.2-TI2V-5B`, routing T2V/I2V through the local Comfy workflow gateway instead of direct Diffusers or any cloud provider.
- Scaffold only: the existing video UI contract is preserved: prompt, negative prompt, optional image strip, resolution, frames, steps, guidance, and seed.
- Scaffold only: the wrapper maps UI dimensions to the supported 720P-family sizes `1280x704` or `704x1280`, fixes output to 24fps, and patches the exact Wan Q5 GGUF, UMT5 FP8 text encoder, Wan VAE, sampler, scheduler, shift, and MP4 output profile into the workflow.
- Scaffold only: `wan22_ti2v_5b_720p24_gguf` workflow pack is committed with API/editable workflow JSON, schema, model manifest, smoke payload, and README.
- Scaffold only: the workflow uses pinned `UnetLoaderGGUF`, Comfy core `ModelSamplingSD3`, `CLIPLoader`, `CLIPTextEncode`, `VAELoader`, `Wan22ImageToVideoLatent`, `KSampler`, `VAEDecodeTiled`, and VideoHelperSuite `VHS_VideoCombine`.
- Scaffold only: optional I2V image upload is implemented through `/upload/image`; T2V mode prunes `LoadImage` and disconnects `Wan22ImageToVideoLatent.start_image` before `/object_info` validation.
- Certified: `slopperly/config/models.yaml` now records the direct local `Wan-AI/Wan2.2-TI2V-5B` artifacts, the QuantStack `Wan2.2-TI2V-5B-Q5_K_M.gguf`, Comfy-Org UMT5 FP8 text encoder, and Wan VAE files. Cloud aliases are not valid production evidence.
- Scaffold only: `slopperly/runtime/comfy/nodes.lock.yaml` now asserts `ModelSamplingSD3`, `VAEDecodeTiled`, and `Wan22ImageToVideoLatent`.
- Evidence: loopback fake-server and workflow-runner coverage exists, but the certification evidence is the real RTX 4090 plugin-path run below, not fake-server acceptance.
- Evidence: owned Slopperly ComfyUI was started from `.slopperly/runtimes/ComfyUI` on `http://127.0.0.1:8190` with API nodes disabled, CUDA 13 PyTorch, dynamic VRAM, `ComfyUI-GGUF`, and VideoHelperSuite.
- Evidence: `SLOPPERLY_COMFYUI_URL=http://127.0.0.1:8190 python -m pytest tests/gpu/test_wan22_ti2v_5b.py --device cuda --profile smoke_16gb --runtime-timeout 30 -s` passed 2 tests in 261.51s.
- Evidence: `.slopperly/certification/smoke_16gb/wan22_ti2v_5b_720p24_gguf_t2v.json` is PASS for a direct `WanTI2V5BPlugin.generate()` T2V artifact at `.slopperly/gpu-artifacts/smoke_16gb/wan22_ti2v_5b_720p24_gguf_t2v/wan22_ti2v_5b_t2v.mp4`.
- Evidence: `.slopperly/certification/smoke_16gb/wan22_ti2v_5b_720p24_gguf_i2v.json` is PASS for a direct `WanTI2V5BPlugin.generate()` I2V artifact at `.slopperly/gpu-artifacts/smoke_16gb/wan22_ti2v_5b_720p24_gguf_i2v/wan22_ti2v_5b_i2v.mp4`.
- Evidence: both generated MP4 files validate at 1280x704, 24fps, 49 frames, 2.041667s, no audio expected.
- Evidence: dropdown certification now requires separate T2V and I2V PASS records for `wan22_ti2v_5b_720p24_gguf`; `python -m slopperly.audit.dropdown_certification --profile smoke_16gb --report-only` reports `PASS wan22_ti2v_5b_720p24_gguf` and 39 blocked entries still needing real artifacts.
- Evidence: `python -m pytest tests/unit`, `python -m slopperly.audit.model_registry`, `python -m slopperly.audit.workflow_packs`, and `python -m slopperly.audit.no_cloud` passed after the certification change.
