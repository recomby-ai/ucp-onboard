# agentic-commerce-skills

让你的网站能被 AI Agent 发现、理解、下单。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[English](README.md) | 中文

---

## 为什么重要

AI Agent 已经开始替用户浏览、购物、支付了。ChatGPT Shopping、Google AI Mode、Perplexity，以及无数自主 Agent，正在访问网站、读取商品数据、发起购买。

如果你的网站没有 agentic-commerce-skills，你在这个全新渠道里就是隐形的。

问题是：目前有 20+ 个竞争协议（Google 阵营 vs OpenAI 阵营 vs 独立协议），没有统一标准，大多数商家完全不知道从哪开始。

**agentic-commerce-skills** 把所有东西整合在一起 —— 协议索引帮你看清全局，可执行的 Skills 帮你实施改造，不断增长的实战案例库帮你（和你的 Agent）少走弯路。

## 这是什么

**协议索引 + 可执行 Skills + 实战案例库**，让任何网站兼容 AI Agent。

```
agentic-commerce-skills/
├── protocols/          ← 协议索引：20+ 个协议，做什么、谁做的、官方链接
├── skills/
│   ├── ar-discover/    ← 让 Agent 能发现你（llms.txt, agents.json, A2A）
│   ├── ar-structured-data/  ← 让 Agent 能理解你（Schema.org, JSON-LD）
│   ├── ar-commerce/    ← 让 Agent 能下单（ACP, UCP）
│   ├── ar-payments/    ← 让 Agent 能支付（Stripe SPT, x402, AP2）
│   ├── ar-identity/    ← 让 Agent 能认证（OAuth, OIDC）
│   └── ar-audit/       ← 给你的网站打分（0-100）
```

## 协议全景

两大生态正在形成，商家两边都得支持。

| 层级 | Google / 开放阵营 | OpenAI / Anthropic 阵营 | 独立协议 |
|------|------------------|------------------------|---------|
| **发现** | A2A Agent Cards, NLWeb | — | llms.txt, Schema.org, agents.json |
| **通信** | A2A, AG-UI, ANP | MCP | — |
| **商务** | UCP（Google + Shopify） | ACP（OpenAI + Stripe） | — |
| **支付** | — | Stripe SPT | x402（Coinbase）, AP2（Visa） |
| **身份** | — | — | OAuth Agent 扩展, DID, OIDC-A |
| **授权** | — | — | ai.txt, RSL |

每个协议都索引在 [`protocols/`](protocols/) 里：做什么、谁做的、当前状态、官方 spec 链接。不复制 spec 内容，只链接官方源。

| 文件 | 覆盖内容 |
|------|---------|
| [discovery.md](protocols/discovery.md) | llms.txt, agents.json, A2A Agent Cards, NLWeb, Schema.org |
| [communication.md](protocols/communication.md) | MCP, A2A, AG-UI, ANP |
| [commerce.md](protocols/commerce.md) | ACP, UCP |
| [payments.md](protocols/payments.md) | Stripe SPT, x402, AP2, PayPal |
| [identity.md](protocols/identity.md) | OAuth Agent 扩展, DID, OIDC-A |
| [licensing.md](protocols/licensing.md) | ai.txt, RSL |

## Skills 怎么工作

每个 Skill 由三部分组成：

```
skills/ar-discover/
├── SKILL.md              ← 改造指南：告诉 Agent 一步步怎么做
├── scripts/
│   └── validate_*.py     ← 验证脚本：检查产出是否符合官方 spec
└── references/
    ├── philosophy.md     ← 为什么要做这件事
    ├── *-guide.md        ← 协议具体操作指南
    └── cases/            ← 实战案例（社区贡献）
        └── _template.md
```

**SKILL.md** = Agent 的改造指南。读完就知道怎么做。

**validate 脚本** = 质量门禁。Agent 改造完 → 跑验证脚本 → FAIL 就继续改 → PASS 才算完。验证标准严格对标官方 spec。

**references/** = Agent 的知识库。改造前先读，少走弯路。

### 核心循环

```
Agent 读 SKILL.md
  → 先搜索官方最新 spec（不依赖训练数据）
  → 查 references/cases/ 看有没有类似案例
  → 执行改造
  → 跑 validate 脚本
  → FAIL？修复后重新验证
  → PASS？完成
  → 踩坑了？写回 case，下一个 Agent 受益
```

## Skills 一览

| Skill | Agent 做什么 | 验证对标 |
|-------|-------------|---------|
| [ar-discover](skills/ar-discover/) | 生成 llms.txt、agents.json、A2A agent card | llmstxt.org spec, A2A 协议 |
| [ar-structured-data](skills/ar-structured-data/) | 生成/修复 Schema.org JSON-LD | Google Search Central 官方要求 |
| [ar-commerce](skills/ar-commerce/) | 搭建 ACP/UCP 商务端点 | OpenAI ACP spec, Google UCP spec |
| [ar-payments](skills/ar-payments/) | 集成 Agent 支付流程 | Stripe SPT, coinbase/x402, Visa AP2 |
| [ar-identity](skills/ar-identity/) | 配置 Agent OAuth/身份认证 | RFC 8414, OpenID Connect Discovery |
| [ar-audit](skills/ar-audit/) | 6 维度综合评分（0-100） | 以上所有 |

## 快速开始

```bash
git clone https://github.com/recomby-ai/agentic-commerce-skills.git
cd agentic-commerce-skills
pip install requests

# 给任何网站打分
python skills/ar-audit/scripts/audit_full.py --url https://yoursite.com

# 验证发现文件
python skills/ar-discover/scripts/validate_discovery.py --url https://yoursite.com

# 或者在 Claude Code 里当 skills 用
claude "Use the ar-audit skill to score example.com"
```

## 贡献案例

最有价值的贡献是一个 **case**（实战案例）—— 记录你（或你的 Agent）在改造网站过程中学到的东西。

案例放在 `skills/{skill}/references/cases/` 里，格式如下：

```markdown
# Shopify 店铺 — 添加 llms.txt

- **Author:** @yourname
- **Date:** 2026-03-15
- **Stack:** Shopify
- **Protocols:** llms.txt, Schema.org

## Context
网站需要什么，为什么需要。

## What Worked
成功的步骤，附代码片段。

## What Did NOT Work
试过但失败的方案，以及为什么失败。

## Gotchas
踩坑点，不明显的问题。

## Verification
怎么验证成功的（跑了哪个 validate 脚本，什么结果）。

## Result
PASS / PARTIAL / FAIL + 一句话总结。
```

这些案例是**给 Agent 读的**。Agent 跑 skill 时会先查案例。你的案例 = 所有未来 Agent 的捷径。

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## License

[MIT](LICENSE) — 2026 Recomby AI
