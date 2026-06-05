import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "acp-feed" / "scripts" / "export_acp_feed.py"
FIXTURE = ROOT / "tests" / "fixtures" / "sample_catalog.json"


spec = importlib.util.spec_from_file_location("export_acp_feed", SCRIPT)
export_acp_feed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export_acp_feed)


class AcpFeedExportTest(unittest.TestCase):
    def test_export_feed_maps_catalog_to_acp_shape(self):
        catalog = json.loads(FIXTURE.read_text())
        feed, warnings = export_acp_feed.export_feed(catalog, "US", {"name": "Example"})

        self.assertEqual(warnings, [])
        self.assertEqual(feed["target_country"], "US")
        self.assertEqual(len(feed["products"]), 1)

        product = feed["products"][0]
        self.assertEqual(product["id"], "prod_1")
        self.assertEqual(product["url"], "https://example.com/products/trail%20shoe")
        self.assertEqual(product["media"][0]["url"], "https://example.com/images/trail%20shoe.jpg")

        variant = product["variants"][0]
        self.assertEqual(variant["id"], "var_1")
        self.assertEqual(variant["price"], {"amount": 9900, "currency": "USD"})
        self.assertEqual(variant["variant_options"][0], {"name": "Color", "value": "Black"})
        self.assertEqual(variant["categories"][0], {"value": "Shoes", "taxonomy": "merchant"})
        self.assertEqual(variant["seller"], {"name": "Example"})

    def test_cli_writes_feed_and_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "acp-feed.json"
            report = Path(tmp) / "acp-feed-report.md"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--input",
                    str(FIXTURE),
                    "--output",
                    str(output),
                    "--target-country",
                    "US",
                    "--report",
                    str(report),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            feed = json.loads(output.read_text())
            self.assertEqual(feed["products"][0]["variants"][0]["title"], "Black / 9")
            self.assertIn("**Products exported:** 1", report.read_text())


if __name__ == "__main__":
    unittest.main()
