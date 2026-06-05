#!/usr/bin/env python3
"""Export a UCP-style catalog JSON file to an OpenAI ACP product feed payload."""

import argparse
import json
import sys
from datetime import datetime, timezone
from urllib.parse import quote, urlsplit, urlunsplit


def clean_text(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_url(value):
    value = clean_text(value)
    if not value:
        return None
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return None
    path = quote(parts.path, safe="/%:@")
    query = quote(parts.query, safe="=&%:@,;+?")
    fragment = quote(parts.fragment, safe="")
    return urlunsplit((parts.scheme, parts.netloc, path, query, fragment))


def normalize_description(value):
    if isinstance(value, dict):
        result = {}
        for key in ("plain", "html", "markdown"):
            text = clean_text(value.get(key))
            if text:
                result[key] = text
        return result or None
    text = clean_text(value)
    return {"plain": text} if text else None


def normalize_media(media):
    result = []
    for item in media or []:
        if not isinstance(item, dict):
            continue
        url = normalize_url(item.get("url"))
        if not url:
            continue
        normalized = {"url": url}
        media_type = clean_text(item.get("type"))
        if media_type:
            normalized["type"] = media_type
        alt = clean_text(item.get("alt"))
        if alt:
            normalized["alt"] = alt
        result.append(normalized)
    return result


def normalize_price(price, warnings, context):
    if not isinstance(price, dict):
        return None
    amount = price.get("amount")
    currency = clean_text(price.get("currency"))
    if amount is None and not currency:
        return None
    if not isinstance(amount, int):
        warnings.append(f"{context}: price.amount must be an integer in minor units")
        return None
    if not currency or len(currency) != 3:
        warnings.append(f"{context}: price.currency must be a three-letter ISO 4217 code")
        return None
    return {"amount": amount, "currency": currency.upper()}


def normalize_categories(categories):
    result = []
    for item in categories or []:
        if isinstance(item, dict):
            value = clean_text(item.get("value") or item.get("name"))
            if not value:
                continue
            normalized = {"value": value}
            taxonomy = clean_text(item.get("taxonomy"))
            if taxonomy:
                normalized["taxonomy"] = taxonomy
            result.append(normalized)
        else:
            value = clean_text(item)
            if value:
                result.append({"value": value, "taxonomy": "merchant"})
    return result


def normalize_options(variant):
    source = variant.get("variant_options") or variant.get("selected_options") or []
    result = []
    for item in source:
        if not isinstance(item, dict):
            continue
        name = clean_text(item.get("name"))
        value = clean_text(item.get("value"))
        if name and value:
            result.append({"name": name, "value": value})
    return result


def export_product(product, seller, warnings):
    product_id = clean_text(product.get("id"))
    if not product_id:
        warnings.append("product without id omitted")
        return None

    exported = {"id": product_id}

    title = clean_text(product.get("title"))
    if title:
        exported["title"] = title

    description = normalize_description(product.get("description"))
    if description:
        exported["description"] = description

    url = normalize_url(product.get("url"))
    if url:
        exported["url"] = url
    elif product.get("url"):
        warnings.append(f"product {product_id}: invalid url omitted")

    media = normalize_media(product.get("media"))
    if media:
        exported["media"] = media

    product_categories = normalize_categories(product.get("categories"))
    product_media = media
    variants = []
    for raw_variant in product.get("variants") or []:
        if not isinstance(raw_variant, dict):
            continue
        variant_id = clean_text(raw_variant.get("id"))
        variant_title = clean_text(raw_variant.get("title"))
        if not variant_id or not variant_title:
            warnings.append(f"product {product_id}: variant without id/title omitted")
            continue

        variant = {"id": variant_id, "title": variant_title}

        v_desc = normalize_description(raw_variant.get("description"))
        if v_desc:
            variant["description"] = v_desc

        v_url = normalize_url(raw_variant.get("url")) or url
        if v_url:
            variant["url"] = v_url

        price = normalize_price(raw_variant.get("price"), warnings, f"variant {variant_id}")
        if price:
            variant["price"] = price

        list_price = normalize_price(raw_variant.get("list_price"), warnings, f"variant {variant_id} list_price")
        if list_price:
            variant["list_price"] = list_price

        availability = raw_variant.get("availability")
        if isinstance(availability, dict):
            normalized_availability = {}
            if isinstance(availability.get("available"), bool):
                normalized_availability["available"] = availability["available"]
            status = clean_text(availability.get("status"))
            if status:
                normalized_availability["status"] = status
            if normalized_availability:
                variant["availability"] = normalized_availability

        options = normalize_options(raw_variant)
        if options:
            variant["variant_options"] = options

        v_media = normalize_media(raw_variant.get("media")) or product_media
        if v_media:
            variant["media"] = v_media

        v_categories = normalize_categories(raw_variant.get("categories")) or product_categories
        if v_categories:
            variant["categories"] = v_categories

        if seller:
            variant["seller"] = seller

        variants.append(variant)

    if not variants:
        warnings.append(f"product {product_id}: omitted because no valid variants were found")
        return None

    exported["variants"] = variants
    return exported


def export_feed(catalog, target_country=None, seller=None):
    warnings = []
    raw_products = catalog if isinstance(catalog, list) else catalog.get("products", [])
    if not isinstance(raw_products, list):
        raise ValueError("input must be a list or an object with a products array")

    products = []
    for raw_product in raw_products:
        if not isinstance(raw_product, dict):
            warnings.append("non-object product omitted")
            continue
        product = export_product(raw_product, seller, warnings)
        if product:
            products.append(product)

    feed = {"products": products}
    if target_country:
        feed["target_country"] = target_country.upper()
    return feed, warnings


def write_report(path, input_path, output_path, feed, warnings):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    variant_count = sum(len(p.get("variants", [])) for p in feed["products"])
    lines = [
        "# OpenAI ACP Feed Export Report",
        "",
        f"**Input:** {input_path}",
        f"**Output:** {output_path}",
        f"**Date:** {now}",
        f"**Products exported:** {len(feed['products'])}",
        f"**Variants exported:** {variant_count}",
        "",
        "## Warnings",
        "",
    ]
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("No warnings.")
    lines.extend([
        "",
        "## Next Steps",
        "",
        "1. Confirm partner access for ChatGPT Commerce product feed onboarding.",
        "2. Validate feed fields against the current OpenAI ACP product docs.",
        "3. Upload by the approved file or API method and keep snapshots current.",
    ])
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Export catalog JSON to OpenAI ACP feed JSON")
    parser.add_argument("--input", "-i", required=True, help="Input catalog JSON path")
    parser.add_argument("--output", "-o", required=True, help="Output ACP feed JSON path")
    parser.add_argument("--target-country", help="Optional ISO 3166-1 alpha-2 target country")
    parser.add_argument("--seller-name", help="Optional seller name to attach to variants")
    parser.add_argument("--seller-url", help="Optional seller URL")
    parser.add_argument("--report", help="Optional markdown report path")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        catalog = json.load(f)

    seller = None
    if args.seller_name or args.seller_url:
        seller = {}
        if args.seller_name:
            seller["name"] = args.seller_name
        if args.seller_url:
            seller_url = normalize_url(args.seller_url)
            if seller_url:
                seller["links"] = [{"type": "website", "url": seller_url}]
            else:
                print("Warning: --seller-url is not an absolute http(s) URL; omitted", file=sys.stderr)

    try:
        feed, warnings = export_feed(catalog, args.target_country, seller)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(feed, f, indent=2, ensure_ascii=False)
        f.write("\n")

    report_path = args.report
    if not report_path and args.output.endswith(".json"):
        report_path = args.output[:-5] + "-report.md"
    if report_path:
        write_report(report_path, args.input, args.output, feed, warnings)

    print(f"ACP feed saved to {args.output} ({len(feed['products'])} products)")
    if warnings:
        print(f"Warnings: {len(warnings)}", file=sys.stderr)
        for warning in warnings[:20]:
            print(f"  - {warning}", file=sys.stderr)
    return 0 if feed["products"] else 1


if __name__ == "__main__":
    sys.exit(main())
