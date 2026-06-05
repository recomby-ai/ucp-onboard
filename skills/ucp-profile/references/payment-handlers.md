# Payment Handler Notes

Supported draft payment handler templates:

| Provider | Handler namespace |
| --- | --- |
| Stripe | `com.stripe.payment_element` |
| Shopify | `com.google.pay`, `dev.shopify.card` |
| Adyen | `com.adyen.dropin` |

Public profiles may include publishable IDs and configuration. They must never
include secret API keys, private payment tokens, or customer data.

`FILL_IN` placeholders must be replaced before a profile is considered final.
