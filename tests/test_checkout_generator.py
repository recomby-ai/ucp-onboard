import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "ucp-checkout" / "scripts" / "generate_api.py"
PROFILE = ROOT / "tests" / "fixtures" / "sample_profile.json"
CATALOG = ROOT / "tests" / "fixtures" / "sample_catalog.json"


class CheckoutGeneratorTest(unittest.TestCase):
    def test_generator_writes_fastapi_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "ucp-server"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--profile",
                    str(PROFILE),
                    "--catalog",
                    str(CATALOG),
                    "--output-dir",
                    str(out),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((out / "app" / "main.py").exists())
            self.assertTrue((out / "requirements.txt").exists())
            copied = json.loads((out / "app" / "data" / "catalog.json").read_text())
            self.assertEqual(copied["products"][0]["id"], "prod_1")
            self.assertIn("checkout_create", (out / "app" / "main.py").read_text())


if __name__ == "__main__":
    unittest.main()
