# UCP Onboard

[English](README.md) | 中文

一个面向 AI agent 的商家接入插件和 skills 包，用来准备 UCP 与 OpenAI
Agentic Commerce Protocol (ACP) 的电商接入材料。

当前主线支持 [UCP（Universal Commerce Protocol）](https://github.com/Universal-Commerce-Protocol/ucp)
的 readiness audit、profile 生成、catalog 映射、sandbox checkout server 生成和
runtime validation。同时新增 OpenAI [Agentic Commerce Protocol](https://developers.openai.com/commerce)
产品 feed 导出，用于 ChatGPT Commerce / Instant Checkout 方向的接入准备。

## 当前架构

```text
商家 URL -> 审计 -> Catalog -> UCP profile -> UCP checkout server -> Validate
                       |
                       +-> OpenAI ACP feed 导出
```

这个 repo 的正确方向是 adapter-based：先把 Shopify/CSV/JSON 等来源统一成一个
规范 catalog，再按协议导出 UCP 或 OpenAI ACP 所需的文件。

## 协议矩阵

| 层级 | 协议 / API | 本 repo 的角色 |
| --- | --- | --- |
| Agent 交易协议 | UCP | discovery profile、catalog/checkout 规划、验证 |
| ChatGPT Commerce feed | OpenAI ACP | 导出产品 feed，辅助 approved partner 接入 |
| 支付授权 | AP2 / payment handlers | 作为支付安全层引用，当前不实现 |
| 数据来源 | Shopify、CSV、JSON | `ucp-catalog` 当前已支持 |
| 未来 connector | WooCommerce、BigCommerce、Schema.org | 规划项，当前不声明已实现 |

## Skills

| Skill | 功能 | 脚本 |
| --- | --- | --- |
| **ucp-audit** | 扫描网站、评分、识别可复用资产和缺口 | `audit_site.py` |
| **ucp-profile** | 根据明确输入生成 `/.well-known/ucp` profile 草稿 | `generate_profile.py` |
| **ucp-catalog** | 把 Shopify / CSV / JSON 映射成规范 catalog | `map_catalog.py` |
| **acp-feed** | 把规范 catalog 导出为 OpenAI ACP product feed | `export_acp_feed.py` |
| **ucp-checkout** | 生成 sandbox Python/FastAPI UCP checkout server | `generate_api.py` |
| **ucp-validate** | 验证 profile、catalog runtime、checkout lifecycle 和工具可用性 | `validate_ucp.py` |
| **ucp-services-vertical** | 起草服务交易 vendor namespace 模型 | SKILL.md |

## 快速开始

```bash
pip install requests beautifulsoup4 jsonschema

# UCP 方向的一键流程
python run_pipeline.py https://allbirds.com --name "Allbirds" --payment shopify

# 分步执行
python skills/ucp-audit/scripts/audit_site.py https://allbirds.com

python skills/ucp-profile/scripts/generate_profile.py \
  --domain example.com --name "My Store" --payment stripe --transport rest

python skills/ucp-catalog/scripts/map_catalog.py \
  --source shopify --url https://allbirds.com --currency USD \
  --output store/clients/allbirds/catalog.json \
  --report store/clients/allbirds/mapping-report.md

python skills/ucp-checkout/scripts/generate_api.py \
  --profile store/clients/allbirds/ucp-profile.json \
  --catalog store/clients/allbirds/catalog.json \
  --output-dir store/clients/allbirds/ucp-server

python skills/acp-feed/scripts/export_acp_feed.py \
  --input store/clients/allbirds/catalog.json \
  --output store/clients/allbirds/acp-feed.json \
  --target-country US

python skills/ucp-validate/scripts/validate_ucp.py https://allbirds.com
```

## 当前完成度

| 模块 | 状态 |
| --- | --- |
| Codex plugin manifest | 已实现 |
| UCP audit | 已实现 |
| UCP profile 生成 | 已实现，但部分 payment 字段需要人工填充 |
| Catalog mapping | 已支持 Shopify public products.json、CSV、JSON |
| OpenAI ACP feed 导出 | 已支持从规范 catalog 导出 |
| UCP checkout server 生成 | 已支持 sandbox Python/FastAPI |
| Runtime validation gate | 已支持 profile、catalog、checkout create/retrieve/update/cancel |
| 完整官方 UCP conformance | 仍交给官方工具 |

## 项目结构

```text
├── .codex-plugin/plugin.json       Codex 插件 manifest
├── run_pipeline.py                 UCP 方向 pipeline
├── AGENTS.md                       agent 启动指南
├── examples/glossier/              输出样例
└── skills/
    ├── ucp-audit/
    ├── ucp-profile/
    ├── ucp-catalog/
    ├── acp-feed/
    ├── ucp-checkout/
    ├── ucp-validate/
    └── ucp-services-vertical/
```

## Services Vertical

UCP 目前主要是 `dev.ucp.shopping.*`。服务交易，例如咨询、设计、AI agent 劳动力、
SaaS 按需服务，需要 scope、deliverables、验收、结算等语义。这个方向现在拆在
`ucp-services-vertical` skill 里，不混进 shopping onboarding。

## 核心资源

- [UCP Specification](https://github.com/Universal-Commerce-Protocol/ucp)
- [UCP Samples](https://github.com/Universal-Commerce-Protocol/samples)
- [OpenAI Agentic Commerce Protocol docs](https://developers.openai.com/commerce)
- [OpenAI Instant Checkout announcement](https://openai.com/index/buy-it-in-chatgpt/)

## 协议

[MIT](LICENSE)
