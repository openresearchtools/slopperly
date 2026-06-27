from pathlib import Path


LOGICAL_NAME = "qwen_image_edit_2511_multi_gguf"
WORKFLOW_ID = "qwen_image_edit_2511_multi_gguf"


def test_qwen_image_edit_2511_one_ref(gpu_cert, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    _require_committed_workflow_pack(gpu_cert, repo_root)
    gpu_cert.block(
        LOGICAL_NAME,
        "Qwen Image Edit plugin-path GPU test is not wired yet; "
        "the existing plugin must be migrated to the local Comfy workflow before certification",
    )


def test_qwen_image_edit_2511_three_ref(gpu_cert, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    _require_committed_workflow_pack(gpu_cert, repo_root)
    gpu_cert.block(
        LOGICAL_NAME,
        "Qwen Image Edit three-reference plugin-path GPU test is not wired yet; "
        "the existing plugin must call the local Comfy workflow through ModelPlugin.generate()",
    )


def _require_committed_workflow_pack(gpu_cert, repo_root: Path):
    pack = repo_root / "slopperly" / "workflows" / "comfy" / WORKFLOW_ID
    if not pack.is_dir():
        gpu_cert.block(
            LOGICAL_NAME,
            f"required Comfy workflow pack is missing: {pack}",
            metadata={"workflow_id": WORKFLOW_ID},
        )
    return pack
