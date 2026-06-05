#!/usr/bin/env python3
"""Generate a UCP business profile (/.well-known/ucp) for a merchant.

Based on official UCP samples discovery_profile.json template format.
Performs basic placeholder/structure checks only; run the official
ucp-schema CLI for full schema validation.

Usage:
  python generate_profile.py --domain example.com --name "My Store" --payment stripe
  python generate_profile.py --domain example.com --name "My Store" --payment shopify --transport mcp
"""

import argparse
import json
import sys
from copy import deepcopy

UCP_VERSION = "2026-04-08"

# === Payment handler templates (from real Shopify/Google/Stripe profiles) ===

PAYMENT_TEMPLATES = {
    "stripe": {
        "com.stripe.payment_element": [
            {
                "id": "stripe_default",
                "version": UCP_VERSION,
                "spec": "https://stripe.com/docs/ucp",
                "schema": "https://stripe.com/schemas/ucp/payment_element.json",
                "available_instruments": [
                    {"type": "card", "constraints": {"brands": ["visa", "mastercard", "amex", "discover"]}},
                    {"type": "wallet", "constraints": {"providers": ["apple_pay", "google_pay"]}},
                ],
                "config": {
                    "publishable_key": "{{STRIPE_PUBLISHABLE_KEY}}"
                },
            }
        ]
    },
    "shopify": {
        "com.google.pay": [
            {
                "id": "gpay",
                "version": "2026-01-11",
                "spec": "https://pay.google.com/gp/p/ucp/2026-01-11/",
                "schema": "https://pay.google.com/gp/p/ucp/2026-01-11/schemas/config.json",
                "config": {
                    "api_version": 2,
                    "api_version_minor": 0,
                    "merchant_info": {
                        "merchant_name": "{{MERCHANT_NAME}}",
                        "merchant_id": "{{GOOGLE_MERCHANT_ID}}",
                        "merchant_origin": "{{DOMAIN}}",
                    },
                    "allowed_payment_methods": [
                        {
                            "type": "CARD",
                            "parameters": {
                                "allowed_auth_methods": ["PAN_ONLY", "CRYPTOGRAM_3DS"],
                                "allowed_card_networks": ["VISA", "MASTERCARD", "AMEX", "DISCOVER"],
                            },
                            "tokenization_specification": {
                                "type": "PAYMENT_GATEWAY",
                                "parameters": [
                                    {"key": "gateway", "value": "shopify"},
                                    {"key": "gateway_merchant_id", "value": "{{SHOPIFY_STORE_ID}}"},
                                ],
                            },
                        }
                    ],
                },
            }
        ],
        "dev.shopify.card": [
            {
                "id": "shopify.card",
                "version": "2026-01-15",
                "spec": "https://ucp.dev/specification/payment-handler-guide",
                "schema": "https://shopify.dev/ucp/card-payment-handler/2026-01-15/config.json",
                "config": {
                    "payment_methods": [
                        {
                            "type": "card",
                            "enabled_card_brands": ["visa", "master", "american_express", "discover", "diners_club"],
                        }
                    ]
                },
            }
        ],
    },
    "adyen": {
        "com.adyen.dropin": [
            {
                "id": "adyen_default",
                "version": UCP_VERSION,
                "spec": "https://adyen.com/docs/ucp",
                "schema": "https://adyen.com/schemas/ucp/dropin.json",
                "available_instruments": [
                    {"type": "card", "constraints": {"brands": ["visa", "mastercard", "amex"]}},
                ],
            }
        ]
    },
}

# === Capability definitions ===

CAPABILITIES = {
    "checkout": {
        "dev.ucp.shopping.checkout": [
            {
                "version": UCP_VERSION,
                "spec": f"https://ucp.dev/{UCP_VERSION}/specification/checkout",
                "schema": f"https://ucp.dev/{UCP_VERSION}/schemas/shopping/checkout.json",
            }
        ]
    },
    "catalog": {
        "dev.ucp.shopping.catalog.search": [
            {
                "version": UCP_VERSION,
                "spec": f"https://ucp.dev/{UCP_VERSION}/specification/catalog/search",
                "schema": f"https://ucp.dev/{UCP_VERSION}/schemas/shopping/catalog_search.json",
            }
        ],
        "dev.ucp.shopping.catalog.lookup": [
            {
                "version": UCP_VERSION,
                "spec": f"https://ucp.dev/{UCP_VERSION}/specification/catalog/lookup",
                "schema": f"https://ucp.dev/{UCP_VERSION}/schemas/shopping/catalog_lookup.json",
            }
        ],
    },
    "cart": {
        "dev.ucp.shopping.cart": [
            {
                "version": UCP_VERSION,
                "spec": f"https://ucp.dev/{UCP_VERSION}/specification/cart",
                "schema": f"https://ucp.dev/{UCP_VERSION}/schemas/shopping/cart.json",
                "extends": "dev.ucp.shopping.checkout",
            }
        ]
    },
    "fulfillment": {
        "dev.ucp.shopping.fulfillment": [
            {
                "version": UCP_VERSION,
                "spec": f"https://ucp.dev/{UCP_VERSION}/specification/fulfillment",
                "schema": f"https://ucp.dev/{UCP_VERSION}/schemas/shopping/fulfillment.json",
                "extends": "dev.ucp.shopping.checkout",
                "config": {
                    "allows_multi_destination": {"shipping": False},
                    "allows_method_combinations": [["shipping"]],
                },
            }
        ]
    },
    "discount": {
        "dev.ucp.shopping.discount": [
            {
                "version": UCP_VERSION,
                "spec": f"https://ucp.dev/{UCP_VERSION}/specification/discount",
                "schema": f"https://ucp.dev/{UCP_VERSION}/schemas/shopping/discount.json",
                "extends": "dev.ucp.shopping.checkout",
            }
        ]
    },
    "order": {
        "dev.ucp.shopping.order": [
            {
                "version": UCP_VERSION,
                "spec": f"https://ucp.dev/{UCP_VERSION}/specification/order",
                "schema": f"https://ucp.dev/{UCP_VERSION}/schemas/shopping/order.json",
            }
        ]
    },
}


def build_profile(domain, name, payment, transport, caps_list):
    """Build a complete UCP business profile."""
    # Services
    if transport == "rest":
        services = {
            "dev.ucp.shopping": [
                {
                    "version": UCP_VERSION,
                    "spec": "https://ucp.dev/specification/overview/",
                    "transport": "rest",
                    "endpoint": f"https://{domain}/ucp/v1",
                    "schema": "https://ucp.dev/services/shopping/openapi.json",
                }
            ]
        }
    elif transport == "mcp":
        services = {
            "dev.ucp.shopping": [
                {
                    "version": UCP_VERSION,
                    "spec": "https://ucp.dev/specification/overview/",
                    "transport": "mcp",
                    "endpoint": f"https://{domain}/api/ucp/mcp",
                    "schema": "https://ucp.dev/services/shopping/openrpc.json",
                },
                {
                    "version": UCP_VERSION,
                    "spec": "https://ucp.dev/specification/overview/",
                    "transport": "embedded",
                    "schema": "https://ucp.dev/services/shopping/embedded.openrpc.json",
                },
            ]
        }
    else:
        print(f"Error: unknown transport '{transport}'. Use 'rest' or 'mcp'.")
        sys.exit(1)

    # Capabilities
    all_caps = {}
    for cap_name in caps_list:
        if cap_name in CAPABILITIES:
            all_caps.update(deepcopy(CAPABILITIES[cap_name]))
        else:
            print(f"Warning: unknown capability '{cap_name}', skipping.")

    # Payment handlers
    if payment in PAYMENT_TEMPLATES:
        handlers = deepcopy(PAYMENT_TEMPLATES[payment])
    else:
        print(f"Error: unknown payment '{payment}'. Options: {list(PAYMENT_TEMPLATES.keys())}")
        sys.exit(1)

    # Fill placeholders in payment handlers
    handlers_json = json.dumps(handlers)
    handlers_json = handlers_json.replace("{{MERCHANT_NAME}}", name)
    handlers_json = handlers_json.replace("{{DOMAIN}}", domain)
    handlers_json = handlers_json.replace("{{GOOGLE_MERCHANT_ID}}", "FILL_IN")
    handlers_json = handlers_json.replace("{{SHOPIFY_STORE_ID}}", "FILL_IN")
    handlers_json = handlers_json.replace("{{STRIPE_PUBLISHABLE_KEY}}", "FILL_IN")
    handlers = json.loads(handlers_json)

    profile = {
        "ucp": {
            "version": UCP_VERSION,
            "services": services,
            "capabilities": all_caps,
            "payment_handlers": handlers,
        }
    }

    return profile


def main():
    parser = argparse.ArgumentParser(description="Generate UCP Business Profile")
    parser.add_argument("--domain", required=True, help="Merchant domain (e.g. example.com)")
    parser.add_argument("--name", required=True, help="Business name")
    parser.add_argument("--payment", required=True, choices=list(PAYMENT_TEMPLATES.keys()),
                        help="Payment provider")
    parser.add_argument("--transport", default="rest", choices=["rest", "mcp"],
                        help="API transport (default: rest)")
    parser.add_argument("--caps", default="checkout,fulfillment,discount,order",
                        help="Comma-separated capabilities: checkout,cart,catalog,fulfillment,discount,order")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    args = parser.parse_args()

    caps_list = [c.strip() for c in args.caps.split(",")]
    profile = build_profile(args.domain, args.name, args.payment, args.transport, caps_list)

    output = json.dumps(profile, indent=2)

    # Check for unfilled placeholders
    placeholders = [p for p in ["FILL_IN"] if p in output]
    if placeholders:
        print("WARNING: Profile contains FILL_IN placeholders that need to be replaced:", file=sys.stderr)
        for line_num, line in enumerate(output.split("\n"), 1):
            if "FILL_IN" in line:
                print(f"  Line {line_num}: {line.strip()}", file=sys.stderr)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Profile saved to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
