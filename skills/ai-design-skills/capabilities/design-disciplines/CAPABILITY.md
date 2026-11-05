---
name: design-disciplines
description: 设计工种层 — 全行业工种技能（core 独立技能 + extended 索引兜底）、深度参考与产物模板。用同名 rules/ 文件覆盖 design-core 的默认。
---

# Design Disciplines — 工种层

**单角色多工种**：整个包渲染成 `.design/`，所有工种共享同一套引擎、人格与产物规范，
差异只在各自的 `SKILL.md`（阶段表 / 产物 / 门禁 / 参考路由）。

## 内容

```text
design-disciplines/
├── references/                     # 9 份，按需加载（与注册表 shared_references 完全对账）
│   ├── 工种索引.md                  ← 由 build-disciplines.py 生成（37 工种）
│   ├── 开源资料索引.md              ← 由 build-disciplines.py 生成
│   ├── 工种通用流水线.md            ← extended 工种兜底
│   ├── 数字产品质量基线.md          ← 整合 MIT 开源检查表结构
│   ├── 视觉与品牌基础.md
│   ├── 立体与空间交付边界.md
│   ├── 可访问性细则.md              ← 逐字复用（WCAG 2.2 AA）
│   ├── AI生成设计缺陷清单.md        ← 逐字复用
│   └── 许可与来源规范.md
├── templates/                      # 9 份产物模板（复用自旧包，字段名已适配）
└── skills/
    ├── design-router/              # 手写：总入口与跨工种分流
    ├── design-any/                 # 手写：长尾工种通用流水线
    └── <19 个 core 工种>/          # 由 build-disciplines.py 从注册表生成
```

## 分层交付

| 层 | 数量 | 形态 |
|---|---|---|
| `core` | 19 | 独立 `SKILL.md` + `agents/openai.yaml` + 专属流水线 / 产物 / 参考路由 |
| `extended` | 18 | 只在 `工种索引.md` 登记，由 `/design-any` 走通用流水线 |
| 入口 / 兜底 | 2 | `design-router`、`design-any` |

> **为什么不都做成技能**：30+ 斜杠命令会让触发词互相抢；线下工种 AI 给不出可施工 / 可打样的
> 交付物，做成完整技能等于假交付。索引登记 + 通用兜底既能覆盖，又不撒谎。

## 生成物纪律

- `disciplines.json` 是**单一事实源**；改工种只改 JSON，跑 `build-disciplines.py` 重生成。
- `design-router` / `design-any` 是手写的，生成器把它们列入白名单，不会被 `--check` 判为残留。
- 只有 `core` 工种才会被渲染进 `.design/skills/`；`extended` 不占工具目录的命令位。
- 渲染时按 `design.json` 的 `disciplines` 过滤，支持子集安装。

## 触发词纪律

`disciplines.json` 里每个工种的 `triggers` 全局不重复（生成器自检 + `check-triggers.py` 复核）。
相近但不完全相同的说法（如「海报排版」vs「海报设计」）属于自然语言正常歧义，
`extended` 工种的触发词只作索引登记，不会造成命令冲突。

## 与其他包的关系

本包产物目录 `.design/`，与旧版角色包目录互不覆盖，**可在同一项目共存**。
注册到工具目录时各自维护自己的清单（`.design-managed.json`），互不干扰。
