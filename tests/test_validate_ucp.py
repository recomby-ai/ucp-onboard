import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "ucp-validate" / "scripts" / "validate_ucp.py"
PROFILE = ROOT / "tests" / "fixtures" / "sample_profile.json"
CATALOG = ROOT / "tests" / "fixtures" / "sample_catalog.json"

spec = importlib.util.spec_from_file_location("validate_ucp", SCRIPT)
validate_ucp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate_ucp)


class ValidateUcpTest(unittest.TestCase):
    def test_profile_structure_passes_basics(self):
        checks = []
        profile = json.loads(PROFILE.read_text())
        validate_ucp.check_profile_structure(profile, checks)
        failing = [c for c in checks if c["status"] == "FAIL"]
        self.assertEqual(failing, [])
        self.assertEqual(
            validate_ucp.service_endpoint(profile),
            "http://localhost:8000/ucp/v1",
        )

    def test_product_and_totals_basics(self):
        product = json.loads(CATALOG.read_text())["products"][0]
        ok, detail = validate_ucp.product_basics(product)
        self.assertTrue(ok, detail)

        ok, detail = validate_ucp.check_totals([
            {"type": "subtotal", "amount": 1000},
            {"type": "total", "amount": 1000},
        ])
        self.assertTrue(ok, detail)

    def test_summary_conditional_pass_on_error_fail(self):
        checks = []
        validate_ucp.add_check(checks, "checkout", "totals", "FAIL", "ERROR", "bad")
        summary = validate_ucp.summarize(checks)
        self.assertEqual(summary["result"], "CONDITIONAL PASS")

    def test_official_schema_validation(self):
        try:
            import jsonschema  # noqa: F401
        except ImportError:
            self.skipTest("jsonschema not installed")
        if not Path(validate_ucp.SCHEMA_DIR).is_dir():
            self.skipTest("vendored schemas not present")

        profile = json.loads(PROFILE.read_text())
        status, detail, errors = validate_ucp.validate_profile_schema(profile)
        self.assertEqual(status, "ok", f"{detail} {errors}")

        status, detail, _ = validate_ucp.validate_profile_schema({"ucp": {"version": "bad"}})
        self.assertEqual(status, "fail", detail)


if __name__ == "__main__":
    unittest.main()
