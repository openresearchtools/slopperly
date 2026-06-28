from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_image


LOGICAL_NAME = "omnigen_v1_multi_image"


def test_omnigen_multi_image_plugin_path(gpu_cert, plugin_loader, base_models, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    workflow_pack = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "slopperly" / "workflows" / "comfy" / LOGICAL_NAME / "workflow.api.json",
        "OmniGen Comfy workflow API graph",
    )
    first = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "vsr_source.ppm",
        "first OmniGen reference image fixture",
    )
    second = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "birefnet_source.ppm",
        "second OmniGen reference image fixture",
    )
    third = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "florence2_caption.png",
        "third OmniGen reference image fixture",
    )

    module = plugin_loader("image", "omnigen")
    plugin = module.OmniGenPlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, "omnigen_multi_image.png")
    module.solve_path = lambda filename: str(output_path)

    scene = SimpleNamespace(
        sequence_editor=SimpleNamespace(strips=[
            SimpleNamespace(name="first", type="IMAGE", filepath=str(first)),
            SimpleNamespace(name="second", type="IMAGE", filepath=str(second)),
            SimpleNamespace(name="third", type="IMAGE", filepath=str(third)),
        ]),
        omnigen_prompt_1="Create a crisp studio object image using image_1",
        omnigen_prompt_2=", borrowing the color palette from image_2",
        omnigen_prompt_3=", and placing the local-test typography from image_3",
        omnigen_strip_1="first",
        omnigen_strip_2="second",
        omnigen_strip_3="third",
        img_guidance_scale=1.6,
    )
    inputs = base_models.ModelInputs(
        prompt="local OmniGen certification",
        width=512,
        height=512,
        steps=8,
        guidance=3.0,
        seed=2026,
        frames=1,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, scene, prefs)
        validation = validate_image(result_path)
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"OmniGen Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"OmniGen PNG validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        output_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "workflow_pack": str(workflow_pack),
            "references": [str(first), str(second), str(third)],
        },
    )
