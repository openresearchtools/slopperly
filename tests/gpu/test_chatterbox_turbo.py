import json
import wave
from pathlib import Path
from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_audio


LOGICAL_NAME = "chatterbox_turbo_tts_comfy"


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


def test_chatterbox_turbo(gpu_cert, plugin_loader, base_models):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))

    module = plugin_loader("audio", "chatterbox_turbo")
    plugin = module.ChatterboxTurboPlugin()
    output_dir = gpu_cert.artifact_path(LOGICAL_NAME, "chatterbox_turbo_manifest.json").parent
    module.solve_path = lambda filename: str(output_dir / filename)

    scene = SimpleNamespace(
        chatterbox_turbo_top_k=1000,
        chatterbox_turbo_top_p=0.95,
        chatterbox_turbo_repetition_penalty=1.2,
        chatterbox_keep_model_loaded=True,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            plain_inputs = base_models.ModelInputs(
                prompt=(
                    "A quick local Chatterbox Turbo voice confirms the Slopperly workflow "
                    "is running on the owned runtime. This deliberately longer sentence "
                    "creates a reference sample for the second Turbo generation path."
                ),
                audio_length=6.0,
                temperature=0.8,
                seed=9191,
            )
            plain_output = plugin.generate(pipe_obj, plain_inputs, scene, prefs)
            reference_input = _reference_wav(
                plain_output,
                output_dir / "chatterbox_turbo_reference.wav",
            )

            ref_inputs = base_models.ModelInputs(
                prompt="This Chatterbox Turbo line uses a local generated reference voice.",
                audio_ref=reference_input,
                audio_length=2.0,
                temperature=0.75,
                seed=9192,
            )
            reference_output = plugin.generate(pipe_obj, ref_inputs, scene, prefs)

        validations = {
            "prompt_tts": validate_audio(
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
        manifest_path = output_dir / "chatterbox_turbo_manifest.json"
        manifest = {
            "prompt_tts": plain_output,
            "reference_input": reference_input,
            "reference_tts": reference_output,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        validation = {
            "kind": "manifest",
            "modes": validations,
        }
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"Chatterbox Turbo Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"Chatterbox Turbo audio validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        manifest_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "prompt_tts": plain_output,
            "reference_input": reference_input,
            "reference_tts": reference_output,
        },
    )
