---
name: design-core
description: 全工种共享的默认层 — 交互节奏、状态机、评审、产物规范与工种注册表。工种包用同名文件覆盖 rules/ 下的内容。
---

# Design Core — 公共默认层

**分层原则：机制在公共层，工种差异在工种层。** 所有设计工种共用同一套引擎逻辑，但每个工种有自己的阶段表、产物与门禁。

## 内容

```text
design-core/
├── disciplines.json            # 全行业工种注册表（单一事实源）
├── rules/
│   ├── 交互模式.md              # 一次一问·决策树·对话内展示（复用 shuhe-role-skills）
│   ├── 状态机与收口.md          # 六态、收口、交付前四步（复用）
│   ├── 循环引擎.md              # 自动推进与人工门禁停机（复用）
│   ├── 评审子智能体.md          # 双轴独立评审（复用）
│   ├── 产物与来源规范.md        # frontmatter / dossier / 来源标记（复用）
│   ├── 人格.md                 # 设计工种共通身份与口径
│   └── 设计通用规范.md          # 所有工种必须遵守的红线
└── templates/
    ├── design.json.tpl         # → .design/design.json（配置）
    ├── README.md.tpl           # → .design/README.md
    └── 00-summary.md.tpl       # 驱动卡（收敛时落盘）
```

## 渲染契约

1. `rules/` 先写 `design-core/rules/*`，再用 `design-disciplines/rules/*` 同名覆盖；
2. `templates/` 取两层合集，`*.md.tpl` 去 `.tpl`；`README.md.tpl` 出到 `.design/` 根；
3. `references/` 取两层合集，逐字复制（不渲染）；
4. `skills/` 只从 `design-disciplines/skills/` 取，按本次选定的工种过滤；
5. `disciplines.json` 逐字复制进 `.design/`，供 `design-router` / `design-any` 运行时查询。

## 与 shuhe-role-skills 的关系

5 份工种无关的引擎规则复用自 `shuhe-role-skills/capabilities/role-core/rules/`，保持行为一致；
**复用时已把产物路径对齐到 `.design/`、把「角色」措辞对齐为「工种」**，并修掉驱动卡与产物模板里
指向旧包不存在文件的失效引用——逐字照搬会让渲染后的 AI 去读不存在的路径。
`npm run check`（`validate-package.py` 第 8 项）会拦截渲染内容里残留的 `.roles/` 与失效引用。
`人格.md` 与 `设计通用规范.md` 是本包新增，面向设计工种。两个包产物目录不同（`.design/` vs `.roles/`），
**可在同一项目共存、互不覆盖**。

## 升级契约

| 类别 | 路径 | 升级时 |
|---|---|---|
| 管理区（生成物） | `.design/rules/`、`templates/`、`references/`、`skills/`、`design.json`、`disciplines.json`、README | 可整体重建 |
| 用户区（作品） | `.design/artifacts/` | **绝不覆盖、绝不删除** |
