import json
from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_image


LOGICAL_NAME = "qwen_image_edit_2511_multi_gguf"
WORKFLOW_ID = "qwen_image_edit_2511_multi_gguf"


def test_qwen_image_edit_2511_one_ref_and_three_ref(
    gpu_cert,
    plugin_loader,
    base_models,
    repo_root,
    sequence_scene_factory,
):
    one_ref = _run_qwen_image_edit_case(
        gpu_cert,
        plugin_loader,
        base_models,
        repo_root,
        prompt="make the reference image warmer with a clean studio background",
        seed=251101,
        filename="qwen_image_edit_one_ref.png",
        mode="one_ref",
    )
    three_ref = _run_qwen_image_edit_case(
        gpu_cert,
        plugin_loader,
        base_models,
        repo_root,
        prompt="edit image one using image two for material and image three for composition",
        seed=251103,
        filename="qwen_image_edit_three_ref.png",
        mode="three_ref",
        sequence_scene_factory=sequence_scene_factory,
    )

    manifest_path = gpu_cert.artifact_path(LOGICAL_NAME, "qwen_image_edit_manifest.json")
    manifest = {
        "one_ref": one_ref,
        "three_ref": three_ref,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        manifest_path,
        {
            "kind": "manifest",
            "cases": {
                "one_ref": one_ref["validation"],
                "three_ref": three_ref["validation"],
            },
        },
        metadata={
            "runtime_url": one_ref["runtime_url"],
            "workflow_pack": one_ref["workflow_pack"],
            "artifacts": {
                "one_ref": one_ref["artifact"],
                "three_ref": three_ref["artifact"],
            },
            "references": {
                "one_ref": one_ref["references"],
                "three_ref": three_ref["references"],
            },
        },
    )


def _run_qwen_image_edit_case(
    gpu_cert,
    plugin_loader,
    base_models,
    repo_root,
    *,
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
        repo_root / "slopperly" / "workflows" / "comfy" / WORKFLOW_ID / "workflow.api.json",
        "Qwen Image Edit Comfy workflow API graph",
    )
    first = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "vsr_source.ppm",
        "first Qwen Image Edit reference image fixture",
    )
    image = _load_fixture(gpu_cert, first)
    references = [str(first)]
    scene = SimpleNamespace()
    if mode == "three_ref":
        if sequence_scene_factory is None:
            gpu_cert.block(LOGICAL_NAME, "sequence scene factory is required for Qwen Image Edit three-ref test")
        second = gpu_cert.require_file(
            LOGICAL_NAME,
            repo_root / "tests" / "fixtures" / "birefnet_source.ppm",
            "second Qwen Image Edit reference image fixture",
        )
        third = gpu_cert.require_file(
            LOGICAL_NAME,
            repo_root / "tests" / "fixtures" / "vsr_source.ppm",
            "third Qwen Image Edit reference image fixture",
        )
        references.extend([str(second), str(third)])
        scene = sequence_scene_factory(
            qwen_strip_1="second",
            qwen_strip_2="third",
            qwen_strip_3="",
        )
        scene.sequence_editor.strips_all.extend([
            SimpleNamespace(name="second", type="IMAGE", filepath=str(second)),
            SimpleNamespace(name="third", type="IMAGE", filepath=str(third)),
        ])

    module = plugin_loader("image", "qwen_image_edit")
    plugin = module.QwenImageEditPlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, filename)
    module.solve_path = lambda filename: str(output_path)

    inputs = base_models.ModelInputs(
        prompt=prompt,
        neg_prompt="text, watermark, low quality",
        image=image,
        width=1024,
        height=1024,
        steps=4,
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
        gpu_cert.block(LOGICAL_NAME, f"Qwen Image Edit {mode} Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"Qwen Image Edit {mode} PNG validation failed: {exc}")

    return {
        "artifact": str(output_path),
        "mode": mode,
        "references": references,
        "runtime_url": runtime_url,
        "validation": validation,
        "workflow_pack": str(workflow_pack),
    }


def _load_fixture(gpu_cert, path):
    try:
        from PIL import Image
    except Exception as exc:
        gpu_cert.block(LOGICAL_NAME, f"Pillow is required to load image fixture: {exc}")
    return Image.open(path).convert("RGB")
