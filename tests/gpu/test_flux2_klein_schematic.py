from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_image


LOGICAL_NAME = "flux2_klein_9b_schematic_lora"
WORKFLOW_ID = "flux2_klein_9b_schematic_lora"


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

    module = plugin_loader("image", "flux2_klein_9b_schematic")
    plugin = module.Flux2Klein9BSchematicPlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, "flux2_klein_schematic_depth.png")
    module.solve_path = lambda filename: str(output_path)

    scene = SimpleNamespace(
        klein_schematic_mode="DEPTH",
        klein_schematic_target="person",
    )
    inputs = base_models.ModelInputs(
        prompt="Generate a relative depth map of the input image.",
        image=str(source),
        width=1024,
        height=1024,
        steps=20,
        guidance=5.0,
        seed=420111,
        frames=1,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, scene, prefs)
        validation = validate_image(result_path, expected_width=1024, expected_height=1024)
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"FLUX.2 Klein schematic Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"FLUX.2 Klein schematic PNG validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        output_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "workflow_pack": str(workflow_pack),
            "source": str(source),
            "mode": "DEPTH",
            "result_path": str(result_path),
        },
    )
