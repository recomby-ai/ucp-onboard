# UCP Onboard

[English](README.md) | 中文

帮助商家接入 [UCP（Universal Commerce Protocol）](https://github.com/Universal-Commerce-Protocol/ucp)的 AI Agent 技能集。

UCP 是 Google、Shopify 等 20+ 合作伙伴共建的开放协议，让 AI agent 能发现商家并完成交易——目前覆盖商品购买，未来我们希望它也能覆盖服务交易。

## 我们在做什么

给 AI agent 一个商家网站 URL，它能自动完成 UCP 全流程对接：

```
商家 URL → 审计 → 生成 profile → 映射 catalog → 搭 checkout → 验证 → 上线 UCP
```

## 我们在推动什么

UCP 目前只定义了 `dev.ucp.shopping.*`——买商品。但商业世界不只有商品，还有**服务**：咨询、设计、AI agent 劳动力、SaaS 按需调用。

我们向 UCP 官方提交了 [Issue #303](https://github.com/Universal-Commerce-Protocol/ucp/issues/303)，建议协议扩展 Services Vertical：

| | Shopping（现在） | Services（我们提议的） |
|---|---|---|
| 交易对象 | 商品（SKU、价格、库存） | 服务（能力描述、scope、交付物） |
| 定价 | 固定价格 | 固定 / 按量 / 按结果 / 按时间 |
| 交付 | 物流发货 | 数字交付 + 验收确认 |
| 生命周期 | `purchased → shipped → delivered` | `booked → in_progress → delivered → verified → settled` |

想象这样的场景：一个 Shopify 卖家对 Gemini 说"帮我找个人优化我的 AI 搜索排名"→ agent 通过 UCP 发现服务提供者 → 比较报价 → 下单 → 验收 → 结算。**全程协议层交互，没有平台中介。**

UCP 的 [Vendor Namespace 机制](https://github.com/Universal-Commerce-Protocol/.github/blob/main/CONTRIBUTING.md)允许任何人通过 `com.{vendor}.*` 先行实现，证明可行后提议升级为核心标准。这是我们的路线。

## 技能列表

| 技能 | 功能 | 脚本 |
|------|------|------|
| **ucp-audit** | 扫描网站，评分 0-100，识别可复用资产和缺失项 | `audit_site.py` |
| **ucp-profile** | 生成标准 `/.well-known/ucp` 商家 profile JSON | `generate_profile.py` |
| **ucp-catalog** | 映射 Shopify / WooCommerce / CSV 商品数据到 UCP 格式 | `map_catalog.py` |
| **ucp-checkout** | 基于[官方 samples](https://github.com/Universal-Commerce-Protocol/samples) 搭建 checkout API | SKILL.md |
| **ucp-validate** | 验证 profile 结构 + URL 可达性，推荐官方 `ucp-schema` CLI 做深度验证 | `validate_ucp.py` |

## 快速开始

```bash
pip install requests beautifulsoup4 jsonschema

# 一键全流程
python run_pipeline.py https://allbirds.com --name "Allbirds" --payment shopify

# 或者分步执行：

# 1. 审计
python skills/ucp-audit/scripts/audit_site.py https://allbirds.com

# 2. 生成 profile
python skills/ucp-profile/scripts/generate_profile.py \
  --domain example.com --name "我的店铺" --payment stripe --transport rest

# 3. 映射商品
python skills/ucp-catalog/scripts/map_catalog.py \
  --source shopify --url https://allbirds.com --currency USD

# 4. 验证
python skills/ucp-validate/scripts/validate_ucp.py https://allbirds.com
```

## 真实网站测试结果

| 网站 | 审计得分 | 验证 | 备注 |
|------|---------|------|------|
| allbirds.com | 65/100 | PASS 11/11 | Shopify，MCP 传输，250 products / 2696 variants |
| glossier.com | 90/100 | PASS 11/11 | Shopify，MCP 传输，127 products / 425 variants |
| puddingheroes.com | 5/100 | FAIL 16/42 | 非标准格式，被正确标记 |

完整输出样例见 [`examples/glossier/`](examples/glossier/)。

## 验证方式

不重复造轮子，验证引用官方工具：

| 层级 | 工具 | 来源 |
|------|------|------|
| Profile 结构 | 我们的 `validate_ucp.py` | 检查必填字段、命名空间、URL 可达性 |
| 完整 Schema 验证 | [`ucp-schema`](https://github.com/Universal-Commerce-Protocol/ucp-schema) | 官方 Rust CLI |
| Checkout 行为 | [`conformance`](https://github.com/Universal-Commerce-Protocol/conformance) | 官方测试套件（12 个测试文件） |
| 外部发现 | [UCPchecker.com](https://ucpchecker.com) | 社区验证器（2800+ 商家） |

## 项目结构

```
├── run_pipeline.py                 一键全流程
├── AGENTS.md                       agent 启动指南
├── examples/glossier/              真实输出样例
└── skills/
    ├── ucp-audit/
    │   ├── SKILL.md                agent 操作说明
    │   └── scripts/audit_site.py   网站扫描器
    ├── ucp-profile/
    │   ├── SKILL.md
    │   └── scripts/generate_profile.py
    ├── ucp-catalog/
    │   ├── SKILL.md
    │   └── scripts/map_catalog.py  支持 Shopify / CSV / JSON
    ├── ucp-checkout/
    │   └── SKILL.md                引用官方 samples
    └── ucp-validate/
        ├── SKILL.md
        └── scripts/validate_ucp.py
```

## 给 AI Agent 使用

每个 `SKILL.md` 是 AI agent 的操作手册。agent 读完就能按步骤执行脚本、产出交付物。

- **NanoClaw / OpenClaw 用户**：把 `skills/` 目录复制到 agent 的 skill 路径
- **Claude Code 用户**：把 SKILL.md 指给 Claude，给一个商家 URL 即可

## 安全

UCP 协议内置了四层安全机制（定义了但需要商家主动实现）：

- **消息签名**（RFC 9421）— ECDSA 签名请求/响应，防篡改防冒充
- **AP2 Mandate** — 密码学级别的购买授权证明（SD-JWT），防未授权购买
- **Signals** — 平台观测的环境数据（IP、UA），用于反欺诈
- **Buyer Consent** — GDPR/CCPA 合规的用户同意传输

详见 [UCP 安全规范](https://github.com/Universal-Commerce-Protocol/ucp/blob/main/docs/specification/signatures.md)。

## UCP 协议速览

```
AI Agent                          商家
   │                                 │
   ├── GET /.well-known/ucp ────────►│  发现
   │◄── capabilities + payment ──────┤
   │                                 │
   ├── POST /catalog/search ────────►│  搜索商品
   │◄── products[] ──────────────────┤
   │                                 │
   ├── POST /checkout (create) ─────►│  创建订单
   │◄── session {id, totals} ────────┤
   │                                 │
   ├── POST /checkout (complete) ───►│  支付
   │◄── order confirmation ──────────┤
```

**核心资源：**
- [UCP 协议规范](https://github.com/Universal-Commerce-Protocol/ucp)
- [官方 Samples](https://github.com/Universal-Commerce-Protocol/samples)（Python/FastAPI + Node.js/Hono）
- [官方 Python SDK](https://github.com/Universal-Commerce-Protocol/python-sdk)
- [我们的 Services Vertical 提案（Issue #303）](https://github.com/Universal-Commerce-Protocol/ucp/issues/303)

## 贡献

1. Fork 这个 repo
2. 添加或改进 skill
3. 用真实商家网站测试
4. 提交 PR，附上测试结果

## 协议

[MIT](LICENSE)
