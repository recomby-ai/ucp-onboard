# OpenAI Agentic Commerce Protocol Notes

Use these notes as a compact reference for ACP feed export work.

## Official Sources

- OpenAI announcement: https://openai.com/index/buy-it-in-chatgpt/
- OpenAI Commerce docs: https://developers.openai.com/commerce
- Get started: https://developers.openai.com/commerce/guides/get-started
- Product API shape: https://developers.openai.com/commerce/specs/api/products
- Best practices: https://developers.openai.com/commerce/guides/best-practices

## Current Boundary

OpenAI describes Agentic Commerce Protocol (ACP) as the connective layer between
merchants and ChatGPT users. The current documented onboarding path starts with
structured product feeds. Feed onboarding is available to approved partners.

ACP feed export is not the same as:

- UCP discovery profile generation
- UCP checkout endpoint implementation
- AP2 payment authorization
- Stripe Shared Payment Token implementation

## Product Mapping

ACP Products API accepts product feed payloads with `products` arrays. Product
records require a stable product `id` and `variants`. Variant records require a
stable variant `id` and `title`.

Map from this repo's UCP-style catalog:

| Source field | ACP field |
| --- | --- |
| `product.id` | `product.id` |
| `product.title` | `product.title` |
| `product.description` | `product.description` |
| `product.url` | `product.url` |
| `product.media` | `product.media` |
| `product.variants[].id` | `variant.id` |
| `product.variants[].title` | `variant.title` |
| `product.variants[].description` | `variant.description` |
| `product.variants[].price` | `variant.price` |
| `product.variants[].availability` | `variant.availability` |
| `product.variants[].selected_options` | `variant.variant_options` |
| `product.categories` | `variant.categories` when no variant categories exist |

## Quality Rules

- Preserve stable IDs from the merchant platform.
- Use minor units for prices: USD 29.99 is `2999`.
- Keep URLs absolute.
- Put variant-specific price, availability, media, and options on the variant.
- Omit optional fields when source quality is weak.
