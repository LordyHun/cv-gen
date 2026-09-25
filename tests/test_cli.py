import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cv_generator.cli import InputError, generate_pdf

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_MD = ROOT / "examples" / "sample_cv.md"
EXAMPLE_CSS = ROOT / "examples" / "sample_cv.css"


class GeneratePdfTests(unittest.TestCase):
    def test_generates_pdf_with_default_styles(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "cv.pdf"
            generate_pdf(EXAMPLE_MD, output)

            self.assertTrue(output.is_file())
            self.assertTrue(output.read_bytes().startswith(b"%PDF-"))
            self.assertGreater(output.stat().st_size, 5_000)

    def test_generates_pdf_with_custom_cv_styles(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "nested" / "styled.pdf"
            generate_pdf(EXAMPLE_MD, output, EXAMPLE_CSS)

            self.assertTrue(output.is_file())
            self.assertTrue(output.read_bytes().startswith(b"%PDF-"))

    def test_invalid_css_is_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            css = temp / "broken.css"
            css.write_text("h1 { color green; }", encoding="utf-8")
            output = temp / "cv.pdf"

            with self.assertRaisesRegex(InputError, "Invalid CSS"):
                generate_pdf(EXAMPLE_MD, output, css)

            self.assertFalse(output.exists())

    def test_explicit_pagebreak_is_honored(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source = temp / "cv.md"
            source.write_text(
                "# Sample CV\n\nFirst page content.\n\n<!-- pagebreak -->\n\n## Next section\n",
                encoding="utf-8",
            )
            warnings = generate_pdf(source, temp / "cv.pdf")

            self.assertEqual(warnings, [])

    def test_warns_when_css_overrides_explicit_pagebreak(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source = temp / "cv.md"
            css = temp / "style.css"
            source.write_text(
                "# Sample CV\n\nFirst page content.\n\n<!-- pagebreak -->\n\n## Next section\n",
                encoding="utf-8",
            )
            css.write_text(".cv-page-break { break-before: auto !important; }", encoding="utf-8")
            warnings = generate_pdf(source, temp / "cv.pdf", css)

            self.assertEqual(len(warnings), 1)
            self.assertIn("was not honored", warnings[0])

    def test_cli_uses_input_stem_for_default_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "sample.md"
            source.write_text("# Sample CV\n\nHello.", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "cv_generator.cli", str(source)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((Path(temp_dir) / "sample.pdf").is_file())

    def test_cli_honors_explicit_output_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source = temp / "sample.md"
            output = temp / "exports" / "resume.pdf"
            source.write_text("# Sample CV\n\nHello.", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "cv_generator.cli",
                    str(source),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.is_file())

    def test_cli_reports_missing_input(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing.md"
            result = subprocess.run(
                [sys.executable, "-m", "cv_generator.cli", str(missing)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("Markdown input not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
