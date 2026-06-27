import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from slopperly.audit.dropdown_certification import audit
from slopperly.validation.certification import BLOCKED, PASS, write_certification_record


def _write_minimal_registry(
    root: Path,
    logical_name: str = "local_text",
    required_certifications: list[str] | None = None,
) -> None:
    config_dir = root / "slopperly" / "config"
    config_dir.mkdir(parents=True)
    lines = [
            "models:",
            f"  - logical_name: {logical_name}",
            "    validation_command: pytest tests/gpu/test_local_text.py --device cuda",
    ]
    if required_certifications:
        lines.append("    required_certifications:")
        lines.extend(f"      - {cert_name}" for cert_name in required_certifications)
    (config_dir / "models.yaml").write_text(
        "\n".join(lines)
        + "\n",
        encoding="utf-8",
    )
    (config_dir / "dropdown_profiles.yaml").write_text(
        "certified_dropdown_entries: {}\n",
        encoding="utf-8",
    )


class DropdownCertificationTests(unittest.TestCase):
    def test_discovered_pass_record_certifies_dropdown_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_minimal_registry(root)
            artifact = root / ".slopperly" / "gpu-artifacts" / "local_text.txt"
            artifact.parent.mkdir(parents=True)
            artifact.write_text("local output", encoding="utf-8")
            write_certification_record(
                root=root,
                profile="smoke_16gb",
                logical_name="local_text",
                status=PASS,
                command="pytest tests/gpu/test_local_text.py --device cuda",
                artifact=str(artifact),
                validation={"kind": "text", "chars": 12},
            )

            passes, failures = audit("smoke_16gb", root)

        self.assertEqual(passes, ["local_text"])
        self.assertEqual(failures, [])

    def test_blocked_record_does_not_certify_dropdown_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_minimal_registry(root)
            artifact = root / ".slopperly" / "gpu-artifacts" / "local_text.txt"
            artifact.parent.mkdir(parents=True)
            artifact.write_text("local output", encoding="utf-8")
            write_certification_record(
                root=root,
                profile="smoke_16gb",
                logical_name="local_text",
                status=BLOCKED,
                command="pytest tests/gpu/test_local_text.py --device cuda",
                artifact=str(artifact),
                reason="local runtime not reachable at http://127.0.0.1:8092",
            )

            passes, failures = audit("smoke_16gb", root)

        self.assertEqual(passes, [])
        self.assertEqual(len(failures), 1)
        self.assertIn("test result status 'BLOCKED'", failures[0])
        self.assertIn("127.0.0.1:8092", failures[0])

    def test_all_required_certifications_must_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_minimal_registry(
                root,
                logical_name="local_video",
                required_certifications=["local_video_t2v", "local_video_i2v"],
            )
            artifact = root / ".slopperly" / "gpu-artifacts" / "local_video_t2v.mp4"
            artifact.parent.mkdir(parents=True)
            artifact.write_bytes(b"mp4")
            write_certification_record(
                root=root,
                profile="smoke_16gb",
                logical_name="local_video_t2v",
                status=PASS,
                command="pytest tests/gpu/test_local_video.py --device cuda",
                artifact=str(artifact),
                validation={"kind": "video"},
            )

            passes, failures = audit("smoke_16gb", root)

        self.assertEqual(passes, [])
        self.assertEqual(len(failures), 1)
        self.assertIn("local_video", failures[0])
        self.assertIn("required certification local_video_i2v", failures[0])


if __name__ == "__main__":
    unittest.main()
