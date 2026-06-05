# Audit Scoring

The audit score is a readiness heuristic, not a certification.

| Check | Points |
| --- | ---: |
| Valid UCP profile exists | 20 |
| Checkout capability declared | 10 |
| Catalog capability declared | 10 |
| Structured product data exists | 15 |
| Required product fields found | 10 |
| Payment provider detected | 15 |
| UCP-compatible payment provider | 5 |
| Public product API detected | 10 |
| HTTPS used | 5 |

Use the raw observations in `audit.json` for downstream decisions. Do not treat
the score alone as sufficient to deploy.
