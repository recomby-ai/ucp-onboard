# UCP Readiness Audit — glossier.com

**URL:** https://glossier.com/
**Date:** 2026-03-25T13:41:37Z
**Score:** 90/100

## Summary
Excellent — this site is close to UCP-ready. Minor gaps to fill.

## Platform
- **Detected:** shopify (high confidence)
- **Payment (HTML):** None in HTML
- **Payment (UCP profile):** com.google.pay, dev.shopify.card
- **Transport:** mcp, embedded
- **Product API:** Yes (storefront)

## UCP Profile Status
✅ Profile exists at /.well-known/ucp (version: 2026-01-23)
- Capabilities: dev.ucp.shopping.checkout, dev.ucp.shopping.fulfillment, dev.ucp.shopping.discount, dev.ucp.shopping.order


## What You Already Have (Reusable Assets)
| UCP Field | Source | Status |
|-----------|--------|--------|
| title | og:title | Ready to map |
| description | og:description | Ready to map |
| media | og:image | Ready to map |
| price | json-ld:offers.price | Ready to map |
| currency | json-ld:offers.priceCurrency | Ready to map |
| availability | json-ld:offers.availability | Ready to map |


## What's Missing
No critical gaps found.

## Recommended Integration Path
1. Generate UCP profile with `ucp-profile` skill
2. Map Shopify products.json to UCP catalog with `ucp-catalog`
3. Deploy a lightweight API proxy (Cloudflare Worker or Vercel Edge Function)
4. Host /.well-known/ucp via the proxy
5. Validate with `ucp-validate`

## Score Breakdown
| Check | Points | Status |
|-------|--------|--------|
| UCP profile exists | 20 | ✅ |
| Has checkout capability | 10 | ✅ |
| Has catalog capability | 10 | ❌ |
| Structured product data | 15 | ✅ |
| All required product fields | 10 | ✅ |
| Payment provider detected | 15 | ✅ |
| UCP-compatible provider | 5 | ✅ |
| Public product API | 10 | ✅ |
| HTTPS enabled | 5 | ✅ |
| **Total** | **90** | |
