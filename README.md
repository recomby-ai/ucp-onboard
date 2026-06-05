# UCP Onboard

English | [中文](README_CN.md)

Codex and Claude Code plugin, and AI-agent skill pack, for onboarding merchants
to agentic commerce protocols.

The current core supports [UCP (Universal Commerce Protocol)](https://github.com/Universal-Commerce-Protocol/ucp)
readiness, profile generation, catalog mapping, sandbox checkout server
generation, and runtime validation. It also exports catalog data to OpenAI's
[Agentic Commerce Protocol](https://developers.openai.com/commerce) product feed shape for ChatGPT Commerce onboarding.

## What This Builds

Give an agent a merchant URL or catalog export, then run the appropriate path:

```text
Merchant URL -> Audit -> Catalog -> UCP profile -> UCP checkout server -> Validate
                         |
                         +-> OpenAI ACP feed export
```

This repo is intentionally adapter-based: platform connectors normalize product
data once, then protocol exporters prepare UCP or OpenAI ACP outputs.

## Protocol Matrix

| Layer | Protocol / API | Role in this repo |
| --- | --- | --- |
| Agent commerce transaction | UCP | Discovery profile, catalog/checkout capability planning, validation |
| ChatGPT Commerce feed | OpenAI ACP | Product feed export for approved ChatGPT Commerce onboarding |
| Payment authorization | AP2 / payment handlers | Referenced as a payment/security layer, not implemented here |
| Source platforms | Shopify, CSV, JSON | Product data inputs for `ucp-catalog` |
| Future connectors | WooCommerce, BigCommerce, Schema.org | Planned adapters, not claimed as implemented |

## Skills

| Skill | What It Does | Script |
| --- | --- | --- |
| **ucp-audit** | Scans a website, scores UCP readiness, identifies reusable assets and gaps | `audit_site.py` |
| **ucp-profile** | Generates a draft `/.well-known/ucp` business profile from explicit inputs | `generate_profile.py` |
| **ucp-catalog** | Maps Shopify / CSV / JSON product data into normalized catalog JSON | `map_catalog.py` |
| **acp-feed** | Exports normalized catalog JSON to OpenAI ACP product feed JSON | `export_acp_feed.py` |
| **ucp-checkout** | Generates a sandbox Python/FastAPI UCP checkout server | `generate_api.py` |
| **ucp-validate** | Validates profile, catalog runtime, checkout lifecycle, and tool availability | `validate_ucp.py` |
| **ucp-services-vertical** | Drafts vendor-namespace service commerce models | SKILL.md |

## Quick Start

```bash
pip install requests beautifulsoup4

# UCP-oriented pipeline
python run_pipeline.py https://allbirds.com --name "Allbirds" --payment shopify

# Step by step
python skills/ucp-audit/scripts/audit_site.py https://allbirds.com

python skills/ucp-profile/scripts/generate_profile.py \
  --domain example.com --name "My Store" --payment stripe --transport rest

python skills/ucp-catalog/scripts/map_catalog.py \
  --source shopify --url https://allbirds.com --currency USD \
  --output store/clients/allbirds/catalog.json \
  --report store/clients/allbirds/mapping-report.md

python skills/ucp-checkout/scripts/generate_api.py \
  --profile store/clients/allbirds/ucp-profile.json \
  --catalog store/clients/allbirds/catalog.json \
  --output-dir store/clients/allbirds/ucp-server

python skills/acp-feed/scripts/export_acp_feed.py \
  --input store/clients/allbirds/catalog.json \
  --output store/clients/allbirds/acp-feed.json \
  --target-country US

python skills/ucp-validate/scripts/validate_ucp.py https://allbirds.com
```

## Install as a Claude Code plugin

The repo ships a Claude Code plugin manifest and a same-repo marketplace, so it
can be installed directly from git:

```bash
# Add this repo as a marketplace, then install the plugin
claude plugin marketplace add recomby-ai/ucp-onboard
claude plugin install ucp-onboard@ucp-onboard
```

The six skills (`ucp-audit`, `ucp-profile`, `ucp-catalog`, `acp-feed`,
`ucp-checkout`, `ucp-validate`, plus `ucp-services-vertical`) are auto-discovered
from `skills/` and exposed as `ucp-onboard:<skill>`. The same `skills/` directory
also backs the Codex plugin (`.codex-plugin/plugin.json`).

## Current Implementation Status

| Area | Status |
| --- | --- |
| Codex plugin manifest | Implemented |
| Claude Code plugin manifest + marketplace | Implemented |
| UCP audit | Implemented |
| UCP profile generation | Implemented, with placeholders that must be filled |
| Catalog mapping | Implemented for Shopify public products.json, CSV, and JSON |
| OpenAI ACP feed export | Implemented from normalized catalog JSON |
| UCP checkout server generation | Implemented for sandbox Python/FastAPI |
| Runtime validation gate | Implemented for profile, catalog, checkout create/retrieve/update/cancel |
| Offline official profile-schema validation | Implemented against vendored UCP `2026-04-08` schemas (jsonschema) |
| Full official UCP conformance testing | Still delegated to official tools |

## Tested Against Real Sites

| Site | Audit Score | Validate | Notes |
| --- | --- | --- | --- |
| allbirds.com | 65/100 | PASS 11/11 | Shopify, MCP transport, 250 products / 2696 variants |
| glossier.com | 90/100 | PASS 11/11 | Shopify, MCP transport, 127 products / 425 variants |
| puddingheroes.com | 5/100 | FAIL 16/42 | Non-standard format, correctly flagged |

See [`examples/glossier/`](examples/glossier/) for sample outputs.

## Validation

This repo performs a local validation gate and still points to official tools
for deeper conformance checks:

| Layer | Tool | Source |
| --- | --- | --- |
| Profile structure | `validate_ucp.py` | Required fields, capability basics, URL reachability |
| Offline profile schema | `validate_ucp.py` + `refs/ucp-schema/` | Vendored official UCP profile schema (`2026-04-08`) via jsonschema |
| Runtime catalog | `validate_ucp.py` | Search and lookup endpoint preflight |
| Runtime checkout | `validate_ucp.py` | Create, retrieve, update, cancel, totals rules |
| Full UCP schema validation | [`ucp-schema`](https://github.com/Universal-Commerce-Protocol/ucp-schema) | Official Rust CLI |
| Checkout behavior | [`conformance`](https://github.com/Universal-Commerce-Protocol/conformance) | Official test suite |
| ChatGPT Commerce feed review | [OpenAI Commerce docs](https://developers.openai.com/commerce) | ACP product feed guidance |

## Project Structure

```text
├── .claude-plugin/plugin.json      Claude Code plugin manifest
├── .claude-plugin/marketplace.json Claude Code marketplace entry (source ".")
├── .codex-plugin/plugin.json       Codex plugin manifest
├── run_pipeline.py                 UCP-oriented pipeline
├── AGENTS.md                       Agent startup instructions
├── examples/glossier/              Real output samples
└── skills/
    ├── ucp-audit/
    ├── ucp-profile/
    ├── ucp-catalog/
    ├── acp-feed/
    ├── ucp-checkout/
    ├── ucp-validate/
    └── ucp-services-vertical/
```

## Services Vertical

UCP currently centers on `dev.ucp.shopping.*`. This repo still tracks the
Services Vertical idea: consulting, design, AI agent labor, and SaaS on-demand
transactions need scope, deliverables, acceptance, and settlement semantics.

That work now lives in `ucp-services-vertical` so shopping onboarding remains
stable.

## Key Resources

- [UCP Specification](https://github.com/Universal-Commerce-Protocol/ucp)
- [UCP Samples](https://github.com/Universal-Commerce-Protocol/samples)
- [OpenAI Agentic Commerce Protocol docs](https://developers.openai.com/commerce)
- [OpenAI Instant Checkout announcement](https://openai.com/index/buy-it-in-chatgpt/)

## License

[MIT](LICENSE)
