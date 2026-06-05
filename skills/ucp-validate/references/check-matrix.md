# Validation Check Matrix

Validation is layered:

| Layer | Checks |
| --- | --- |
| Profile | profile exists, JSON parses, `ucp` root, version, services, capabilities, payment handlers |
| Namespace / URLs | spec/schema URL reachability spot checks |
| Catalog | search/lookup endpoints respond and return valid product/variant basics |
| Checkout | create/retrieve/update/cancel lifecycle, status, links, totals |
| Tools | `ucp-schema` and conformance suite availability |

Never call checkout completion in automated validation.
