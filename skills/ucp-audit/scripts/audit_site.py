#!/usr/bin/env python3
"""UCP Readiness Audit — scans a merchant website and scores UCP readiness."""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Install dependencies: pip install requests beautifulsoup4")
    sys.exit(1)

HEADERS = {"User-Agent": "UCP-Audit/1.0 (+https://recomby.ai)"}
TIMEOUT = 15


def fetch(url):
    """Fetch URL, return (response, error)."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        return r, None
    except Exception as e:
        return None, str(e)


def check_ucp_profile(base_url):
    """Check if /.well-known/ucp exists and is valid."""
    result = {
        "has_ucp_profile": False,
        "ucp_capabilities": [],
        "ucp_version": None,
        "ucp_payment_handlers": [],
        "ucp_transports": [],
        "profile_errors": [],
        "profile_url": None,
    }

    # Try standard path, then .json variant
    for path in ["/.well-known/ucp", "/.well-known/ucp.json"]:
        url = urljoin(base_url, path)
        r, err = fetch(url)
        if err or r.status_code != 200:
            continue
        try:
            data = r.json()
        except json.JSONDecodeError:
            result["profile_errors"].append(f"{path}: Response is not valid JSON")
            continue

        result["has_ucp_profile"] = True
        result["profile_url"] = path
        ucp = data.get("ucp", {})
        result["ucp_version"] = ucp.get("version")

        # Capabilities — handle both object format and array format
        caps = ucp.get("capabilities", {})
        if isinstance(caps, dict):
            result["ucp_capabilities"] = list(caps.keys())
        elif isinstance(caps, list):
            result["ucp_capabilities"] = caps

        # Payment handlers from profile (not just HTML detection)
        handlers = ucp.get("payment_handlers", {})
        if isinstance(handlers, dict):
            result["ucp_payment_handlers"] = list(handlers.keys())

        # Transport types
        services = ucp.get("services", {})
        for svc_name, svc_entries in services.items():
            entries = svc_entries if isinstance(svc_entries, list) else [svc_entries]
            for entry in entries:
                t = entry.get("transport", "")
                if t and t not in result["ucp_transports"]:
                    result["ucp_transports"].append(t)

        if not ucp.get("version"):
            result["profile_errors"].append("Missing ucp.version")
        if not ucp.get("services"):
            result["profile_errors"].append("Missing ucp.services")
        if not ucp.get("payment_handlers"):
            result["profile_errors"].append("Missing ucp.payment_handlers")
        break  # Found a valid profile, stop trying

    return result


PLATFORM_SIGS = {
    "shopify": [
        lambda h, b: "x-shopify-stage" in (h or {}),
        lambda h, b: "cdn.shopify.com" in b,
        lambda h, b: "Shopify.theme" in b,
    ],
    "woocommerce": [
        lambda h, b: "wc-ajax" in b,
        lambda h, b: "woocommerce" in b.lower(),
        lambda h, b: "/wp-content/plugins/woocommerce/" in b,
    ],
    "magento": [
        lambda h, b: "mage/" in b.lower(),
        lambda h, b: "Magento_" in b,
    ],
    "bigcommerce": [
        lambda h, b: "bigcommerce.com" in b,
        lambda h, b: "data-content-region" in b,
    ],
}


def detect_platform(response):
    """Detect e-commerce platform from response."""
    if not response:
        return "unknown", "low"
    headers = {k.lower(): v for k, v in response.headers.items()}
    body = response.text

    for platform, checks in PLATFORM_SIGS.items():
        matches = sum(1 for check in checks if check(headers, body))
        if matches >= 2:
            return platform, "high"
        if matches == 1:
            return platform, "medium"

    return "custom", "low"


def extract_structured_data(soup):
    """Extract JSON-LD, Open Graph, and microdata from HTML."""
    result = {
        "types_found": [],
        "json_ld": [],
        "opengraph": {},
        "product_fields": {},
    }

    # JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            items = data if isinstance(data, list) else [data]
            for item in items:
                t = item.get("@type", "")
                if t:
                    result["json_ld"].append(t)
                if t == "Product":
                    result["types_found"].append("json-ld:Product")
                    if item.get("name"):
                        result["product_fields"]["title"] = "json-ld:name"
                    if item.get("description"):
                        result["product_fields"]["description"] = "json-ld:description"
                    if item.get("image"):
                        result["product_fields"]["media"] = "json-ld:image"
                    if item.get("sku"):
                        result["product_fields"]["sku"] = "json-ld:sku"
                    offers = item.get("offers", {})
                    if isinstance(offers, list):
                        offers = offers[0] if offers else {}
                    if offers.get("price"):
                        result["product_fields"]["price"] = "json-ld:offers.price"
                    if offers.get("priceCurrency"):
                        result["product_fields"]["currency"] = "json-ld:offers.priceCurrency"
                    if offers.get("availability"):
                        result["product_fields"]["availability"] = "json-ld:offers.availability"
        except (json.JSONDecodeError, TypeError):
            continue

    # Open Graph
    for meta in soup.find_all("meta", attrs={"property": re.compile(r"^og:")}):
        prop = meta.get("property", "")
        content = meta.get("content", "")
        result["opengraph"][prop] = content
        if prop == "og:title":
            result["product_fields"].setdefault("title", "og:title")
        if prop == "og:description":
            result["product_fields"].setdefault("description", "og:description")
        if prop == "og:image":
            result["product_fields"].setdefault("media", "og:image")

    # Product meta tags
    for meta in soup.find_all("meta", attrs={"property": re.compile(r"^product:")}):
        prop = meta.get("property", "")
        if "price:amount" in prop:
            result["product_fields"].setdefault("price", "meta:product:price:amount")
        if "price:currency" in prop:
            result["product_fields"].setdefault("currency", "meta:product:price:currency")

    if result["opengraph"]:
        result["types_found"].append("opengraph")

    # Microdata
    if soup.find(attrs={"itemtype": re.compile(r"schema.org/Product")}):
        result["types_found"].append("microdata:Product")

    return result


PAYMENT_SIGS = {
    "stripe": ["js.stripe.com", "stripe.com/v3"],
    "paypal": ["paypal.com/sdk", "paypalobjects.com"],
    "adyen": ["adyen.com"],
    "square": ["squareup.com", "square.com/web-payments"],
    "braintree": ["braintreegateway.com"],
    "klarna": ["klarna.com"],
}

UCP_COMPATIBLE_PROVIDERS = {"stripe", "adyen", "square"}


def detect_payments(body):
    """Detect payment providers from page HTML."""
    found = []
    for provider, signatures in PAYMENT_SIGS.items():
        if any(sig in body for sig in signatures):
            found.append(provider)
    return found


def check_api(base_url, platform):
    """Check if a public product API is accessible."""
    if platform == "shopify":
        url = urljoin(base_url, "/products.json?limit=1")
        r, err = fetch(url)
        if r and r.status_code == 200:
            return True, "storefront"
    elif platform == "woocommerce":
        url = urljoin(base_url, "/wp-json/wc/v3/products")
        r, err = fetch(url)
        if r and r.status_code in (200, 401):  # 401 = exists but needs auth
            return True, "rest"

    return False, "none"


def calculate_score(profile, platform, structured, payments, has_api, secure=True):
    """Calculate UCP readiness score (0-100)."""
    score = 0

    # Combine payment sources: HTML detection + profile handlers
    all_payments = list(payments)
    for h in profile.get("ucp_payment_handlers", []):
        # Extract provider name from handler namespace
        # com.google.pay → google, dev.shopify.card → shopify, com.stripe.* → stripe
        parts = h.split(".")
        if len(parts) >= 2:
            provider = parts[1] if parts[0] in ("com", "dev") else parts[0]
            if provider not in all_payments:
                all_payments.append(provider)

    # Profile (20 + 10 + 10)
    if profile["has_ucp_profile"]:
        score += 20
        if any("checkout" in c for c in profile["ucp_capabilities"]):
            score += 10
        if any("catalog" in c for c in profile["ucp_capabilities"]):
            score += 10

    # Structured data (15)
    if any("Product" in t for t in structured["types_found"]):
        score += 15

    # Product fields (10)
    required = {"title", "price", "description", "media"}
    available = set(structured["product_fields"].keys())
    if required <= available:
        score += 10

    # Payment (15 + 5) — from HTML detection OR profile payment_handlers
    if all_payments:
        score += 15
        ucp_compatible = UCP_COMPATIBLE_PROVIDERS | {"google", "shopify"}
        if any(p in ucp_compatible for p in all_payments):
            score += 5

    # API (10)
    if has_api:
        score += 10

    # HTTPS (5)
    if secure:
        score += 5

    return score


def generate_report(url, profile, platform, structured, payments, has_api, api_type, score, secure=True):
    """Generate markdown audit report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    domain = urlparse(url).hostname

    # Assessment
    if score >= 80:
        assessment = "Excellent — this site is close to UCP-ready. Minor gaps to fill."
    elif score >= 50:
        assessment = "Moderate — foundational data exists but significant integration work needed."
    elif score >= 20:
        assessment = "Early stage — some reusable assets but most UCP components need to be built."
    else:
        assessment = "Starting from scratch — no existing UCP-compatible infrastructure detected."

    # Reusable assets
    assets_rows = ""
    for ucp_field, source in structured["product_fields"].items():
        assets_rows += f"| {ucp_field} | {source} | Ready to map |\n"
    if not assets_rows:
        assets_rows = "| (none found) | — | — |\n"

    # Missing items
    missing = []
    if not profile["has_ucp_profile"]:
        missing.append("**/.well-known/ucp profile** — No UCP business profile found. This is the entry point for AI agent discovery.")
    required_fields = {"title", "price", "description", "media"}
    missing_fields = required_fields - set(structured["product_fields"].keys())
    for f in missing_fields:
        missing.append(f"**Product {f}** — Not found in structured data. Needs to be added to product pages or pulled from API.")
    # Combine payment sources
    all_payments = list(payments)
    for h in profile.get("ucp_payment_handlers", []):
        parts = h.split(".")
        if len(parts) >= 2:
            provider = parts[1] if parts[0] in ("com", "dev") else parts[0]
            if provider not in all_payments:
                all_payments.append(provider)

    if not all_payments:
        missing.append("**Payment provider** — No recognized payment provider detected in HTML or UCP profile. UCP requires at least one payment handler.")
    if not has_api:
        missing.append("**Product API** — No public product API found. Catalog data will need to be scraped or exported manually.")

    missing_text = "\n".join(f"{i+1}. {m}" for i, m in enumerate(missing)) if missing else "No critical gaps found."

    # Integration path
    if platform[0] == "shopify":
        path = """1. Generate UCP profile with `ucp-profile` skill
2. Map Shopify products.json to UCP catalog with `ucp-catalog`
3. Deploy a lightweight API proxy (Cloudflare Worker or Vercel Edge Function)
4. Host /.well-known/ucp via the proxy
5. Validate with `ucp-validate`"""
    elif platform[0] == "woocommerce":
        path = """1. Generate UCP profile with `ucp-profile` skill
2. Export WooCommerce products to CSV or add an authenticated WooCommerce connector
3. Map exported products to catalog.json with `ucp-catalog`
4. Deploy alongside existing WordPress installation
5. Validate with `ucp-validate`"""
    else:
        path = """1. Run `ucp-audit` to identify reusable data assets (done)
2. Generate UCP profile with `ucp-profile` skill
3. Export product data to CSV, map with `ucp-catalog`
4. Implement checkout API using `ucp-checkout` guidance
5. Deploy API and /.well-known/ucp profile
6. Validate with `ucp-validate`"""

    report = f"""# UCP Readiness Audit — {domain}

**URL:** {url}
**Date:** {now}
**Score:** {score}/100

## Summary
{assessment}

## Platform
- **Detected:** {platform[0]} ({platform[1]} confidence)
- **Payment (HTML):** {", ".join(payments) if payments else "None in HTML"}
- **Payment (UCP profile):** {", ".join(profile.get("ucp_payment_handlers", [])) if profile.get("ucp_payment_handlers") else "N/A"}
- **Transport:** {", ".join(profile.get("ucp_transports", [])) if profile.get("ucp_transports") else "N/A"}
- **Product API:** {"Yes (" + api_type + ")" if has_api else "Not found"}

## UCP Profile Status
{"✅ Profile exists at " + str(profile.get("profile_url", "/.well-known/ucp")) + " (version: " + str(profile["ucp_version"]) + ")" if profile["has_ucp_profile"] else "❌ No UCP profile found"}
{"- Capabilities: " + ", ".join(profile["ucp_capabilities"]) if profile["ucp_capabilities"] else ""}
{"- Errors: " + ", ".join(profile["profile_errors"]) if profile["profile_errors"] else ""}

## What You Already Have (Reusable Assets)
| UCP Field | Source | Status |
|-----------|--------|--------|
{assets_rows}

## What's Missing
{missing_text}

## Recommended Integration Path
{path}

## Score Breakdown
| Check | Points | Status |
|-------|--------|--------|
| UCP profile exists | 20 | {"✅" if profile["has_ucp_profile"] else "❌"} |
| Has checkout capability | 10 | {"✅" if any("checkout" in c for c in profile["ucp_capabilities"]) else "❌"} |
| Has catalog capability | 10 | {"✅" if any("catalog" in c for c in profile["ucp_capabilities"]) else "❌"} |
| Structured product data | 15 | {"✅" if any("Product" in t for t in structured["types_found"]) else "❌"} |
| All required product fields | 10 | {"✅" if required_fields <= set(structured["product_fields"].keys()) else "❌"} |
| Payment provider detected | 15 | {"✅" if all_payments else "❌"} |
| UCP-compatible provider | 5 | {"✅" if any(p in (UCP_COMPATIBLE_PROVIDERS | {"google", "shopify"}) for p in all_payments) else "❌"} |
| Public product API | 10 | {"✅" if has_api else "❌"} |
| HTTPS enabled | 5 | {"✅" if secure else "❌"} |
| **Total** | **{score}** | |
"""
    return report


def main():
    parser = argparse.ArgumentParser(description="UCP Readiness Audit")
    parser.add_argument("url", help="Merchant website URL")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    parser.add_argument("--json-output", help="Optional machine-readable JSON output file")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of markdown")
    args = parser.parse_args()

    url = args.url
    if not url.startswith("http"):
        url = "https://" + url

    # Ensure trailing slash for urljoin
    if not urlparse(url).path:
        url += "/"

    print(f"Auditing {url} ...")

    # Step 1: UCP Profile
    print("  [1/5] Checking UCP profile...")
    profile = check_ucp_profile(url)

    # Step 2: Platform detection
    print("  [2/5] Detecting platform...")
    r, _ = fetch(url)
    platform = detect_platform(r)

    # Step 3: Structured data
    print("  [3/5] Scanning structured data...")
    soup = BeautifulSoup(r.text if r else "", "html.parser") if r else BeautifulSoup("", "html.parser")
    structured = extract_structured_data(soup)

    # Try to find and scan a product page
    product_links = []
    if r:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if any(p in href for p in ["/products/", "/product/", "/shop/", "/item/"]):
                full_url = urljoin(url, href)
                if full_url not in product_links and urlparse(full_url).hostname == urlparse(url).hostname:
                    product_links.append(full_url)
                if len(product_links) >= 2:
                    break

    # Fetch each product page once, then reuse its HTML for both structured
    # data extraction and payment detection.
    product_pages = []
    for plink in product_links:
        pr, _ = fetch(plink)
        if pr:
            product_pages.append(pr.text)

    for page_text in product_pages:
        psoup = BeautifulSoup(page_text, "html.parser")
        pdata = extract_structured_data(psoup)
        # Merge product fields
        for k, v in pdata["product_fields"].items():
            structured["product_fields"].setdefault(k, v)
        for t in pdata["types_found"]:
            if t not in structured["types_found"]:
                structured["types_found"].append(t)

    # Step 4: Payment detection
    print("  [4/5] Detecting payment methods...")
    body = (r.text if r else "") + "".join(product_pages)
    payments = detect_payments(body)

    # Step 5: API check
    print("  [5/5] Checking API accessibility...")
    has_api, api_type = check_api(url, platform[0])

    # Calculate score
    secure = urlparse(url).scheme == "https"
    score = calculate_score(profile, platform[0], structured, payments, has_api, secure)
    result_data = {
        "url": url,
        "score": score,
        "profile": profile,
        "platform": {"name": platform[0], "confidence": platform[1]},
        "structured_data": structured,
        "payments": payments,
        "api": {"available": has_api, "type": api_type},
    }

    if args.json:
        output = json.dumps(result_data, indent=2)
    else:
        output = generate_report(url, profile, platform, structured, payments, has_api, api_type, score, secure)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"\nReport saved to {args.output}")
    else:
        print("\n" + output)

    if args.json_output:
        with open(args.json_output, "w") as f:
            json.dump(result_data, f, indent=2)
            f.write("\n")
        print(f"JSON saved to {args.json_output}")

    print(f"\nScore: {score}/100")
    return 0 if score > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
