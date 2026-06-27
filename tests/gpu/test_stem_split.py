import json
from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_audio


LOGICAL_NAME = "audio_stem_split_demucs"


def test_stem_split(gpu_cert, plugin_loader, base_models, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    audio_path = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "stem_split_source.wav",
        "stem split WAV fixture",
    )

    module = plugin_loader("audio", "stem_split")
    plugin = module.StemSplitterPlugin()
    output_dir = gpu_cert.artifact_path(LOGICAL_NAME, "stems_manifest.json").parent
    module.solve_path = lambda filename: str(output_dir / filename)

    scene = SimpleNamespace(
        stem_split_model="htdemucs_ft",
        stem_split_vocals=True,
        stem_split_drums=True,
        stem_split_bass=True,
        stem_split_other=True,
        stem_split_guitar=False,
        stem_split_piano=False,
    )
    inputs = base_models.ModelInputs(audio_ref=str(audio_path))
    inputs.output_basename = "stem_split_source"
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            result = plugin.generate(pipe_obj, inputs, scene, prefs)
        if not result.startswith(module._MULTI_STEM_PREFIX):
            gpu_cert.fail(LOGICAL_NAME, "Stem splitter did not return MULTI_STEM payload")
        stems = json.loads(result[len(module._MULTI_STEM_PREFIX):])
        expected = ["vocals", "drums", "bass", "other"]
        if list(stems) != expected:
            gpu_cert.fail(LOGICAL_NAME, f"Stem payload keys {list(stems)} != {expected}")
        validation = {
            stem: validate_audio(
                path,
                expected_duration=1.0,
                duration_tolerance=0.3,
                expected_sample_rate=44100,
                require_non_silent=False,
            )
            for stem, path in stems.items()
        }
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"Stem split Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"Stem split audio validation failed: {exc}")

    manifest = output_dir / "stems_manifest.json"
    manifest.write_text(
        json.dumps({"stems": stems, "validation": validation}, indent=2),
        encoding="utf-8",
    )
    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        manifest,
        {"kind": "audio_stems", "stems": validation},
        metadata={"runtime_url": runtime_url, "source_audio": str(audio_path), "stem_paths": stems},
    )
