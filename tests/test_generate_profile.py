import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "ucp-profile" / "scripts" / "generate_profile.py"

spec = importlib.util.spec_from_file_location("generate_profile", SCRIPT)
generate_profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generate_profile)


class GenerateProfileTest(unittest.TestCase):
    def test_build_profile_includes_requested_capabilities(self):
        profile = generate_profile.build_profile(
            "example.com",
            "Example Store",
            "stripe",
            "rest",
            ["checkout", "catalog"],
        )
        ucp = profile["ucp"]
        self.assertEqual(ucp["version"], "2026-01-23")
        self.assertIn("dev.ucp.shopping.checkout", ucp["capabilities"])
        self.assertIn("dev.ucp.shopping.catalog.search", ucp["capabilities"])
        self.assertIn("com.stripe.payment_element", ucp["payment_handlers"])
        self.assertEqual(
            ucp["services"]["dev.ucp.shopping"][0]["endpoint"],
            "https://example.com/ucp/v1",
        )


if __name__ == "__main__":
    unittest.main()
