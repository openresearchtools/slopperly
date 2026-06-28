import json
from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_image


LOGICAL_NAME = "flux2_klein_9b_schematic_lora"
WORKFLOW_ID = "flux2_klein_9b_schematic_lora"
SCHEMATIC_CASES = (
    ("DEPTH", "Generate a relative depth map of the input image.", 420111, "flux2_klein_schematic_depth.png"),
    ("NORMAL", "Generate a surface normal map of the input image.", 420112, "flux2_klein_schematic_normal.png"),
    ("BODY_POSE", "Generate a body pose map of all visible people in the input image.", 420113, "flux2_klein_schematic_body_pose.png"),
    ("FULL_POSE", "Generate a full pose map of all visible people in the input image.", 420114, "flux2_klein_schematic_full_pose.png"),
    ("BINARY_SEG", "Generate a binary segmentation mask of person in the input image.", 420115, "flux2_klein_schematic_binary_seg.png"),
    ("AMODAL_SEG", "Generate an amodal segmentation mask of person in the input image.", 420116, "flux2_klein_schematic_amodal_seg.png"),
)


def test_flux2_klein_schematic_lora(gpu_cert, plugin_loader, base_models, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    workflow_pack = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "slopperly" / "workflows" / "comfy" / WORKFLOW_ID / "workflow.api.json",
        "FLUX.2 Klein 9B schematic LoRA Comfy workflow API graph",
    )
    source = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "vsr_source.ppm",
        "FLUX.2 Klein schematic source image fixture",
    )

    case_results = {}
    for mode, prompt, seed, filename in SCHEMATIC_CASES:
        case_results[mode] = _run_schematic_case(
            gpu_cert,
            plugin_loader,
            base_models,
            source=source,
            mode=mode,
            prompt=prompt,
            seed=seed,
            filename=filename,
            runtime_url=runtime_url,
            workflow_pack=workflow_pack,
        )

    manifest_path = gpu_cert.artifact_path(LOGICAL_NAME, "flux2_klein_schematic_manifest.json")
    manifest_path.write_text(json.dumps(case_results, indent=2, sort_keys=True), encoding="utf-8")
    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        manifest_path,
        {
            "kind": "manifest",
            "cases": {
                mode: result["validation"]
                for mode, result in case_results.items()
            },
        },
        metadata={
            "runtime_url": runtime_url,
            "workflow_pack": str(workflow_pack),
            "source": str(source),
            "modes": list(case_results.keys()),
            "artifacts": {
                mode: result["artifact"]
                for mode, result in case_results.items()
            },
        },
    )


def _run_schematic_case(
    gpu_cert,
    plugin_loader,
    base_models,
    *,
    source,
    mode,
    prompt,
    seed,
    filename,
    runtime_url,
    workflow_pack,
):
    module = plugin_loader("image", "flux2_klein_9b_schematic")
    plugin = module.Flux2Klein9BSchematicPlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, filename)
    module.solve_path = lambda _filename, path=output_path: str(path)

    scene = SimpleNamespace(
        klein_schematic_mode=mode,
        klein_schematic_target="person",
    )
    inputs = base_models.ModelInputs(
        prompt=prompt,
        image=str(source),
        width=1024,
        height=1024,
        steps=20,
        guidance=5.0,
        seed=seed,
        frames=1,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, scene, prefs)
        validation = validate_image(result_path, expected_width=1024, expected_height=1024)
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"FLUX.2 Klein schematic {mode} Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"FLUX.2 Klein schematic {mode} PNG validation failed: {exc}")

    return {
        "artifact": str(output_path),
        "mode": mode,
        "prompt": prompt,
        "result_path": str(result_path),
        "seed": seed,
        "validation": validation,
        "workflow_pack": str(workflow_pack),
    }
