#!/usr/bin/env python3
"""UCP validation gate for profile, catalog, and checkout preflight checks."""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("pip install requests")
    sys.exit(1)

HEADERS = {"User-Agent": "UCP-Validate/3.0 (+https://recomby.ai)"}
TIMEOUT = 15
VERSION_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
NETWORK_TRANSPORTS = {"rest", "mcp", "a2a"}

# Offline official-schema validation against vendored UCP schemas.
SCHEMA_VERSION = "2026-04-08"
SCHEMA_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
    "refs", "ucp-schema", SCHEMA_VERSION,
)
SCHEMA_BASE = "https://ucp.local/"
PROFILE_SCHEMA_PATH = "discovery/profile_schema.json"


def build_schema_registry(schema_dir):
    """Load vendored UCP schemas into a referencing Registry keyed by file path.

    The upstream $refs resolve by file path relative to source/, not by $id, so
    we register each file under a path-based URI and drop its $id.
    """
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012

    resources = []
    for root, _, files in os.walk(schema_dir):
        for filename in files:
            if not filename.endswith(".json"):
                continue
            full = os.path.join(root, filename)
            rel = os.path.relpath(full, schema_dir).replace(os.sep, "/")
            with open(full, encoding="utf-8") as f:
                doc = json.load(f)
            doc.pop("$id", None)
            resources.append((SCHEMA_BASE + rel, Resource.from_contents(doc, default_specification=DRAFT202012)))
    return Registry().with_resources(resources)


def validate_profile_schema(data, schema_dir=SCHEMA_DIR):
    """Validate a profile dict against the vendored official UCP profile schema.

    Returns (status, detail, errors) where status is 'ok', 'fail', or 'skip'.
    Skips gracefully when jsonschema/referencing or the vendored schemas are
    unavailable, so this stays an additive, non-fatal check.
    """
    try:
        import jsonschema
        from referencing import Registry  # noqa: F401
    except ImportError:
        return "skip", "jsonschema/referencing not installed", []
    if not os.path.isdir(schema_dir):
        return "skip", f"vendored schemas not found ({schema_dir})", []
    try:
        registry = build_schema_registry(schema_dir)
        validator = jsonschema.Draft202012Validator(
            {"$ref": SCHEMA_BASE + PROFILE_SCHEMA_PATH}, registry=registry)
        errors = sorted(validator.iter_errors(data), key=lambda e: e.json_path)
    except Exception as exc:  # noqa: BLE001 - keep validation non-fatal
        return "skip", f"schema validation could not run: {exc}", []
    if errors:
        details = [f"{e.json_path or '$'}: {e.message}" for e in errors]
        return "fail", f"{len(errors)} schema error(s)", details
    return "ok", "Profile conforms to official UCP profile schema", []


def check_schema(data, checks):
    status, detail, errors = validate_profile_schema(data)
    if status == "skip":
        add_check(checks, "schema", "official profile schema", "SKIP", "INFO", detail)
    elif status == "ok":
        add_check(checks, "schema", "official profile schema", "PASS", "ERROR", f"{detail} ({SCHEMA_VERSION})")
    else:
        joined = "; ".join(errors[:3])
        add_check(checks, "schema", "official profile schema", "FAIL", "ERROR", f"{detail}: {joined}"[:400])


def add_check(checks, layer, name, status, severity, detail):
    checks.append({
        "layer": layer,
        "name": name,
        "status": status,
        "severity": severity,
        "detail": detail,
    })


def fetch_profile(base_url):
    for path in ["/.well-known/ucp", "/.well-known/ucp.json"]:
        url = base_url.rstrip("/") + path
        try:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
            if response.status_code == 200:
                return response.json(), url, None
        except Exception as exc:
            last_error = str(exc)
    return None, None, f"Profile not found at /.well-known/ucp or /.well-known/ucp.json{': ' + last_error if 'last_error' in locals() else ''}"


def load_profile(args):
    if args.profile_file:
        with open(args.profile_file, encoding="utf-8") as f:
            return json.load(f), args.profile_file, None
    return fetch_profile(args.url)


def profile_capabilities(data):
    caps = data.get("ucp", {}).get("capabilities", {})
    if isinstance(caps, dict):
        return set(caps.keys())
    if isinstance(caps, list):
        return set(str(c) for c in caps)
    return set()


def service_endpoint(data, override=None):
    if override:
        return override.rstrip("/")
    services = data.get("ucp", {}).get("services", {})
    if not isinstance(services, dict):
        return None
    entries = services.get("dev.ucp.shopping")
    if entries is None:
        for key, value in services.items():
            if "shopping" in key:
                entries = value
                break
    if entries is None:
        return None
    entries = entries if isinstance(entries, list) else [entries]
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("transport") == "rest" and entry.get("endpoint"):
            return str(entry["endpoint"]).rstrip("/")
    for entry in entries:
        if isinstance(entry, dict) and entry.get("endpoint"):
            return str(entry["endpoint"]).rstrip("/")
    return None


def request_json(method, url, payload=None):
    try:
        response = requests.request(method, url, json=payload, headers=HEADERS, timeout=TIMEOUT)
        text = response.text[:500]
        data = response.json() if response.text else None
        return response.status_code, data, text, None
    except Exception as exc:
        return None, None, "", str(exc)


def check_profile_structure(data, checks):
    if not isinstance(data, dict):
        add_check(checks, "profile", "valid object", "FAIL", "CRITICAL", "Profile root is not an object")
        return

    ucp = data.get("ucp")
    if not isinstance(ucp, dict):
        add_check(checks, "profile", "ucp root", "FAIL", "CRITICAL", "Missing 'ucp' root key")
        return
    add_check(checks, "profile", "ucp root", "PASS", "CRITICAL", "Found 'ucp' root")

    version = ucp.get("version", "")
    if VERSION_RE.match(str(version)):
        add_check(checks, "profile", "version format", "PASS", "CRITICAL", f"Version: {version}")
    else:
        add_check(checks, "profile", "version format", "FAIL", "CRITICAL", f"Version '{version}' does not match YYYY-MM-DD")

    services = ucp.get("services", {})
    if isinstance(services, dict) and services:
        add_check(checks, "profile", "services", "PASS", "CRITICAL", f"Services: {', '.join(services.keys())}")
        for service_name, raw_entries in services.items():
            entries = raw_entries if isinstance(raw_entries, list) else [raw_entries]
            for entry in entries:
                if not isinstance(entry, dict):
                    add_check(checks, "profile", f"{service_name} entry", "FAIL", "ERROR", "Service entry is not an object")
                    continue
                transport = entry.get("transport")
                if transport in NETWORK_TRANSPORTS and not entry.get("endpoint"):
                    add_check(checks, "profile", f"{service_name} endpoint", "FAIL", "ERROR", f"Transport {transport} missing endpoint")
                else:
                    add_check(checks, "profile", f"{service_name} transport", "PASS", "INFO", f"{transport or 'unknown'} at {entry.get('endpoint', 'N/A')}")
    else:
        add_check(checks, "profile", "services", "FAIL", "CRITICAL", "Missing or empty ucp.services")

    caps = ucp.get("capabilities", {})
    if isinstance(caps, dict) and caps:
        add_check(checks, "profile", "capabilities", "PASS", "ERROR", f"{len(caps)} capabilities")
        for cap_name, raw_entries in caps.items():
            if not re.match(r"^[a-z0-9]+(\.[a-z0-9_-]+)+$", cap_name):
                add_check(checks, "profile", f"capability {cap_name}", "FAIL", "ERROR", "Capability name does not follow reverse-domain style")
            entries = raw_entries if isinstance(raw_entries, list) else [raw_entries]
            for entry in entries:
                if isinstance(entry, dict) and not VERSION_RE.match(str(entry.get("version", ""))):
                    add_check(checks, "profile", f"capability {cap_name} version", "FAIL", "ERROR", "Missing or invalid version")
    elif isinstance(caps, list) and caps:
        add_check(checks, "profile", "capabilities", "WARN", "WARNING", "Capabilities are in non-standard list format")
    else:
        add_check(checks, "profile", "capabilities", "FAIL", "ERROR", "Missing or empty ucp.capabilities")

    handlers = ucp.get("payment_handlers", {})
    if isinstance(handlers, dict) and handlers:
        add_check(checks, "profile", "payment handlers", "PASS", "ERROR", f"Handlers: {', '.join(handlers.keys())}")
        for handler_name, raw_entries in handlers.items():
            entries = raw_entries if isinstance(raw_entries, list) else [raw_entries]
            for entry in entries:
                if not isinstance(entry, dict):
                    add_check(checks, "profile", f"handler {handler_name}", "FAIL", "ERROR", "Handler entry is not an object")
                    continue
                for field in ("id", "version"):
                    if not entry.get(field):
                        add_check(checks, "profile", f"handler {handler_name} {field}", "FAIL", "ERROR", f"Missing {field}")
    else:
        add_check(checks, "profile", "payment handlers", "FAIL", "ERROR", "Missing or empty ucp.payment_handlers")


def check_url_reachability(data, checks, max_checks=5):
    caps = data.get("ucp", {}).get("capabilities", {})
    if not isinstance(caps, dict):
        add_check(checks, "urls", "spec/schema urls", "SKIP", "INFO", "Capabilities are not object-shaped")
        return
    checked = 0
    for cap_name, raw_entries in caps.items():
        entries = raw_entries if isinstance(raw_entries, list) else [raw_entries]
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            for field in ("spec", "schema"):
                url = entry.get(field)
                if not url or checked >= max_checks:
                    continue
                checked += 1
                try:
                    response = requests.head(url, headers=HEADERS, timeout=10, allow_redirects=True)
                    status = "PASS" if response.status_code < 400 else "WARN"
                    severity = "WARNING" if response.status_code >= 400 else "INFO"
                    add_check(checks, "urls", f"{cap_name} {field}", status, severity, f"{url} -> {response.status_code}")
                except Exception as exc:
                    add_check(checks, "urls", f"{cap_name} {field}", "WARN", "WARNING", f"{url} -> {exc}")
    if checked == 0:
        add_check(checks, "urls", "spec/schema urls", "SKIP", "INFO", "No URLs to check")


def product_basics(product):
    if not isinstance(product, dict):
        return False, "product is not an object"
    for field in ("id", "title", "description", "variants"):
        if field not in product:
            return False, f"missing product.{field}"
    variants = product.get("variants")
    if not isinstance(variants, list) or not variants:
        return False, "missing variants"
    variant = variants[0]
    for field in ("id", "title", "description", "price"):
        if field not in variant:
            return False, f"missing variant.{field}"
    price = variant.get("price", {})
    if not isinstance(price.get("amount"), int):
        return False, "variant price.amount is not an integer"
    if not price.get("currency"):
        return False, "variant price.currency is missing"
    return True, "product basics valid"


def check_catalog(endpoint, checks):
    status, data, text, err = request_json("POST", f"{endpoint}/catalog/search", {"query": "", "limit": 2})
    if err or status is None:
        add_check(checks, "catalog", "search endpoint", "FAIL", "ERROR", err or "request failed")
        return None
    if status >= 400:
        add_check(checks, "catalog", "search endpoint", "FAIL", "ERROR", f"HTTP {status}: {text}")
        return None
    products = data.get("products") if isinstance(data, dict) else None
    if not isinstance(products, list):
        add_check(checks, "catalog", "search products", "FAIL", "ERROR", "Response missing products[]")
        return None
    add_check(checks, "catalog", "search endpoint", "PASS", "ERROR", f"Returned {len(products)} products")
    if not products:
        add_check(checks, "catalog", "search non-empty", "WARN", "WARNING", "No products returned")
        return None

    ok, detail = product_basics(products[0])
    add_check(checks, "catalog", "product schema basics", "PASS" if ok else "FAIL", "ERROR", detail)

    product_id = products[0].get("id")
    status, lookup_data, text, err = request_json("POST", f"{endpoint}/catalog/lookup", {"ids": [product_id]})
    if err or status is None:
        add_check(checks, "catalog", "lookup endpoint", "FAIL", "ERROR", err or "request failed")
    elif status >= 400:
        add_check(checks, "catalog", "lookup endpoint", "FAIL", "ERROR", f"HTTP {status}: {text}")
    else:
        lookup_products = lookup_data.get("products") if isinstance(lookup_data, dict) else None
        if isinstance(lookup_products, list) and lookup_products and lookup_products[0].get("id") == product_id:
            add_check(checks, "catalog", "lookup endpoint", "PASS", "ERROR", f"Returned {product_id}")
        else:
            add_check(checks, "catalog", "lookup endpoint", "FAIL", "ERROR", "Lookup did not return matching product")

    return products[0]


def total_count(totals, total_type):
    return sum(1 for item in totals if isinstance(item, dict) and item.get("type") == total_type)


def check_totals(totals):
    if not isinstance(totals, list):
        return False, "totals is not an array"
    if total_count(totals, "subtotal") != 1 or total_count(totals, "total") != 1:
        return False, "totals must contain exactly one subtotal and one total"
    for item in totals:
        amount = item.get("amount")
        if not isinstance(amount, int):
            return False, f"{item.get('type')} amount is not integer"
        if item.get("type") in ("discount", "items_discount") and amount >= 0:
            return False, "discount amount must be negative"
        if item.get("type") not in ("discount", "items_discount") and amount < 0:
            return False, f"{item.get('type')} amount must be non-negative"
    return True, "totals valid"


def check_checkout(endpoint, product, checks):
    if not product:
        add_check(checks, "checkout", "sample product", "SKIP", "INFO", "No catalog product available for checkout checks")
        return
    variant = product.get("variants", [{}])[0]
    payload = {
        "line_items": [
            {
                "product_id": product.get("id"),
                "variant_id": variant.get("id"),
                "quantity": 1,
            }
        ]
    }
    status, session, text, err = request_json("POST", f"{endpoint}/checkout", payload)
    if err or status is None:
        add_check(checks, "checkout", "create session", "FAIL", "ERROR", err or "request failed")
        return
    if status >= 400 or not isinstance(session, dict):
        add_check(checks, "checkout", "create session", "FAIL", "ERROR", f"HTTP {status}: {text}")
        return
    session_id = session.get("id")
    required = all(field in session for field in ("id", "status", "line_items", "currency", "totals"))
    add_check(checks, "checkout", "session required fields", "PASS" if required else "FAIL", "ERROR", f"session id {session_id}")
    add_check(checks, "checkout", "initial status", "PASS" if session.get("status") == "incomplete" else "FAIL", "ERROR", str(session.get("status")))
    ok, detail = check_totals(session.get("totals"))
    add_check(checks, "checkout", "totals structure", "PASS" if ok else "FAIL", "ERROR", detail)

    status, retrieved, text, err = request_json("GET", f"{endpoint}/checkout/{session_id}")
    add_check(
        checks,
        "checkout",
        "retrieve session",
        "PASS" if not err and status and status < 400 and isinstance(retrieved, dict) and retrieved.get("id") == session_id else "FAIL",
        "ERROR",
        err or f"HTTP {status}",
    )

    update_payload = {"line_items": [{**payload["line_items"][0], "quantity": 2}]}
    status, updated, text, err = request_json("POST", f"{endpoint}/checkout/{session_id}", update_payload)
    if not err and status and status < 400 and isinstance(updated, dict):
        ok, detail = check_totals(updated.get("totals"))
        add_check(checks, "checkout", "update session", "PASS", "ERROR", "Updated quantity")
        add_check(checks, "checkout", "updated totals", "PASS" if ok else "FAIL", "ERROR", detail)
    else:
        add_check(checks, "checkout", "update session", "FAIL", "ERROR", err or f"HTTP {status}: {text}")

    status, canceled, text, err = request_json("POST", f"{endpoint}/checkout/{session_id}/cancel", {})
    if not err and status and status < 400 and isinstance(canceled, dict) and canceled.get("status") == "canceled":
        add_check(checks, "checkout", "cancel session", "PASS", "WARNING", "Canceled")
    else:
        add_check(checks, "checkout", "cancel session", "WARN", "WARNING", err or f"HTTP {status}: {text}")


def check_official_tools(checks):
    if shutil.which("ucp-schema"):
        add_check(checks, "tools", "ucp-schema", "PASS", "INFO", "ucp-schema CLI found")
    else:
        add_check(checks, "tools", "ucp-schema", "SKIP", "INFO", "ucp-schema CLI not installed")

    conformance_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "refs", "conformance")
    if os.path.exists(conformance_path):
        add_check(checks, "tools", "conformance suite", "PASS", "INFO", f"Found at {conformance_path}")
    else:
        add_check(checks, "tools", "conformance suite", "SKIP", "INFO", "Official conformance suite not cloned")


def summarize(checks):
    counts = {"PASS": 0, "FAIL": 0, "WARN": 0, "SKIP": 0}
    for check in checks:
        counts[check["status"]] = counts.get(check["status"], 0) + 1
    critical_fail = any(c["status"] == "FAIL" and c["severity"] == "CRITICAL" for c in checks)
    error_fail = any(c["status"] == "FAIL" and c["severity"] == "ERROR" for c in checks)
    if critical_fail:
        result = "FAIL"
    elif error_fail:
        result = "CONDITIONAL PASS"
    else:
        result = "PASS"
    return {"result": result, "counts": counts}


def generate_report(url, profile_url, endpoint, checks, summary):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = "\n".join(
        f"| {c['layer']} | {c['name']} | {c['status']} | {c['severity']} | {c['detail']} |"
        for c in checks
    )
    failures = "\n".join(
        f"- [{c['layer']}] {c['name']}: {c['detail']}"
        for c in checks
        if c["status"] == "FAIL"
    ) or "No failing checks."

    return f"""# UCP Validation Report

**URL:** {url}
**Profile:** {profile_url or "not found"}
**Runtime endpoint:** {endpoint or "not tested"}
**Date:** {now}
**Result:** {summary['result']}

## Summary

| Status | Count |
| --- | ---: |
| PASS | {summary['counts'].get('PASS', 0)} |
| FAIL | {summary['counts'].get('FAIL', 0)} |
| WARN | {summary['counts'].get('WARN', 0)} |
| SKIP | {summary['counts'].get('SKIP', 0)} |

## Checks

| Layer | Check | Status | Severity | Detail |
| --- | --- | --- | --- | --- |
{rows}

## Failures

{failures}

## Next Steps

1. Fix FAIL checks before production.
2. Run official schema validation with `ucp-schema` when available.
3. Run the official conformance suite for production checkout behavior.
4. Never validate by calling checkout completion against real payment credentials.
"""


def main():
    parser = argparse.ArgumentParser(description="Validate a UCP integration")
    parser.add_argument("url", nargs="?", default="https://example.com", help="Merchant URL")
    parser.add_argument("--profile-file", help="Read profile JSON from a local file instead of fetching")
    parser.add_argument("--runtime-endpoint", help="Override UCP service endpoint for catalog/checkout checks")
    parser.add_argument("--skip-runtime", action="store_true", help="Skip catalog and checkout HTTP checks")
    parser.add_argument("--output", "-o", help="Markdown report path")
    parser.add_argument("--json-output", help="Machine-readable validation JSON path")
    args = parser.parse_args()

    if not args.url.startswith("http"):
        args.url = "https://" + args.url

    checks = []
    data, profile_url, err = load_profile(args)
    if err:
        add_check(checks, "profile", "profile fetch", "FAIL", "CRITICAL", err)
        endpoint = None
    else:
        add_check(checks, "profile", "profile fetch", "PASS", "CRITICAL", f"Loaded {profile_url}")
        check_profile_structure(data, checks)
        check_schema(data, checks)
        check_url_reachability(data, checks)
        endpoint = service_endpoint(data, args.runtime_endpoint)

        caps = profile_capabilities(data)
        if args.skip_runtime:
            add_check(checks, "runtime", "runtime checks", "SKIP", "INFO", "Skipped by --skip-runtime")
        elif not endpoint:
            add_check(checks, "runtime", "service endpoint", "SKIP", "INFO", "No runtime endpoint found")
        else:
            sample_product = None
            if any("catalog.search" in cap or "catalog.lookup" in cap for cap in caps):
                sample_product = check_catalog(endpoint, checks)
            else:
                add_check(checks, "catalog", "catalog capabilities", "SKIP", "INFO", "Catalog capability not declared")
            if any("checkout" in cap for cap in caps):
                check_checkout(endpoint, sample_product, checks)
            else:
                add_check(checks, "checkout", "checkout capability", "SKIP", "INFO", "Checkout capability not declared")

    check_official_tools(checks)
    summary = summarize(checks)
    payload = {
        "url": args.url,
        "profile": profile_url,
        "runtime_endpoint": endpoint,
        "summary": summary,
        "checks": checks,
    }
    report = generate_report(args.url, profile_url, endpoint, checks, summary)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report saved to {args.output}")
    else:
        print(report)

    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            f.write("\n")
        print(f"JSON saved to {args.json_output}")

    return 0 if summary["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
