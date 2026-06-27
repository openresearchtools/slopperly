import base64
import tempfile
import unittest
import wave
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from slopperly.validation.artifacts import (
    ArtifactValidationError,
    validate_audio,
    validate_image,
    validate_text,
)

PNG_RGBA_2X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAIAAAABCAYAAAD0In+KAAAADUlEQVR4nGP4z8DwHwAFAAH/3fYg8QAAAABJRU5ErkJggg=="
)


def _wav(path: Path, *, silent: bool = False):
    sample = b"\0\0" if silent else b"\x20\x03"
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(sample * 1600)


class ArtifactValidatorTests(unittest.TestCase):
    def test_validate_png_dimensions_and_alpha(self):
        with tempfile.TemporaryDirectory() as tmp:
            img = Path(tmp) / "img.png"
            img.write_bytes(PNG_RGBA_2X1)
            info = validate_image(
                str(img),
                expected_width=2,
                expected_height=1,
                require_alpha=True,
            )
        self.assertEqual(info["format"], "PNG")
        self.assertTrue(info["alpha"])

    def test_validate_png_dimension_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            img = Path(tmp) / "img.png"
            img.write_bytes(PNG_RGBA_2X1)
            with self.assertRaises(ArtifactValidationError):
                validate_image(str(img), expected_width=4)

    def test_validate_wav_duration_rate_and_non_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "tone.wav"
            _wav(wav)
            info = validate_audio(
                str(wav),
                expected_duration=0.1,
                duration_tolerance=0.01,
                expected_sample_rate=16000,
            )
        self.assertGreater(info["rms"], 0.0)

    def test_validate_wav_silence_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "silence.wav"
            _wav(wav, silent=True)
            with self.assertRaises(ArtifactValidationError):
                validate_audio(str(wav), require_non_silent=True)

    def test_validate_text(self):
        info = validate_text("local generation result", forbidden_fragments=["cloud error"])
        self.assertEqual(info["kind"], "text")
        with self.assertRaises(ArtifactValidationError):
            validate_text("   ")


if __name__ == "__main__":
    unittest.main()
