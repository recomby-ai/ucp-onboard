# UCP Onboard —— 项目认知文档

> 这份文档记录的是"我如何理解这个项目"——不是 API 手册，而是**心智模型**：
> 它解决什么问题、为什么这样设计、各部分如何互相咬合、哪里是脆弱点。
> 理解到位了，改代码就不会改错方向。
>
> 它是一份**活文档（稳定的锚）**：认知会随着对项目和上游 spec 的深入而更新。

---

## 0. 一句话本质

**把"给人看的电商网站"翻译成"给 AI agent 交易的结构化接口"的一条适配流水线。**

它不生产电商功能（不做购物车、不做支付、不做库存），它生产**协议产物**：
让商家以最小改造，变得「可被 AI 发现 + 可被 AI 下单」。

所以判断任何一段代码该不该存在、对不对，只问一句：
**"它是在帮商家更标准、更可信地接入 agentic commerce 吗？"**

---

## 1. 问题背景：为什么需要这个东西

### 1.1 世界正在发生的变化
AI agent（ChatGPT、Gemini 等）开始代替人去"逛店、比价、下单"。
但今天的电商网站是为**人眼 + 浏览器**设计的：商品信息散在 HTML、价格藏在 JS 渲染里、
下单流程是一串点击。agent 没法可靠地解析和操作。

### 1.2 协议层的答案
于是出现了两套标准，要求商家用**机器可读的契约**暴露自己：

| 协议 | 推手 | 解决什么 |
|------|------|---------|
| **UCP** (Universal Commerce Protocol) | Google + Shopify 等 | 全链路：发现(profile) → 目录(catalog) → 下单(checkout) → 订单(order) |
| **OpenAI ACP** (Agentic Commerce Protocol) | OpenAI / ChatGPT Commerce | 主要是商品 feed 投喂 + Instant Checkout |

两者都要求：
- 商家在 `/.well-known/ucp` 放一份**自我描述**（我支持什么能力、用什么支付、接口在哪）
- 商品数据按**统一 schema** 暴露（金额用 minor units、有 variants、有 availability…）
- 提供**可调用的接口**（搜索、下单）

### 1.3 这个项目的定位
商家（尤其中小商家）自己读 spec、改站、写接口、做校验，门槛高。
**recomby.ai 把这套接入工作自动化成一个 agent skill pack**——这就是本仓库。
它是一个 **Codex 插件 / skill 包**，既能被 AI agent 调用，也能当 CLI 工具跑。

> 认知锚点：这是一个 **B2B 工具**，用户是"想接入 agentic commerce 的商家/集成方"，
> 不是终端消费者。所以产物是 `.json` / `.md` / 可部署的 server 脚手架，不是 UI。

---

## 2. 核心心智模型：一条"翻译流水线 + 自洽验证环"

```
        ┌─────────────────────── 输入：商家 URL / 商品文件 ───────────────────────┐
        │                                                                          │
   [1] ucp-audit          扫站、识别平台/结构化数据/支付/API，打 0-100 readiness 分
        │  产出现状画像，告诉商家"你离 UCP-ready 有多远、哪些资产能复用"
        ▼
   [2] ucp-profile        生成 /.well-known/ucp —— 商家的"自我声明书"
        │  声明：版本、服务端点、支持的 capabilities、支付 handler
        ▼
   [3] ucp-catalog        把 Shopify/CSV/JSON 商品 → UCP 商品 schema（catalog.json）
        │  统一字段、金额转 minor units、补 variants/availability
        │
        ├──(分支)──► acp-feed       catalog.json → OpenAI ACP feed（另一条赛道）
        │
        ├──(可选)──► ucp-checkout   用 profile + catalog 生成 FastAPI 沙箱 server
        │            （真正能跑起来、实现 catalog/checkout 接口的参考实现）
        ▼
   [4] ucp-validate       端到端验收：拉 profile → 检查结构 → 打 catalog/checkout 接口
        │  能力驱动：profile 声明了什么能力，就验什么接口
        ▼
        └─────────────────────── 产出：一套可部署 + 可信的接入产物 ───────────────┘
```

### 2.1 为什么是"流水线"
因为接入是**有依赖顺序**的：
- 不先 audit，就不知道商家有什么、缺什么；
- 不先有 profile，validate 无从下手（profile 是入口）；
- catalog 依赖商家数据源；checkout server 依赖 profile + catalog。

`run_pipeline.py` 就是这条流水线的编排器，用 `subprocess` 串起各脚本，
产物统一落 `store/clients/{client_name}/`。

### 2.2 为什么是"自洽验证环"（最关键的设计洞察）
这是整个项目最聪明的地方，也是我认为它"设计成立"的核心证据：

```
ucp-profile  ──声明能力──►  ┐
ucp-catalog  ──提供数据──►  ├──► ucp-checkout 生成的 server 恰好实现这些能力
                            ┘            │
                                         ▼
                            ucp-validate 去打这个 server 的接口
                            （能力驱动：profile 说有 catalog，就打 catalog/search）
```

也就是说：**生成端（profile/catalog/checkout）和验证端（validate）共用同一套契约**。
- profile 声明 `dev.ucp.shopping.catalog.search` → validate 就会 POST `/catalog/search`
- checkout server 实现 `/catalog/search` 返回 `{products:[...]}` → validate 检查 `products[]` 结构
- checkout server 的 session 返回 `currency/totals/status` → validate 校验 totals 必须恰好一个 subtotal + 一个 total、金额是整数、discount 必须为负…

这形成一个**闭环**：本项目自己生成的东西，能被自己验证通过。
这既是质量保证，也是给商家的"参考实现 + 验收标准"双重交付。

> 认知锚点：理解了"契约在两端共享"，你就知道——
> **改了任何一端的字段，必须同步另一端**，否则环就破了。
> （例：spec 升级让 Order 的 `currency` 变必填，profile 端、checkout server 端、validate 端要一起改。）

---

## 3. 数据契约：贯穿全项目的"不变量"

这些约定是流水线能拼起来的"螺纹"，写在 CLAUDE.md / AGENTS.md，散落在每个脚本里：

| 不变量 | 为什么 | 违反的后果 |
|--------|--------|-----------|
| **金额一律 minor units（整数分）** | 浮点会丢精度；agent 间结算不能有歧义 | 价格错、validate 直接 FAIL（它强校验 `amount` 必须是 int） |
| **日期一律 RFC 3339** | 跨系统时间无歧义 | 解析失败 |
| **能力名用反域名风格** `dev.ucp.shopping.*` | 命名空间隔离、可扩展、避免冲突 | validate 用正则 `^[a-z0-9]+(\.[a-z0-9_-]+)+$` 校验，不符就 FAIL |
| **每个商品至少 1 个 variant** | UCP 把"可购买单元"建模在 variant 上 | 没 variant 的商品被丢弃 |
| **profile 是单一入口** `/.well-known/ucp` | agent 发现商家的标准位置 | 找不到 = 整条验证 CRITICAL FAIL |
| **公开产物里不放任何密钥** | profile/feed 是公网可读的 | 泄露支付凭证 |
| **不声称未实现的能力 / 未获批的合作** | 信任问题；agent 会按声明去调用 | 声明了调不通 = 接入失败、信任崩 |

> 认知锚点：这些不是"代码风格"，是**协议级硬约束**。
> validate 脚本本质上就是这些不变量的"可执行版本"。

---

## 4. 各 skill 的角色与"它负责的那份契约"

| Skill | 输入 | 输出 | 它在协议里负责的"那一块" |
|-------|------|------|------------------------|
| **ucp-audit** | 商家 URL | readiness 报告 + 评分 | "现状诊断"——识别平台(Shopify/Woo/Magento…)、结构化数据(JSON-LD/OG/microdata)、支付商、公开 API |
| **ucp-profile** | 域名/名称/支付/transport/能力 | `/.well-known/ucp` | "自我声明书"——商家告诉 agent 我支持什么 |
| **ucp-catalog** | Shopify/CSV/JSON | `catalog.json` | "商品目录标准化"——把杂乱商品数据压成统一 schema |
| **acp-feed** | catalog.json | OpenAI ACP feed | "另一条赛道"——同样的目录，转成 ChatGPT Commerce 要的格式 |
| **ucp-checkout** | profile + catalog | FastAPI 沙箱 server | "参考实现"——给商家一个能跑的、正确的接口范本 |
| **ucp-validate** | 商家 URL（或本地文件） | 验收报告 PASS/CONDITIONAL/FAIL | "验收闸门"——把所有不变量变成可执行检查 |
| **ucp-services-vertical** | （指导性） | 草稿/命名空间模型 | "向服务业延伸的愿景"——不只卖实物，也卖服务 |

### 4.1 分层哲学（每个 skill 内部）
```
skills/<name>/
├── SKILL.md      ← 给 agent 看的"什么时候用我、怎么用"（自然语言指令）
├── scripts/      ← 确定性的转换逻辑（Python，可测、可重放）
└── references/   ← 协议长文档、字段映射表（知识，不是逻辑）
```
这套分层的意图：**自然语言决策（SKILL.md）与确定性执行（scripts）解耦**。
agent 负责"判断走哪条路"，脚本负责"精确地做不出错的事"。
这也是为什么校验/转换都放在 `.py` 里——LLM 不该手算金额转换。

---

## 5. 两条路径：UCP 全链路 vs ACP feed

```
UCP 全链路：  audit → profile + catalog → checkout → validate
              （商家要被 agent 直接发现 + 下单）

ACP feed：    catalog → acp-feed
              （商家要进 ChatGPT Commerce / Instant Checkout 的商品投喂）
```

AGENTS.md 的指令是"**选匹配目标的最小路径**"——
不是每次都跑全套，而是按用户目标裁剪。这体现了 agent skill 的设计取向：
**意图驱动、按需编排**，而不是死板的固定流程。

> 注意 AGENTS.md 特别强调：ACP 的"partner approval"是**业务状态**，
> 本仓库无法推断，不能替商家声称已获批。这又回到了"不声称未实现"的信任原则。

---

## 6. 我对"质量来自哪里"的判断

这个项目的可信度，建立在三个支点上：

1. **确定性脚本**：所有易错的转换（金额、HTML 清洗、URL 规范化）都在纯函数里，可单测。
   `tests/` 里 9 个测试就是钉住这些不变量（如 `to_minor("1.234","BHD")==1234`）。
2. **自洽环**：生成的东西能被自己的 validate 验过（见 §2.2）。
3. **诚实边界**：明确区分"我能确定的"（schema 结构）和"我不能确定的"（合作审批、真实支付）。
   validate 甚至明确写"绝不用真实支付凭证去跑 checkout 完成"。

---

## 7. 这个心智模型如何指导"改代码"

一旦接受上面的认知，下面这些判断就是自然推论（也对应我审查里发现的问题）：

| 认知 | 推论 / 该怎么改 |
|------|----------------|
| 契约两端共享 | 产物（catalog.json）和声明（profile capabilities）必须一致；csv/json 源生成了目录就该声明 catalog 能力 |
| spec 版本是协议契约的一部分 | 版本应是**单一来源**，能一处升级；现在硬编码 `2026-01-23` 散在多处，且落后于上游 `2026-04-08` |
| validate 是不变量的可执行版 | 升级 spec（如 Order `currency` 变必填、新增 Cart）必须三端同步：profile / checkout server / validate |
| "不声称未实现" | requirements 里 `jsonschema`/`jinja2` 没真用、docstring 说"validates against schema"却没校验——要么补实现，要么删声称 |
| 确定性逻辑要可复用 | product 和 variant 的 HTML 清洗逻辑不一致 → 应抽公共 `strip_html()` |
| 接入是给商家用的工具 | 应有 CI 兜底（现在有 tests 没 CI），保证每次改动不破坏契约 |

---

## 8. 外部权威参考（真理来源 / 改动锚点）

> 改任何东西前先锚定这些来源，否则就是凭记忆瞎改——违反「与上游 spec 一致」那条不变量。

### 8.1 项目内部参考（`skills/*/references/`）
这是项目自己写下的契约说明，已与代码基本一致，可直接当改动依据：

| 参考 | 内容 |
|------|------|
| `ucp-profile/references/capabilities.md` | 能力开关；明确写着当前版本 `2026-01-23`、"只声明能真正服务的能力" |
| `ucp-checkout/references/checkout-lifecycle.md` | checkout 生命周期 + totals 规则（与 validate 完全一致） |
| `ucp-catalog/references/currency-minor-units.md` | 货币最小单位倍率表（JPY=1、BHD=1000…） |
| `ucp-catalog/references/source-mapping.md` | 数据源契约；"未来连接器必须产出同一份 catalog.json" |
| `acp-feed/references/openai-acp.md` | ACP 字段映射表（`selected_options → variant_options` 等） |
| `ucp-validate/references/check-matrix.md` | 验证分层矩阵 |
| `ucp-audit/references/{platform-signatures,scoring}.md` | 平台指纹、评分表 |
| `ucp-services-vertical/references/services-model.md` | 服务业模型草案 |

> 这些内部参考**反向印证**了代码意图，是判断"改得对不对"的第一手依据。

### 8.2 外部权威参考（金标准，按权威度排序）

| 参考 | 地址 | 作用 |
|------|------|------|
| **UCP 官方 JSON Schema** ⭐ | upstream `source/discovery/profile_schema.json`、`source/schemas/shopping/{checkout,catalog_search}.json` | profile/catalog/checkout 长啥样的**金标准** |
| UCP spec / releases | github.com/Universal-Commerce-Protocol/ucp（现 `2026-04-08`） | 版本、新能力（Cart）、破坏性变更 |
| UCP 文档 | ucp.dev/documentation/ | 概念与指南 |
| OpenAI ACP | developers.openai.com/commerce（含 `specs/api/products`） | ACP feed 字段标准 |
| 示例产物 | `examples/glossier/*` | 一份端到端参考输出 |

### 8.3 已闭合的缺口：官方 schema 已真正接入
> 历史：曾经 `requirements.txt` 装了 `jsonschema` 却无人 import，docstring 谎称
> "validates against official schema"。这是「声明≠实现」的 bug。

现在已修复并**真正实现**：官方 `v2026-04-08` 的 profile schema 树（共 8 个文件，
沿 `$ref` 传递抓取）已 vendored 到 `refs/ucp-schema/2026-04-08/`，`ucp-validate`
用 `jsonschema` + `referencing` 做**离线**校验（无 `jsonschema` 时优雅 SKIP）。
关键细节：上游 `$ref` 按**文件路径**（相对 `source/`）解析而非按 `$id`，所以
加载时按路径建 registry 并剥掉 `$id`。我们自己生成的 profile（REST/MCP）实测
**0 error** 通过官方 schema，印证了生成端的契约正确性。

---

## 9. 一页速记（TL;DR）

- **是什么**：把电商网站翻译成 AI 可交易接口的**协议适配流水线**（B2B skill 包 / Codex 插件）。
- **解决什么**：让商家低成本接入 UCP 和 OpenAI ACP，变得"可被 agent 发现 + 下单"。
- **怎么组织**：audit→profile+catalog→checkout→validate 一条流水线，外加 catalog→acp-feed 分支。
- **为什么成立**：生成端和验证端**共享同一套契约**，形成自洽闭环。
- **靠什么可信**：确定性脚本 + 自洽验证 + 诚实的能力边界。
- **改代码的北极星**：任何改动都要保持"契约在流水线两端一致、声明与实现一致、与上游 spec 一致"。
</content>
</invoke>
