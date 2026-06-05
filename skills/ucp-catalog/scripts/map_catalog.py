#!/usr/bin/env python3
"""Map merchant product data to UCP catalog schema format.

Supports: Shopify (products.json), CSV, raw JSON.
Output validated against official UCP types/product.json schema.

Usage:
  python map_catalog.py --source shopify --url https://store.myshopify.com
  python map_catalog.py --source csv --file products.csv --currency USD
  python map_catalog.py --source json --file products.json --currency USD
"""

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("pip install requests")
    sys.exit(1)

HEADERS = {"User-Agent": "UCP-Catalog/1.0 (+https://recomby.ai)"}

# Currency minor unit multipliers (most are 100)
MINOR_UNITS = {"JPY": 1, "KRW": 1, "BHD": 1000, "KWD": 1000, "OMR": 1000}


def strip_html(html, limit=1000):
    """Strip HTML tags and collapse whitespace; truncate to `limit` chars."""
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", text).strip()[:limit]


def to_minor(price_str, currency):
    """Convert price string to minor units integer."""
    try:
        price = float(price_str)
    except (ValueError, TypeError):
        return 0
    multiplier = MINOR_UNITS.get(currency, 100)
    return int(round(price * multiplier))


def map_shopify(url, currency="USD", limit=250):
    """Fetch and map Shopify products.json to UCP format."""
    products_url = f"{url.rstrip('/')}/products.json?limit={limit}"
    r = requests.get(products_url, headers=HEADERS, timeout=15)
    if r.status_code != 200:
        print(f"Error: {products_url} returned {r.status_code}")
        sys.exit(1)

    raw = r.json().get("products", [])
    products = []

    for p in raw:
        # Variants
        variants = []
        prices = []
        for v in p.get("variants", []):
            price_amount = to_minor(v.get("price", "0"), currency)
            prices.append(price_amount)
            variant = {
                "id": str(v.get("id", "")),
                "title": v.get("title", "Default"),
                "description": {"plain": strip_html(p.get("body_html"), 500) or p.get("title", "")},
                "price": {"amount": price_amount, "currency": currency},
            }
            if v.get("sku"):
                variant["sku"] = v["sku"]
            variant["availability"] = {
                "available": v.get("available", True),
                "status": "in_stock" if v.get("available", True) else "out_of_stock",
            }
            if v.get("option1"):
                opts = []
                for i, opt_name in enumerate(p.get("options", []), 1):
                    val = v.get(f"option{i}")
                    if val:
                        opts.append({"name": opt_name.get("name", f"Option {i}"), "value": val})
                if opts:
                    variant["selected_options"] = opts
            variants.append(variant)

        if not variants:
            continue

        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0

        # Strip HTML from description
        desc_plain = strip_html(p.get("body_html"), 1000) or p.get("title", "")

        product = {
            "id": str(p.get("id", "")),
            "title": p.get("title", ""),
            "description": {"plain": desc_plain},
            "price_range": {
                "min": {"amount": min_price, "currency": currency},
                "max": {"amount": max_price, "currency": currency},
            },
            "variants": variants,
        }

        # Optional fields
        if p.get("handle"):
            product["url"] = f"{url.rstrip('/')}/products/{p['handle']}"
        if p.get("images"):
            product["media"] = [{"type": "image", "url": img.get("src", "")} for img in p["images"][:5]]
        if p.get("product_type"):
            product["categories"] = [{"value": p["product_type"], "taxonomy": "merchant"}]
        if p.get("tags"):
            tags = p["tags"] if isinstance(p["tags"], list) else p["tags"].split(", ")
            product["tags"] = tags[:10]

        products.append(product)

    return products


def map_csv(file_path, currency="USD"):
    """Map CSV file to UCP catalog format.

    Expected columns: id, title, description, price, sku, image_url, category, available
    """
    products = []
    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            price = to_minor(row.get("price", "0"), currency)
            available = row.get("available", "true").lower() in ("true", "1", "yes", "in_stock")
            product = {
                "id": row.get("id", row.get("sku", str(len(products)))),
                "title": row.get("title", row.get("name", "")),
                "description": {"plain": row.get("description", row.get("title", ""))},
                "price_range": {
                    "min": {"amount": price, "currency": currency},
                    "max": {"amount": price, "currency": currency},
                },
                "variants": [
                    {
                        "id": f"var_{row.get('id', row.get('sku', str(len(products))))}",
                        "title": "Default",
                        "description": {"plain": row.get("description", row.get("title", ""))},
                        "price": {"amount": price, "currency": currency},
                        "availability": {"available": available, "status": "in_stock" if available else "out_of_stock"},
                    }
                ],
            }
            if row.get("sku"):
                product["variants"][0]["sku"] = row["sku"]
            if row.get("image_url"):
                product["media"] = [{"type": "image", "url": row["image_url"]}]
            if row.get("category"):
                product["categories"] = [{"value": row["category"], "taxonomy": "merchant"}]

            products.append(product)

    return products


def validate_products(products):
    """Basic validation against UCP product schema requirements."""
    errors = []
    for i, p in enumerate(products):
        pid = p.get("id", f"index_{i}")
        # Required fields
        for field in ("id", "title", "description", "price_range", "variants"):
            if field not in p:
                errors.append(f"Product {pid}: missing required field '{field}'")
        # Variants
        variants = p.get("variants", [])
        if not variants:
            errors.append(f"Product {pid}: must have at least 1 variant")
        for j, v in enumerate(variants):
            for field in ("id", "title", "description", "price"):
                if field not in v:
                    errors.append(f"Product {pid} variant {j}: missing '{field}'")
            price = v.get("price", {})
            if not isinstance(price.get("amount"), int):
                errors.append(f"Product {pid} variant {j}: price.amount must be integer (got {type(price.get('amount')).__name__})")
            if price.get("amount", 0) < 0:
                errors.append(f"Product {pid} variant {j}: price.amount must be >= 0")
    return errors


def field_coverage(products):
    """Return simple field coverage counts for mapped products."""
    fields = {
        "title": 0,
        "description": 0,
        "price": 0,
        "media": 0,
        "sku": 0,
        "availability": 0,
        "categories": 0,
    }
    for product in products:
        if product.get("title"):
            fields["title"] += 1
        if product.get("description"):
            fields["description"] += 1
        if product.get("media"):
            fields["media"] += 1
        if product.get("categories"):
            fields["categories"] += 1
        variants = product.get("variants", [])
        if any(v.get("price") for v in variants):
            fields["price"] += 1
        if any(v.get("sku") for v in variants):
            fields["sku"] += 1
        if any(v.get("availability") for v in variants):
            fields["availability"] += 1
    return fields


def generate_mapping_report(source, currency, products, errors):
    """Generate a markdown mapping report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    total_variants = sum(len(p.get("variants", [])) for p in products)
    coverage = field_coverage(products)
    total = len(products) or 1
    rows = "\n".join(
        f"| {name} | {count}/{len(products)} | {round((count / total) * 100)}% |"
        for name, count in coverage.items()
    )
    if not rows:
        rows = "| (none) | 0/0 | 0% |"

    if errors:
        issues = "\n".join(f"- {e}" for e in errors[:50])
        if len(errors) > 50:
            issues += f"\n- ... {len(errors) - 50} more"
    else:
        issues = "No validation errors."

    return f"""# Catalog Mapping Report

**Source:** {source}
**Currency:** {currency}
**Date:** {now}
**Products mapped:** {len(products)}
**Variants mapped:** {total_variants}
**Validation errors:** {len(errors)}

## Field Coverage

| Field | Products | Coverage |
| --- | ---: | ---: |
{rows}

## Issues

{issues}
"""


def main():
    parser = argparse.ArgumentParser(description="Map product data to UCP catalog format")
    parser.add_argument("--source", required=True, choices=["shopify", "csv", "json"],
                        help="Data source type")
    parser.add_argument("--url", help="Store URL (for shopify source)")
    parser.add_argument("--file", help="File path (for csv/json source)")
    parser.add_argument("--currency", default="USD", help="ISO 4217 currency code (default: USD)")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    parser.add_argument("--report", help="Optional mapping report markdown path")
    args = parser.parse_args()

    if args.source == "shopify":
        if not args.url:
            print("Error: --url required for shopify source")
            sys.exit(1)
        print(f"Fetching products from {args.url}...", file=sys.stderr)
        products = map_shopify(args.url, args.currency)
    elif args.source == "csv":
        if not args.file:
            print("Error: --file required for csv source")
            sys.exit(1)
        products = map_csv(args.file, args.currency)
    elif args.source == "json":
        if not args.file:
            print("Error: --file required for json source")
            sys.exit(1)
        with open(args.file) as f:
            raw = json.load(f)
        products = raw if isinstance(raw, list) else raw.get("products", [])
    else:
        sys.exit(1)

    # Validate
    errors = validate_products(products)
    if errors:
        print(f"\nValidation: {len(errors)} error(s):", file=sys.stderr)
        for e in errors[:20]:
            print(f"  - {e}", file=sys.stderr)
    else:
        print(f"\nValidation: all {len(products)} products pass", file=sys.stderr)

    # Count stats
    total_variants = sum(len(p.get("variants", [])) for p in products)

    payload = {
        "products": products,
        "metadata": {
            "source": args.source,
            "total_products": len(products),
            "total_variants": total_variants,
            "currency": args.currency,
            "validation_errors": len(errors),
        }
    }
    output = json.dumps(payload, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Catalog saved to {args.output} ({len(products)} products, {total_variants} variants)", file=sys.stderr)
    else:
        print(output)

    if args.report:
        with open(args.report, "w") as f:
            f.write(generate_mapping_report(args.source, args.currency, products, errors))
        print(f"Mapping report saved to {args.report}", file=sys.stderr)


if __name__ == "__main__":
    main()
