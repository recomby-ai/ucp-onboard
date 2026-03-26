# UCP Validation Report — glossier.com

**URL:** https://glossier.com
**Profile:** https://glossier.com/.well-known/ucp
**Date:** 2026-03-25T13:42:01Z
**Result:** PASS (10/10 checks passed)

## Results

| Status | Detail |
|--------|--------|
| PASS | Profile found at https://glossier.com/.well-known/ucp |
| PASS | Version: 2026-01-23 |
| PASS | Services: dev.ucp.shopping |
| INFO | Transport: mcp at http://www.glossier.com/api/ucp/mcp |
| INFO | Transport: embedded at N/A |
| PASS | Capabilities: 4 — dev.ucp.shopping.checkout, dev.ucp.shopping.fulfillment, dev.ucp.shopping.discount, dev.ucp.shopping.order |
| PASS | Payment handlers: com.google.pay, dev.shopify.card |
| SKIP | jsonschema not installed — pip install jsonschema for schema validation |
| PASS | dev.ucp.shopping.checkout spec: https://ucp.dev/2026-01-23/specification/checkout → 200 |
| PASS | dev.ucp.shopping.checkout schema: https://ucp.dev/2026-01-23/schemas/shopping/checkout.json → 200 |
| PASS | dev.ucp.shopping.fulfillment spec: https://ucp.dev/2026-01-23/specification/fulfillment → 200 |
| PASS | dev.ucp.shopping.fulfillment schema: https://ucp.dev/2026-01-23/schemas/shopping/fulfillment.json → 200 |
| PASS | dev.ucp.shopping.discount spec: https://ucp.dev/2026-01-23/specification/discount → 200 |
| INFO | ucp-schema CLI not installed — cargo install ucp-schema for full validation |
| INFO | Official conformance suite not cloned — clone Universal-Commerce-Protocol/conformance for checkout testing |

## Next Steps

1. **Fix errors above** if any
2. **Full schema validation**: `ucp-schema validate profile.json` (install: `cargo install ucp-schema`)
3. **Checkout behavior test**: clone `Universal-Commerce-Protocol/conformance` and run against your server
4. **External check**: paste your URL at https://ucpchecker.com
