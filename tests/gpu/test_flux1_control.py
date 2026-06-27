from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_image


def test_flux1_canny_control(gpu_cert, plugin_loader, base_models, repo_root):
    logical_name = "flux1_canny_control"
    gpu_cert.require_cuda(logical_name)
    runtime_url = gpu_cert.require_runtime(logical_name, "comfyui", paths=("/object_info",))
    workflow_pack = gpu_cert.require_file(
        logical_name,
        repo_root / "slopperly" / "workflows" / "comfy" / logical_name / "workflow.api.json",
        "FLUX.1 Canny Comfy workflow API graph",
    )
    source = gpu_cert.require_file(
        logical_name,
        repo_root / "tests" / "fixtures" / "vsr_source.ppm",
        "FLUX.1 Canny source image fixture",
    )

    module = plugin_loader("image", "flux_canny")
    plugin = module.FluxCannyPlugin()
    output_path = gpu_cert.artifact_path(logical_name, "flux1_canny_control.png")
    module.solve_path = lambda filename: str(output_path)
    inputs = base_models.ModelInputs(
        prompt="a clean architectural render guided by local Canny edges",
        image=str(source),
        width=1024,
        height=1024,
        steps=28,
        guidance=3.5,
        strength=0.8,
        seed=610101,
        frames=1,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)
    scene = SimpleNamespace()

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, scene, prefs)
        validation = validate_image(result_path, expected_width=1024, expected_height=1024)
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(logical_name, f"FLUX.1 Canny Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(logical_name, f"FLUX.1 Canny PNG validation failed: {exc}")

    gpu_cert.pass_artifact(
        logical_name,
        output_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "workflow_pack": str(workflow_pack),
            "result_path": str(result_path),
            "source": str(source),
        },
    )


def test_flux1_depth_control(gpu_cert, plugin_loader, base_models, repo_root):
    logical_name = "flux1_depth_control"
    gpu_cert.require_cuda(logical_name)
    runtime_url = gpu_cert.require_runtime(logical_name, "comfyui", paths=("/object_info",))
    workflow_pack = gpu_cert.require_file(
        logical_name,
        repo_root / "slopperly" / "workflows" / "comfy" / logical_name / "workflow.api.json",
        "FLUX.1 Depth Comfy workflow API graph",
    )
    source = gpu_cert.require_file(
        logical_name,
        repo_root / "tests" / "fixtures" / "vsr_source.ppm",
        "FLUX.1 Depth source image fixture",
    )

    module = plugin_loader("image", "flux_depth")
    plugin = module.FluxDepthPlugin()
    output_path = gpu_cert.artifact_path(logical_name, "flux1_depth_control.png")
    module.solve_path = lambda filename: str(output_path)
    inputs = base_models.ModelInputs(
        prompt="a clean product render guided by local depth structure",
        image=str(source),
        width=1024,
        height=1024,
        steps=28,
        guidance=3.5,
        strength=0.8,
        seed=610202,
        frames=1,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)
    scene = SimpleNamespace()

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, scene, prefs)
        validation = validate_image(result_path, expected_width=1024, expected_height=1024)
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(logical_name, f"FLUX.1 Depth Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(logical_name, f"FLUX.1 Depth PNG validation failed: {exc}")

    gpu_cert.pass_artifact(
        logical_name,
        output_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "workflow_pack": str(workflow_pack),
            "result_path": str(result_path),
            "source": str(source),
        },
    )
