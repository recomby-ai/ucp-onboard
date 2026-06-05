import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "ucp-catalog" / "scripts" / "map_catalog.py"
CSV_FIXTURE = ROOT / "tests" / "fixtures" / "products.csv"

spec = importlib.util.spec_from_file_location("map_catalog", SCRIPT)
map_catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(map_catalog)


class MapCatalogTest(unittest.TestCase):
    def test_to_minor_uses_currency_multiplier(self):
        self.assertEqual(map_catalog.to_minor("49.99", "USD"), 4999)
        self.assertEqual(map_catalog.to_minor("500", "JPY"), 500)
        self.assertEqual(map_catalog.to_minor("1.234", "BHD"), 1234)

    def test_map_csv_and_report(self):
        products = map_catalog.map_csv(str(CSV_FIXTURE), "USD")
        errors = map_catalog.validate_products(products)
        report = map_catalog.generate_mapping_report("csv", "USD", products, errors)

        self.assertEqual(errors, [])
        self.assertEqual(products[0]["variants"][0]["price"]["amount"], 4999)
        self.assertIn("Products mapped:** 1", report)
        self.assertIn("| title | 1/1 | 100% |", report)


if __name__ == "__main__":
    unittest.main()
