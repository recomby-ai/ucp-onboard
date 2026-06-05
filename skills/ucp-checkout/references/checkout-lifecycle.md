# Checkout Lifecycle

Minimum server behavior:

1. `POST /ucp/v1/checkout` creates an incomplete session.
2. `GET /ucp/v1/checkout/{id}` retrieves it.
3. `POST /ucp/v1/checkout/{id}` updates line item quantities and totals.
4. `POST /ucp/v1/checkout/{id}/cancel` cancels it.

Validation and generated sample servers must not implement real payment capture.
Payment completion should remain a sandbox stub until the merchant explicitly
adds and reviews a provider integration.

Totals rules:

- exactly one `subtotal`
- exactly one `total`
- discounts are negative
- all other totals are non-negative
- all amounts are integer minor units
