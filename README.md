# UCP Onboard

English | [中文](README_CN.md)

AI agent skills for onboarding merchants to [UCP (Universal Commerce Protocol)](https://github.com/Universal-Commerce-Protocol/ucp) — the open standard by Google, Shopify, and 20+ partners that lets AI agents discover and transact with businesses.

Currently covers product commerce. We're pushing for it to cover services too.

## What We're Building

Give an AI agent a merchant's website URL, and it handles the full UCP integration:

```
Merchant URL → Audit → Profile → Catalog → Checkout → Validate → Live on UCP
```

## What We're Pushing For

UCP currently defines `dev.ucp.shopping.*` — buying products. But commerce isn't just products. It's also **services**: consulting, design, AI agent labor, SaaS on-demand.

We submitted [Issue #303](https://github.com/Universal-Commerce-Protocol/ucp/issues/303) to the UCP consortium, proposing a Services Vertical:

| | Shopping (today) | Services (our proposal) |
|---|---|---|
| What's traded | Products (SKU, price, inventory) | Services (scope, deliverables, capability) |
| Pricing | Fixed | Fixed / usage-based / outcome-based / hourly |
| Fulfillment | Physical shipping | Digital delivery + acceptance verification |
| Lifecycle | `purchased → shipped → delivered` | `booked → in_progress → delivered → verified → settled` |

Imagine: a Shopify seller tells Gemini "help me find someone to optimize my AI search ranking" → agent discovers service providers via UCP → compares scope/pricing → books engagement → verifies delivery → settles payment. **All through the protocol, no platform middleman.**

UCP's [Vendor Namespace mechanism](https://github.com/Universal-Commerce-Protocol/.github/blob/main/CONTRIBUTING.md) allows anyone to prototype via `com.{vendor}.*` and propose graduation to core once adoption is proven. That's our path.

## Skills

| Skill | What It Does | Script |
|-------|-------------|--------|
| **ucp-audit** | Scans a website, scores UCP readiness 0-100, identifies reusable assets and gaps | `audit_site.py` |
| **ucp-profile** | Generates `/.well-known/ucp` business profile JSON with correct capabilities and payment handlers | `generate_profile.py` |
| **ucp-catalog** | Maps Shopify / WooCommerce / CSV product data to UCP catalog schema (minor units, variants, media) | `map_catalog.py` |
| **ucp-checkout** | Guides setup of checkout API based on [official UCP samples](https://github.com/Universal-Commerce-Protocol/samples) | SKILL.md |
| **ucp-validate** | Validates profile structure + spec URL reachability, recommends official `ucp-schema` CLI for deep validation | `validate_ucp.py` |

## Quick Start

```bash
pip install requests beautifulsoup4 jsonschema

# Full pipeline in one command
python run_pipeline.py https://allbirds.com --name "Allbirds" --payment shopify

# Or step by step:

# 1. Audit
python skills/ucp-audit/scripts/audit_site.py https://allbirds.com

# 2. Generate profile
python skills/ucp-profile/scripts/generate_profile.py \
  --domain example.com --name "My Store" --payment stripe --transport rest

# 3. Map catalog
python skills/ucp-catalog/scripts/map_catalog.py \
  --source shopify --url https://allbirds.com --currency USD

# 4. Validate
python skills/ucp-validate/scripts/validate_ucp.py https://allbirds.com
```

## Tested Against Real Sites

| Site | Audit Score | Validate | Notes |
|------|------------|----------|-------|
| allbirds.com | 65/100 | PASS 11/11 | Shopify, MCP transport, 250 products / 2696 variants |
| glossier.com | 90/100 | PASS 11/11 | Shopify, MCP transport, 127 products / 425 variants |
| puddingheroes.com | 5/100 | FAIL 16/42 | Non-standard format, correctly flagged |

See [`examples/glossier/`](examples/glossier/) for full sample output.

## How Validation Works

We don't reinvent the wheel. Validation references official tools:

| Layer | Tool | Source |
|-------|------|--------|
| Profile structure | Our `validate_ucp.py` | Checks required fields, namespace rules, URL reachability |
| Full schema validation | [`ucp-schema`](https://github.com/Universal-Commerce-Protocol/ucp-schema) | Official Rust CLI: `cargo install ucp-schema` |
| Checkout behavior | [`conformance`](https://github.com/Universal-Commerce-Protocol/conformance) | Official test suite (12 Python test files) |
| External discovery | [UCPchecker.com](https://ucpchecker.com) | Community validator (2,800+ merchants monitored) |

## Project Structure

```
├── run_pipeline.py                 One-command full pipeline
├── AGENTS.md                       Agent startup instructions
├── examples/glossier/              Real output samples
└── skills/
    ├── ucp-audit/
    │   ├── SKILL.md                Agent instructions
    │   └── scripts/audit_site.py   Website scanner
    ├── ucp-profile/
    │   ├── SKILL.md
    │   └── scripts/generate_profile.py
    ├── ucp-catalog/
    │   ├── SKILL.md
    │   └── scripts/map_catalog.py  Supports Shopify / CSV / JSON
    ├── ucp-checkout/
    │   └── SKILL.md                References official samples
    └── ucp-validate/
        ├── SKILL.md
        └── scripts/validate_ucp.py
```

## Using with AI Agents

Each `SKILL.md` is an instruction manual for AI agents. The agent reads it, runs the scripts, and produces deliverables.

- **NanoClaw / OpenClaw users:** Copy `skills/` into your agent's skill path
- **Claude Code users:** Point Claude at a SKILL.md and give it a merchant URL

## Security

UCP has built-in security mechanisms (defined in spec, but merchants must implement them):

- **Message Signatures** (RFC 9421) — ECDSA signing of requests/responses, prevents tampering and impersonation
- **AP2 Mandates** — Cryptographic proof of user purchase authorization (SD-JWT), prevents unauthorized purchases
- **Signals** — Platform-observed environment data (IP, UA) for fraud prevention
- **Buyer Consent** — GDPR/CCPA consent transmission

See the [UCP Security spec](https://github.com/Universal-Commerce-Protocol/ucp/blob/main/docs/specification/signatures.md) for details.

## UCP Protocol Overview

```
AI Agent                          Merchant
   │                                 │
   ├── GET /.well-known/ucp ────────►│  Discovery
   │◄── capabilities + payment ──────┤
   │                                 │
   ├── POST /catalog/search ────────►│  Product Search
   │◄── products[] ──────────────────┤
   │                                 │
   ├── POST /checkout (create) ─────►│  Checkout
   │◄── session {id, totals} ────────┤
   │                                 │
   ├── POST /checkout (complete) ───►│  Payment
   │◄── order confirmation ──────────┤
```

**Key resources:**
- [UCP Specification](https://github.com/Universal-Commerce-Protocol/ucp)
- [Official Samples](https://github.com/Universal-Commerce-Protocol/samples) (Python/FastAPI + Node.js/Hono)
- [Official Python SDK](https://github.com/Universal-Commerce-Protocol/python-sdk)
- [Our Services Vertical Proposal (Issue #303)](https://github.com/Universal-Commerce-Protocol/ucp/issues/303)

## Contributing

1. Fork the repo
2. Add or improve a skill
3. Test against a real merchant site
4. Submit a PR with test results

## License

[MIT](LICENSE)
