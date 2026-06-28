import json
from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_image


LOGICAL_NAME = "flux2_klein_9b_t2i_edit"
T2I_WORKFLOW_ID = "flux2_klein_9b_t2i_edit"
EDIT_WORKFLOW_ID = "flux2_klein_9b_t2i_edit_img2img"


def test_flux2_klein_9b_t2i_and_edit(
    gpu_cert,
    plugin_loader,
    base_models,
    repo_root,
    sequence_scene_factory,
):
    t2i = _run_flux2_klein_case(
        gpu_cert,
        plugin_loader,
        base_models,
        repo_root,
        workflow_id=T2I_WORKFLOW_ID,
        prompt="a clean local FLUX.2 Klein 9B poster reading SLOPPERLY LOCAL",
        seed=420041,
        filename="flux2_klein_9b_t2i.png",
        mode="t2i",
    )
    edit = _run_flux2_klein_case(
        gpu_cert,
        plugin_loader,
        base_models,
        repo_root,
        workflow_id=EDIT_WORKFLOW_ID,
        prompt="edit the object into a polished local product render",
        seed=420042,
        filename="flux2_klein_9b_edit.png",
        mode="edit",
        sequence_scene_factory=sequence_scene_factory,
    )

    manifest_path = gpu_cert.artifact_path(LOGICAL_NAME, "flux2_klein_9b_manifest.json")
    manifest = {
        "t2i": t2i,
        "edit": edit,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        manifest_path,
        {
            "kind": "manifest",
            "cases": {
                "t2i": t2i["validation"],
                "edit": edit["validation"],
            },
        },
        metadata={
            "runtime_url": t2i["runtime_url"],
            "workflow_packs": {
                "t2i": t2i["workflow_pack"],
                "edit": edit["workflow_pack"],
            },
            "artifacts": {
                "t2i": t2i["artifact"],
                "edit": edit["artifact"],
            },
            "references": edit.get("references", []),
            "edit_usage_note": edit.get("usage_note", ""),
        },
    )


def _run_flux2_klein_case(
    gpu_cert,
    plugin_loader,
    base_models,
    repo_root,
    *,
    workflow_id,
    prompt,
    seed,
    filename,
    mode,
    sequence_scene_factory=None,
):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    workflow_pack = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "slopperly" / "workflows" / "comfy" / workflow_id / "workflow.api.json",
        f"FLUX.2 Klein 9B Comfy {mode} workflow API graph",
    )
    image = None
    scene = SimpleNamespace()
    references = []
    if mode == "edit":
        if sequence_scene_factory is None:
            gpu_cert.block(LOGICAL_NAME, "sequence scene factory is required for FLUX.2 Klein 9B edit test")
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
        references = [str(source), str(reference)]
        image = _load_fixture(gpu_cert, source)
        scene = sequence_scene_factory(
            klein_strip_1="second",
            klein_strip_2="",
            klein_strip_3="",
        )
        scene.sequence_editor.strips_all.append(
            SimpleNamespace(name="second", type="IMAGE", filepath=str(reference))
        )

    module = plugin_loader("image", "flux2_klein_9b")
    plugin = module.Flux2Klein9BPlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, filename)
    module.solve_path = lambda filename: str(output_path)

    inputs = base_models.ModelInputs(
        prompt=prompt,
        image=image,
        mode="img2img" if mode == "edit" else "txt2img",
        width=1024,
        height=1024,
        steps=4,
        guidance=1.0,
        strength=0.65,
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
        gpu_cert.block(LOGICAL_NAME, f"FLUX.2 Klein 9B {mode} Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"FLUX.2 Klein 9B {mode} PNG validation failed: {exc}")

    metadata = {
        "runtime_url": runtime_url,
        "workflow_pack": str(workflow_pack),
        "mode": mode,
        "artifact": str(output_path),
        "result_path": str(result_path),
        "validation": validation,
        "usage_note": getattr(inputs, "usage_note", ""),
    }
    if references:
        metadata["references"] = references
    return metadata


def _load_fixture(gpu_cert, path):
    try:
        from PIL import Image
    except Exception as exc:
        gpu_cert.block(LOGICAL_NAME, f"Pillow is required to load image fixture: {exc}")
    return Image.open(path).convert("RGB")
