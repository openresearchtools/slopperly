from pathlib import Path


LOGICAL_NAME = "wan22_ti2v_5b_720p24_gguf"
WORKFLOW_ID = "wan22_ti2v_5b_720p24_gguf"


def test_wan22_ti2v_5b_t2v_720p24(gpu_cert, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    _require_committed_workflow_pack(gpu_cert, repo_root)
    gpu_cert.block(
        LOGICAL_NAME,
        "Wan2.2 TI2V T2V plugin-path GPU test is not wired yet; "
        "the local default video dropdown must call the committed Comfy workflow",
    )


def test_wan22_ti2v_5b_i2v_720p24(gpu_cert, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    _require_committed_workflow_pack(gpu_cert, repo_root)
    gpu_cert.block(
        LOGICAL_NAME,
        "Wan2.2 TI2V I2V plugin-path GPU test is not wired yet; "
        "image input must flow through ModelPlugin.generate() to the local Comfy workflow",
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
