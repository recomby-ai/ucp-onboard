# Source Mapping

Current implemented sources:

| Source | Input | Notes |
| --- | --- | --- |
| Shopify | public `/products.json` | No authentication, max 250 products per request |
| CSV | local file | Expected columns include `id`, `title`, `description`, `price`, `sku`, `image_url`, `category`, `available` |
| JSON | local file | Accepts a product array or object with `products` |

Future connectors should produce the same normalized `catalog.json` contract
instead of inventing a parallel schema.
