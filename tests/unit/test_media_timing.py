import tempfile
import unittest
import wave
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from slopperly.runtime.errors import WorkflowValidationError
from slopperly.runtime.media_timing import plan_audio_driven_video, probe_audio_duration


def _wav(path: Path, *, seconds: float, sample_rate: int = 16000):
    frames = int(seconds * sample_rate)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x01\x00" * frames)


class MediaTimingTests(unittest.TestCase):
    def test_probe_wav_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "speech.wav"
            _wav(wav_path, seconds=1.25)

            duration = probe_audio_duration(wav_path)

        self.assertAlmostEqual(duration, 1.25, places=3)

    def test_audio_driven_plan_for_16_to_24_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "dialogue.wav"
            _wav(wav_path, seconds=2.1)

            plan = plan_audio_driven_video(
                audio_path=wav_path,
                target_fps=24,
                workflow_native_fps=16,
            )

        self.assertEqual(plan.target_frames, 51)
        self.assertEqual(plan.native_frames, 34)
        self.assertEqual(plan.final_duration_seconds, plan.audio_duration_seconds)
        self.assertGreaterEqual(plan.generated_duration_seconds, plan.audio_duration_seconds)
        self.assertEqual(plan.log_fields()["target_fps"], 24.0)

    def test_requested_frames_define_duration_without_audio(self):
        plan = plan_audio_driven_video(
            requested_frames=49,
            target_fps=24,
            workflow_native_fps=24,
        )

        self.assertAlmostEqual(plan.audio_duration_seconds, 49 / 24)
        self.assertEqual(plan.target_frames, 49)
        self.assertEqual(plan.native_frames, 49)

    def test_invalid_timing_inputs_raise_diagnostics(self):
        with self.assertRaises(WorkflowValidationError):
            plan_audio_driven_video(target_fps=0, requested_frames=24)
        with self.assertRaises(WorkflowValidationError):
            plan_audio_driven_video(target_fps=24)


if __name__ == "__main__":
    unittest.main()
