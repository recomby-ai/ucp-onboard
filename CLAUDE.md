# UCP Onboard Agent

## What This Is

A Codex plugin and skill pack for merchant onboarding into agentic commerce.
It supports UCP readiness/profile/catalog work, sandbox checkout server
generation, runtime validation, services vertical drafting, and OpenAI ACP
product feed export from normalized catalog data.

## Skill Pipeline

```text
UCP:        ucp-audit -> ucp-profile + ucp-catalog -> ucp-checkout -> ucp-validate
OpenAI ACP: ucp-catalog -> acp-feed
```

## Directory Structure

```text
skills/
├── ucp-audit/      - Scan merchant site and output readiness report
├── ucp-profile/    - Generate /.well-known/ucp business profile
├── ucp-catalog/    - Map Shopify/CSV/JSON data to catalog JSON
├── acp-feed/       - Export catalog JSON to OpenAI ACP feed JSON
├── ucp-checkout/   - Generate sandbox FastAPI checkout server
├── ucp-validate/   - Validate profile, catalog, and checkout runtime
└── ucp-services-vertical/ - Draft service commerce vendor namespace models
```

## Conventions

- Keep `SKILL.md` concise and accurate.
- Put deterministic transformations in `scripts/`.
- Put protocol notes and long mappings in `references/`.
- All output files go to `store/clients/{client_name}/`.
- Amounts are always in minor units.
- Do not store secrets in public JSON artifacts.

## Key Resources

- UCP spec: https://github.com/Universal-Commerce-Protocol/ucp
- UCP docs: https://ucp.dev/documentation/
- OpenAI Commerce docs: https://developers.openai.com/commerce
- OpenAI ACP announcement: https://openai.com/index/buy-it-in-chatgpt/
