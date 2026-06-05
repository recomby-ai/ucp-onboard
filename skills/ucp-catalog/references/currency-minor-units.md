# Currency Minor Units

Prices in catalog, UCP checkout, and ACP feed outputs use integer minor units.

Default multiplier is 100.

Current overrides:

| Currency | Multiplier |
| --- | ---: |
| JPY | 1 |
| KRW | 1 |
| BHD | 1000 |
| KWD | 1000 |
| OMR | 1000 |

When adding a new currency-sensitive connector, verify the multiplier before
shipping.
