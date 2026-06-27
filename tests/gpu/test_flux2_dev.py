from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_image


LOGICAL_NAME = "flux2_dev_gguf_quality"
T2I_WORKFLOW_ID = "flux2_dev_gguf_quality"
REF_WORKFLOW_ID = "flux2_dev_gguf_quality_refs"


def test_flux2_dev_quality_t2i(gpu_cert, plugin_loader, base_models, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    workflow_pack = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "slopperly" / "workflows" / "comfy" / T2I_WORKFLOW_ID / "workflow.api.json",
        "FLUX.2 Dev Q5 GGUF Comfy T2I workflow API graph",
    )

    module = plugin_loader("image", "flux2_dev")
    plugin = module.Flux2DevPlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, "flux2_dev_t2i.png")
    module.solve_path = lambda filename: str(output_path)

    inputs = base_models.ModelInputs(
        prompt="a clean local FLUX.2 Dev poster reading SLOPPERLY LOCAL",
        width=1024,
        height=1024,
        steps=8,
        guidance=3.5,
        seed=420341,
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
        gpu_cert.block(LOGICAL_NAME, f"FLUX.2 Dev T2I Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"FLUX.2 Dev T2I PNG validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        output_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "workflow_pack": str(workflow_pack),
            "mode": "t2i",
            "result_path": str(result_path),
        },
    )


def test_flux2_dev_quality_three_ref(
    gpu_cert,
    plugin_loader,
    base_models,
    repo_root,
    sequence_scene_factory,
):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    workflow_pack = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "slopperly" / "workflows" / "comfy" / REF_WORKFLOW_ID / "workflow.api.json",
        "FLUX.2 Dev Q5 GGUF Comfy multi-reference workflow API graph",
    )
    source = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "vsr_source.ppm",
        "FLUX.2 Dev primary reference fixture",
    )
    reference_a = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "birefnet_source.ppm",
        "FLUX.2 Dev secondary reference fixture",
    )
    reference_b = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "vsr_source.ppm",
        "FLUX.2 Dev tertiary reference fixture",
    )
    image = _load_fixture(gpu_cert, source)

    module = plugin_loader("image", "flux2_dev")
    plugin = module.Flux2DevPlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, "flux2_dev_three_ref.png")
    module.solve_path = lambda filename: str(output_path)

    scene = sequence_scene_factory(
        flux_strip_1="second",
        flux_strip_2="third",
        flux_strip_3="",
    )
    scene.sequence_editor.strips_all.append(
        SimpleNamespace(name="second", type="IMAGE", filepath=str(reference_a))
    )
    scene.sequence_editor.strips_all.append(
        SimpleNamespace(name="third", type="IMAGE", filepath=str(reference_b))
    )
    inputs = base_models.ModelInputs(
        prompt="combine the local references into a polished product render",
        image=image,
        width=1024,
        height=1024,
        steps=8,
        guidance=3.5,
        seed=420342,
        frames=1,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, scene, prefs)
        validation = validate_image(result_path, expected_width=1024, expected_height=1024)
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"FLUX.2 Dev multi-reference Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"FLUX.2 Dev multi-reference PNG validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        output_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "workflow_pack": str(workflow_pack),
            "references": [str(source), str(reference_a), str(reference_b)],
            "mode": "multi_ref",
            "result_path": str(result_path),
        },
    )


def _load_fixture(gpu_cert, path):
    try:
        from PIL import Image
    except Exception as exc:
        gpu_cert.block(LOGICAL_NAME, f"Pillow is required to load image fixture: {exc}")
    return Image.open(path).convert("RGB")
