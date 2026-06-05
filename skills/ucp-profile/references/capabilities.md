# UCP Capability Notes

Current generator supports these capability switches:

- `checkout`
- `cart` (pre-checkout basket; added in UCP `2026-04-08`)
- `catalog`
- `fulfillment`
- `discount`
- `order`

Only include capabilities the merchant can actually serve. `cart`,
`fulfillment` and `discount` extend checkout and should be dropped if checkout
is not present. `cart` converts to a checkout session via `cart_id`.

The script currently emits UCP version `2026-04-08` (single source:
`UCP_VERSION` in `generate_profile.py`).
