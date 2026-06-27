from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_image


LOGICAL_NAME = "flux2_klein_4b_t2i_edit"
T2I_WORKFLOW_ID = "flux2_klein_4b_t2i_edit"
EDIT_WORKFLOW_ID = "flux2_klein_4b_t2i_edit_img2img"


def test_flux2_klein_4b_t2i(gpu_cert, plugin_loader, base_models, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    workflow_pack = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "slopperly" / "workflows" / "comfy" / T2I_WORKFLOW_ID / "workflow.api.json",
        "FLUX.2 Klein 4B Comfy T2I workflow API graph",
    )

    module = plugin_loader("image", "flux2_klein_4b")
    plugin = module.Flux2Klein4BPlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, "flux2_klein_4b_t2i.png")
    module.solve_path = lambda filename: str(output_path)

    inputs = base_models.ModelInputs(
        prompt="a clean local FLUX.2 Klein 4B poster reading SLOPPERLY LOCAL",
        width=1024,
        height=1024,
        steps=4,
        guidance=1.0,
        seed=420041,
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
        gpu_cert.block(LOGICAL_NAME, f"FLUX.2 Klein 4B T2I Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"FLUX.2 Klein 4B T2I PNG validation failed: {exc}")

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


def test_flux2_klein_4b_edit(
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
        repo_root / "slopperly" / "workflows" / "comfy" / EDIT_WORKFLOW_ID / "workflow.api.json",
        "FLUX.2 Klein 4B Comfy reference-edit workflow API graph",
    )
    source = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "vsr_source.ppm",
        "FLUX.2 Klein primary edit image fixture",
    )
    reference = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "birefnet_source.ppm",
        "FLUX.2 Klein secondary reference image fixture",
    )
    image = _load_fixture(gpu_cert, source)

    module = plugin_loader("image", "flux2_klein_4b")
    plugin = module.Flux2Klein4BPlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, "flux2_klein_4b_edit.png")
    module.solve_path = lambda filename: str(output_path)

    scene = sequence_scene_factory(
        klein_strip_1="second",
        klein_strip_2="",
        klein_strip_3="",
    )
    scene.sequence_editor.strips_all.append(
        SimpleNamespace(name="second", type="IMAGE", filepath=str(reference))
    )
    inputs = base_models.ModelInputs(
        prompt="edit the object into a polished local product render",
        image=image,
        mode="img2img",
        width=1024,
        height=1024,
        steps=4,
        guidance=1.0,
        strength=0.65,
        seed=420042,
        frames=1,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, scene, prefs)
        validation = validate_image(result_path, expected_width=1024, expected_height=1024)
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"FLUX.2 Klein 4B edit Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"FLUX.2 Klein 4B edit PNG validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        output_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "workflow_pack": str(workflow_pack),
            "references": [str(source), str(reference)],
            "mode": "edit",
            "result_path": str(result_path),
        },
    )


def _load_fixture(gpu_cert, path):
    try:
        from PIL import Image
    except Exception as exc:
        gpu_cert.block(LOGICAL_NAME, f"Pillow is required to load image fixture: {exc}")
    return Image.open(path).convert("RGB")
