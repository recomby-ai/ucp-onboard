#!/usr/bin/env python3
"""UCP Onboarding Pipeline — run audit/profile/catalog/validation for a merchant.

Usage:
  python run_pipeline.py https://allbirds.com --name "Allbirds" --payment shopify
  python run_pipeline.py https://example.com --name "My Store" --payment stripe --transport rest
"""

import argparse
import os
import subprocess
import sys
from urllib.parse import urlparse

SKILLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skills")


def run_script(script_path, args, step_name):
    """Run a Python script and return (success, output)."""
    cmd = [sys.executable, script_path] + args
    print(f"\n{'='*60}")
    print(f"  Step: {step_name}")
    print(f"  Command: {' '.join(cmd)}")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd, capture_output=False, text=True)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="UCP Onboarding Pipeline")
    parser.add_argument("url", help="Merchant website URL")
    parser.add_argument("--name", required=True, help="Business name")
    parser.add_argument("--payment", required=True, choices=["stripe", "shopify", "adyen"],
                        help="Payment provider")
    parser.add_argument("--transport", default="rest", choices=["rest", "mcp"],
                        help="API transport (default: rest)")
    parser.add_argument("--currency", default="USD", help="Currency code (default: USD)")
    parser.add_argument("--source", default="shopify", choices=["shopify", "csv", "json"],
                        help="Catalog data source (default: shopify)")
    parser.add_argument("--catalog-file", help="File path for csv/json catalog source")
    parser.add_argument("--export-acp", action="store_true",
                        help="Export catalog.json to OpenAI ACP feed JSON")
    parser.add_argument("--generate-checkout", action="store_true",
                        help="Generate a sandbox FastAPI UCP checkout server")
    parser.add_argument("--target-country", default="US",
                        help="Target country for ACP feed export (default: US)")
    parser.add_argument("--output-dir", help="Output directory (default: store/clients/{domain})")
    args = parser.parse_args()

    url = args.url
    if not url.startswith("http"):
        url = "https://" + url

    domain = urlparse(url).hostname.replace("www.", "")
    client_name = domain.split(".")[0]

    output_dir = args.output_dir or os.path.join("store", "clients", client_name)
    os.makedirs(output_dir, exist_ok=True)

    print(f"\nUCP Onboarding Pipeline")
    print(f"  Merchant: {args.name} ({url})")
    print(f"  Payment: {args.payment}")
    print(f"  Transport: {args.transport}")
    print(f"  Output: {output_dir}/")

    # Step 1: Audit
    audit_output = os.path.join(output_dir, "audit-report.md")
    audit_json_output = os.path.join(output_dir, "audit.json")
    ok = run_script(
        os.path.join(SKILLS_DIR, "ucp-audit", "scripts", "audit_site.py"),
        [url, "-o", audit_output, "--json-output", audit_json_output],
        "Audit website",
    )
    if not ok:
        print("\n[WARN] Audit had issues, continuing anyway...")

    # Step 2: Generate profile
    caps = "checkout,fulfillment,discount,order"
    if args.source == "shopify":
        caps = "checkout,catalog,fulfillment,discount,order"

    profile_output = os.path.join(output_dir, "ucp-profile.json")
    ok = run_script(
        os.path.join(SKILLS_DIR, "ucp-profile", "scripts", "generate_profile.py"),
        ["--domain", domain, "--name", args.name, "--payment", args.payment,
         "--transport", args.transport, "--caps", caps, "-o", profile_output],
        "Generate UCP profile",
    )
    if not ok:
        print("\n[ERROR] Profile generation failed")
        return 1

    # Step 3: Map catalog
    catalog_output = os.path.join(output_dir, "catalog.json")
    mapping_report = os.path.join(output_dir, "mapping-report.md")
    catalog_args = ["--source", args.source, "--currency", args.currency, "-o", catalog_output, "--report", mapping_report]
    if args.source == "shopify":
        catalog_args.extend(["--url", url])
    elif args.catalog_file:
        catalog_args.extend(["--file", args.catalog_file])
    else:
        print("\n[SKIP] Catalog mapping — no data source specified (use --source + --catalog-file for csv/json)")
        catalog_args = None

    if catalog_args:
        ok = run_script(
            os.path.join(SKILLS_DIR, "ucp-catalog", "scripts", "map_catalog.py"),
            catalog_args,
            "Map product catalog",
        )
        if not ok:
            print("\n[WARN] Catalog mapping had issues, continuing...")

    # Optional: Export OpenAI ACP feed
    if args.export_acp and os.path.exists(catalog_output):
        acp_output = os.path.join(output_dir, "acp-feed.json")
        ok = run_script(
            os.path.join(SKILLS_DIR, "acp-feed", "scripts", "export_acp_feed.py"),
            ["--input", catalog_output, "--output", acp_output, "--target-country", args.target_country],
            "Export OpenAI ACP feed",
        )
        if not ok:
            print("\n[WARN] ACP feed export had issues, review acp-feed-report.md")
    elif args.export_acp:
        print("\n[SKIP] ACP feed export — catalog.json was not created")

    # Optional: Generate sandbox checkout server
    if args.generate_checkout and os.path.exists(profile_output) and os.path.exists(catalog_output):
        checkout_dir = os.path.join(output_dir, "ucp-server")
        ok = run_script(
            os.path.join(SKILLS_DIR, "ucp-checkout", "scripts", "generate_api.py"),
            ["--profile", profile_output, "--catalog", catalog_output, "--output-dir", checkout_dir, "--force"],
            "Generate sandbox UCP checkout server",
        )
        if not ok:
            print("\n[WARN] Checkout server generation had issues")
    elif args.generate_checkout:
        print("\n[SKIP] Checkout server generation — profile or catalog missing")

    # Step 4: Validate
    validate_output = os.path.join(output_dir, "validation-report.md")
    validate_json_output = os.path.join(output_dir, "validation.json")
    run_script(
        os.path.join(SKILLS_DIR, "ucp-validate", "scripts", "validate_ucp.py"),
        [url, "-o", validate_output, "--json-output", validate_json_output],
        "Validate UCP integration",
    )

    # Summary
    print(f"\n{'='*60}")
    print(f"  Pipeline Complete")
    print(f"{'='*60}")
    print(f"\nDeliverables in {output_dir}/:")
    for f in sorted(os.listdir(output_dir)):
        size = os.path.getsize(os.path.join(output_dir, f))
        if size > 1024:
            print(f"  {f:30s} {size/1024:.0f}K")
        else:
            print(f"  {f:30s} {size}B")

    print(f"\nNext steps:")
    print(f"  1. Review audit-report.md for gaps")
    print(f"  2. Use audit.json and mapping-report.md for downstream automation")
    print(f"  3. Fill FILL_IN placeholders in ucp-profile.json")
    print(f"  4. Deploy profile to {domain}/.well-known/ucp")
    print(f"  5. Generate/run ucp-server for sandbox checkout preflight when needed")
    print(f"  6. If using ChatGPT Commerce, review acp-feed.json and confirm partner approval")
    print(f"  7. Run official validation: ucp-schema validate ucp-profile.json")

    return 0


if __name__ == "__main__":
    sys.exit(main())
