import json
import wave
from pathlib import Path
from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_audio


LOGICAL_NAME = "chatterbox_multilingual_tts_comfy"


def _reference_wav(source: str, destination: Path, minimum_duration: float = 6.0) -> str:
    source_path = Path(source)
    with wave.open(str(source_path), "rb") as src:
        params = src.getparams()
        frames = src.readframes(params.nframes)
    duration = params.nframes / float(params.framerate or 1)
    if duration >= minimum_duration:
        return str(source_path)

    missing_frames = int((minimum_duration - duration) * params.framerate) + 1
    silent = b"\0" * missing_frames * params.nchannels * params.sampwidth
    destination.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destination), "wb") as dst:
        dst.setparams(params)
        dst.writeframes(frames)
        dst.writeframes(silent)
    return str(destination)


def test_chatterbox_multilingual(gpu_cert, plugin_loader, base_models):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))

    module = plugin_loader("audio", "chatterbox_multilingual")
    plugin = module.ChatterboxMultilingualPlugin()
    output_dir = gpu_cert.artifact_path(LOGICAL_NAME, "chatterbox_multilingual_manifest.json").parent
    module.solve_path = lambda filename: str(output_dir / filename)

    scene = SimpleNamespace(
        chatterbox_mtl_language="fr",
        chatterbox_multilingual_repetition_penalty=2.0,
        chatterbox_multilingual_min_p=0.05,
        chatterbox_multilingual_top_p=1.0,
        chatterbox_keep_model_loaded=True,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            plain_inputs = base_models.ModelInputs(
                prompt=(
                    "Bonjour, cette voix Chatterbox multilingue locale confirme que "
                    "le flux Slopperly fonctionne sur le runtime possede."
                ),
                exaggeration=0.5,
                pace=0.5,
                temperature=0.8,
                seed=9292,
            )
            plain_output = plugin.generate(pipe_obj, plain_inputs, scene, prefs)
            reference_input = _reference_wav(
                plain_output,
                output_dir / "chatterbox_multilingual_reference.wav",
            )

            scene.chatterbox_mtl_language = "es"
            ref_inputs = base_models.ModelInputs(
                prompt="Esta segunda voz multilingue usa una referencia local generada.",
                audio_ref=reference_input,
                exaggeration=0.55,
                pace=0.45,
                temperature=0.75,
                seed=9293,
            )
            reference_output = plugin.generate(pipe_obj, ref_inputs, scene, prefs)

        validations = {
            "multilingual_tts": validate_audio(
                plain_output,
                expected_sample_rate=24000,
                require_non_silent=True,
            ),
            "reference_input": validate_audio(
                reference_input,
                expected_sample_rate=24000,
                require_non_silent=True,
            ),
            "reference_tts": validate_audio(
                reference_output,
                expected_sample_rate=24000,
                require_non_silent=True,
            ),
        }
        manifest_path = output_dir / "chatterbox_multilingual_manifest.json"
        manifest = {
            "multilingual_tts": plain_output,
            "reference_input": reference_input,
            "reference_tts": reference_output,
            "languages": {
                "multilingual_tts": "French (fr)",
                "reference_tts": "Spanish (es)",
            },
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        validation = {
            "kind": "manifest",
            "modes": validations,
        }
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(
            LOGICAL_NAME,
            f"Chatterbox Multilingual Comfy plugin path runtime error: {exc}",
        )
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"Chatterbox Multilingual audio validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        manifest_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "multilingual_tts": plain_output,
            "reference_input": reference_input,
            "reference_tts": reference_output,
        },
    )
