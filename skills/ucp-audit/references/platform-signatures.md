# Platform Signatures

Current heuristic signatures:

| Platform | Signals |
| --- | --- |
| Shopify | `x-shopify-stage`, `cdn.shopify.com`, `Shopify.theme` |
| WooCommerce | `wc-ajax`, `woocommerce`, `/wp-content/plugins/woocommerce/` |
| Magento | `mage/`, `Magento_` |
| BigCommerce | `bigcommerce.com`, `data-content-region` |

Detection confidence is based on matched signal count. Detection does not imply
that a connector is implemented.
