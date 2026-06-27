import json
from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_image


LOGICAL_NAME = "flux2_dev_gguf_quality"
T2I_WORKFLOW_ID = "flux2_dev_gguf_quality"
REF_WORKFLOW_ID = "flux2_dev_gguf_quality_refs"


def test_flux2_dev_quality_t2i_and_three_ref(
    gpu_cert,
    plugin_loader,
    base_models,
    repo_root,
    sequence_scene_factory,
):
    t2i = _run_flux2_dev_case(
        gpu_cert,
        plugin_loader,
        base_models,
        repo_root,
        workflow_id=T2I_WORKFLOW_ID,
        prompt="a clean local FLUX.2 Dev poster reading SLOPPERLY LOCAL",
        seed=420341,
        filename="flux2_dev_t2i.png",
        mode="t2i",
    )
    multi_ref = _run_flux2_dev_case(
        gpu_cert,
        plugin_loader,
        base_models,
        repo_root,
        workflow_id=REF_WORKFLOW_ID,
        prompt="combine the local references into a polished product render",
        seed=420342,
        filename="flux2_dev_three_ref.png",
        mode="multi_ref",
        sequence_scene_factory=sequence_scene_factory,
    )

    manifest_path = gpu_cert.artifact_path(LOGICAL_NAME, "flux2_dev_manifest.json")
    manifest = {
        "t2i": t2i,
        "multi_ref": multi_ref,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        manifest_path,
        {
            "kind": "manifest",
            "cases": {
                "t2i": t2i["validation"],
                "multi_ref": multi_ref["validation"],
            },
        },
        metadata={
            "runtime_url": t2i["runtime_url"],
            "workflow_packs": {
                "t2i": t2i["workflow_pack"],
                "multi_ref": multi_ref["workflow_pack"],
            },
            "artifacts": {
                "t2i": t2i["artifact"],
                "multi_ref": multi_ref["artifact"],
            },
            "references": multi_ref.get("references", []),
        },
    )


def _run_flux2_dev_case(
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
        f"FLUX.2 Dev Q5 GGUF Comfy {mode} workflow API graph",
    )
    image = None
    scene = SimpleNamespace()
    references = []
    if mode == "multi_ref":
        if sequence_scene_factory is None:
            gpu_cert.block(LOGICAL_NAME, "sequence scene factory is required for FLUX.2 Dev multi-reference test")
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
        references = [str(source), str(reference_a), str(reference_b)]
        image = _load_fixture(gpu_cert, source)
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

    module = plugin_loader("image", "flux2_dev")
    plugin = module.Flux2DevPlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, filename)
    module.solve_path = lambda filename: str(output_path)

    inputs = base_models.ModelInputs(
        prompt=prompt,
        image=image,
        width=1024,
        height=1024,
        steps=8,
        guidance=3.5,
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
        gpu_cert.block(LOGICAL_NAME, f"FLUX.2 Dev {mode} Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"FLUX.2 Dev {mode} PNG validation failed: {exc}")

    metadata = {
        "runtime_url": runtime_url,
        "workflow_pack": str(workflow_pack),
        "mode": mode,
        "artifact": str(output_path),
        "result_path": str(result_path),
        "validation": validation,
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
