# agentic-commerce-skills

Make your website work with AI agents — discoverable, understandable, transactable.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

English | [中文](README_CN.md)

---

## Why this matters

AI agents are starting to browse, shop, and pay — on behalf of users. ChatGPT Shopping, Google AI Mode, Perplexity, and countless autonomous agents are already visiting websites, reading product data, and initiating purchases.

If your website isn't agentic-commerce-skills, you're invisible to this entire channel.

The problem: there are 20+ competing protocols (Google vs OpenAI vs independent), no single standard, and most merchants have no idea where to start.

**agentic-commerce-skills** gives you everything in one place — a protocol index to understand the landscape, executable skills to actually implement support, and a growing library of real-world cases so you (and your agents) don't repeat mistakes.

## What is this

**Protocols + Skills + Cases** for making any website AI-agent-compatible.

```
agentic-commerce-skills/
├── protocols/          ← Protocol index: 20+ protocols, what they do, who made them, links
├── skills/
│   ├── ar-discover/    ← Make agents find you (llms.txt, agents.json, A2A)
│   ├── ar-structured-data/  ← Make agents understand you (Schema.org, JSON-LD)
│   ├── ar-commerce/    ← Make agents buy from you (ACP, UCP)
│   ├── ar-payments/    ← Make agents pay you (Stripe SPT, x402, AP2)
│   ├── ar-identity/    ← Make agents authenticate (OAuth, OIDC)
│   └── ar-audit/       ← Score your site's agent-readiness (0-100)
```

## Protocol Landscape

Two ecosystems are forming. Merchants need to support both.

| Layer | Google / Open | OpenAI / Anthropic | Independent |
|-------|--------------|-------------------|-------------|
| **Discovery** | A2A Agent Cards, NLWeb | — | llms.txt, Schema.org, agents.json |
| **Communication** | A2A, AG-UI, ANP | MCP | — |
| **Commerce** | UCP (Google + Shopify) | ACP (OpenAI + Stripe) | — |
| **Payments** | — | Stripe SPT | x402 (Coinbase), AP2 (Visa) |
| **Identity** | — | — | OAuth Agent Ext, DID, OIDC-A |
| **Licensing** | — | — | ai.txt, RSL |

Every protocol is indexed in [`protocols/`](protocols/) with: what it does, who made it, current status, and official spec links. No spec content is copied — we link to the source.

| File | Covers |
|------|--------|
| [discovery.md](protocols/discovery.md) | llms.txt, agents.json, A2A Agent Cards, NLWeb, Schema.org |
| [communication.md](protocols/communication.md) | MCP, A2A, AG-UI, ANP |
| [commerce.md](protocols/commerce.md) | ACP, UCP |
| [payments.md](protocols/payments.md) | Stripe SPT, x402, AP2, PayPal |
| [identity.md](protocols/identity.md) | OAuth Agent Extensions, DID, OIDC-A |
| [licensing.md](protocols/licensing.md) | ai.txt, RSL |

## How Skills Work

Each skill has three parts:

```
skills/ar-discover/
├── SKILL.md              ← Prompts: tells the agent what to do, step by step
├── scripts/
│   └── validate_*.py     ← Validation: verifies the output is spec-compliant
└── references/
    ├── philosophy.md     ← Why this matters
    ├── *-guide.md        ← Protocol-specific how-to guides
    └── cases/            ← Real-world implementation cases
        └── _template.md
```

**SKILL.md** = prompts for the agent. It reads this, knows what to do.

**validate script** = quality gate. Agent generates output → validate script checks it → FAIL means keep fixing → PASS means done.

**references/** = the agent's knowledge base. Guides, specs, and cases it reads before acting.

### The loop

```
Agent reads SKILL.md
  → checks references/cases/ for similar situations
  → does the work
  → runs validate script
  → FAIL? fix and re-validate
  → PASS? done
```

## Skills Overview

| Skill | What the agent does | Validates against |
|-------|--------------------|--------------------|
| [ar-discover](skills/ar-discover/) | Deploy llms.txt, agents.json, A2A agent card | llmstxt.org spec, A2A protocol |
| [ar-structured-data](skills/ar-structured-data/) | Add/fix Schema.org JSON-LD markup | Google Search Central requirements |
| [ar-commerce](skills/ar-commerce/) | Set up ACP/UCP checkout endpoints | OpenAI ACP spec, Google UCP spec |
| [ar-payments](skills/ar-payments/) | Integrate agent payment flows | Stripe SPT, coinbase/x402, Visa AP2 |
| [ar-identity](skills/ar-identity/) | Configure agent OAuth/identity endpoints | RFC 8414, OpenID Connect Discovery |
| [ar-audit](skills/ar-audit/) | Full 6-dimension site audit (0-100 score) | All of the above |

## Quick Start

```bash
git clone https://github.com/recomby-ai/agentic-commerce-skills.git
cd agentic-commerce-skills
pip install requests

# Audit any website
python skills/ar-audit/scripts/audit_full.py --url https://yoursite.com

# Validate discovery files
python skills/ar-discover/scripts/validate_discovery.py --url https://yoursite.com

# Or use with Claude Code as skills
claude "Use the ar-audit skill to score example.com"
```

## Contributing Cases

The most valuable contribution is a **case** — a record of what you (or your agent) learned while making a site agentic-commerce-skills.

Cases go in `skills/{skill}/references/cases/` and look like this:

```markdown
# Shopify Store — Adding llms.txt

- **Author:** @yourname
- **Date:** 2026-03-15
- **Stack:** Shopify
- **Protocols:** llms.txt, Schema.org

## Context
What the site needed and why.

## What Worked
Steps that succeeded, with code snippets.

## What Did NOT Work
Approaches that failed and why.

## Gotchas
Non-obvious issues.

## Verification
How you confirmed it works.

## Result
PASS / PARTIAL / FAIL + one-line summary.
```

These cases are **for agents to read**. When an agent runs a skill, it checks cases first. Your case helps every future agent working on a similar stack.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full submission guide.

## License

[MIT](LICENSE) — 2026 Recomby AI
