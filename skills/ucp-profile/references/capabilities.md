# UCP Capability Notes

Current generator supports these capability switches:

- `checkout`
- `catalog`
- `fulfillment`
- `discount`
- `order`

Only include capabilities the merchant can actually serve. `fulfillment` and
`discount` extend checkout and should be dropped if checkout is not present.

The script currently emits UCP version `2026-01-23`.
