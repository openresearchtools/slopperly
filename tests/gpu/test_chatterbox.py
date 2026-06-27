import json
from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_audio


LOGICAL_NAME = "chatterbox_tts_vc_comfy"


def test_chatterbox(gpu_cert, plugin_loader, base_models):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))

    module = plugin_loader("audio", "chatterbox")
    plugin = module.ChatterboxPlugin()
    output_dir = gpu_cert.artifact_path(LOGICAL_NAME, "chatterbox_manifest.json").parent
    module.solve_path = lambda filename: str(output_dir / filename)

    scene = SimpleNamespace(chatterbox_keep_model_loaded=True)
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            plain_inputs = base_models.ModelInputs(
                prompt="A calm local Chatterbox voice confirms the Slopperly workflow is running.",
                audio_length=2.0,
                exaggeration=0.5,
                pace=0.5,
                temperature=0.8,
                seed=9090,
            )
            plain_output = plugin.generate(pipe_obj, plain_inputs, scene, prefs)

            ref_inputs = base_models.ModelInputs(
                prompt="This second local Chatterbox line uses the generated reference voice.",
                audio_ref=plain_output,
                audio_length=2.0,
                exaggeration=0.55,
                pace=0.45,
                temperature=0.75,
                seed=9091,
            )
            reference_output = plugin.generate(pipe_obj, ref_inputs, scene, prefs)

            vc_inputs = base_models.ModelInputs(
                audio_ref=plain_output,
                is_voice_clone=True,
                seed=9092,
            )
            vc_output = plugin.generate(pipe_obj, vc_inputs, scene, prefs)

        validations = {
            "plain_tts": validate_audio(
                plain_output,
                expected_sample_rate=24000,
                require_non_silent=True,
            ),
            "reference_tts": validate_audio(
                reference_output,
                expected_sample_rate=24000,
                require_non_silent=True,
            ),
            "voice_conversion": validate_audio(
                vc_output,
                expected_sample_rate=24000,
                require_non_silent=True,
            ),
        }
        manifest_path = output_dir / "chatterbox_manifest.json"
        vc_usage_note = vc_inputs.usage_note or ""
        manifest = {
            "plain_tts": plain_output,
            "reference_tts": reference_output,
            "voice_conversion": vc_output,
            "voice_conversion_usage_note": vc_usage_note,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        if "legacy single audio picker" not in vc_usage_note:
            gpu_cert.fail(LOGICAL_NAME, "Chatterbox VC compatibility usage note was not recorded")
        validation = {
            "kind": "manifest",
            "modes": validations,
        }
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"Chatterbox Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"Chatterbox audio validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        manifest_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "plain_tts": plain_output,
            "reference_tts": reference_output,
            "voice_conversion": vc_output,
        },
    )
