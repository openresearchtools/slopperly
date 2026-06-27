import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from slopperly.runtime.comfy.workflow_runner import ComfyWorkflowRunner
from slopperly.runtime.errors import WorkflowValidationError


SOURCE_PACK = ROOT / "slopperly/workflows/comfy/ltx23_i2v"


def _copy_pack(tmp: str) -> Path:
    pack = Path(tmp) / "ltx23_i2v"
    shutil.copytree(SOURCE_PACK, pack)
    return pack


def _mutate_workflow(pack: Path, mutator):
    path = pack / "workflow.api.json"
    workflow = json.loads(path.read_text(encoding="utf-8"))
    mutator(workflow)
    path.write_text(json.dumps(workflow, indent=2), encoding="utf-8")


class ComfyWorkflowSecurityTests(unittest.TestCase):
    def test_current_ltx23_pack_is_local_only(self):
        workflow, schema = ComfyWorkflowRunner(None).validate_pack(SOURCE_PACK)
        self.assertIn("inputs", schema)
        self.assertIn("38", workflow)

    def test_cloud_partner_node_class_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = _copy_pack(tmp)
            _mutate_workflow(
                pack,
                lambda workflow: workflow.__setitem__(
                    "99",
                    {"class_type": "FalCloudPartnerSubmit", "inputs": {"prompt": ["11", 0]}},
                ),
            )

            with self.assertRaises(WorkflowValidationError) as raised:
                ComfyWorkflowRunner(None).validate_pack(pack)

        self.assertIn("forbidden cloud/partner class", str(raised.exception))

    def test_non_local_endpoint_url_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = _copy_pack(tmp)
            cloud_url = "https://" + "queue." + "fal" + ".run/image"
            _mutate_workflow(
                pack,
                lambda workflow: workflow["11"]["inputs"].__setitem__(
                    "text",
                    f"send this to {cloud_url}",
                ),
            )

            with self.assertRaises(WorkflowValidationError) as raised:
                ComfyWorkflowRunner(None).validate_pack(pack)

        self.assertIn("forbidden cloud token", str(raised.exception))

    def test_localhost_url_is_allowed_for_self_hosted_nodes(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = _copy_pack(tmp)
            _mutate_workflow(
                pack,
                lambda workflow: workflow["11"]["inputs"].__setitem__(
                    "text",
                    "local helper http://127.0.0.1:8188/health",
                ),
            )

            workflow, _ = ComfyWorkflowRunner(None).validate_pack(pack)

        self.assertIn("127.0.0.1", workflow["11"]["inputs"]["text"])


if __name__ == "__main__":
    unittest.main()
