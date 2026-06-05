# Services Model

Draft service fields:

| Field | Purpose |
| --- | --- |
| `id` | Stable service identifier |
| `title` | User-facing service name |
| `description` | Plain, HTML, or Markdown description |
| `scope` | Included work and exclusions |
| `deliverables[]` | Concrete outputs |
| `pricing` | Fixed, usage-based, outcome-based, or hourly |
| `availability` | Booking or capacity metadata |
| `acceptance_criteria[]` | What counts as delivered |
| `lifecycle` | Allowed state transitions |

Lifecycle:

```text
booked -> in_progress -> delivered -> verified -> settled
booked -> canceled
in_progress -> canceled
delivered -> disputed
```

Settlement should follow verification unless the commercial model explicitly
requires escrow, milestones, or prepayment.
