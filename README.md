# 全行业设计师技能包（ai-design-skills）

> **一个项目 = 一个设计师技能包，包里按工种分技能。**
> 覆盖 4 域 **37 个设计工种**，共用一套设计引擎；支持版本升级，支持多 AI 工具按扫描路径软链安装。
>
> 本包只公开三个入口：`/apply-design-skills`（生成）、`/install-design-skills`（注册）、`/update-design-skills`（更新）。
> 工种技能本身是**渲染出来的自包含模板**，生成后属于目标项目。

## 它解决什么

设计师不该被迫学流水线、模板或工程术语。生成后，使用者只需一句话：

```text
/design-router 我要做一个新品牌，官网和包装都要
/ui-design 帮我做登录页的界面稿
/brand-design 我们品牌要升级 VI
/design-any 帮我看看这个展台的动线
```

技能按**自己的工种流水线**推进：第 0 阶段先确认现状 → 一次一问把需求问清 → 收口经你确认 → 才产出产物，关键内容直接展示在对话里。

## 核心约定

### 分层交付（关键设计）

全行业 37 个工种，**不都做成技能**：

| 层 | 数量 | 形态 | 理由 |
|---|---|---|---|
| `core` | 19 | 独立 `SKILL.md` + 专属流水线 / 产物 / 参考路由 | 高频、AI 能给出可验收产物 |
| `extended` | 18 | 登记在 `工种索引.md`，由 `/design-any` 通用流水线兜底 | 长尾，或强依赖 CAD / 打样 / 材料 / 资质 |
| 入口 / 兜底 | 2 | `/design-router`、`/design-any` | 分流与覆盖 |

> **为什么**：30+ 斜杠命令会让触发词互相抢；室内、服装、建筑这类工种 AI 给不出可施工 / 可打样的交付物，
> 做成完整技能等于**假交付**。索引登记 + 通用兜底既能覆盖，又不撒谎——`/design-any` 第 0 步会明确列出
> 「我能给什么、不能给什么」。

### 工种全景

| 域 | 数量 | core 工种 | extended（走兜底） |
|---|---|---|---|
| **数字产品** | 12 | UI / UX / 交互 / 产品 / 视觉 / 网页 / 动效 / 设计系统 / 可访问性 / 设计研究 | 游戏 UI、原型与线框 |
| **平面品牌** | 12 | 平面 / 品牌 VI / 包装 / 字体排版 / 插画 / 信息图 / AI 生成设计 | Logo、印前、装帧版式、海报广告、图标 |
| **空间与实体** | 9 | 3D 建模与渲染 | 室内、建筑景观、工业造型、服装、展览舞美、影视美术、家具、珠宝 |
| **商业与新兴** | 4 | 电商视觉 | 服务设计、设计运营、导视与空间图形 |

完整清单（含触发词、流水线、产物、来源）见 [工种全景](docs/工种全景.md) 与
`capabilities/design-core/disciplines.json`（**单一事实源**）。

### 共享引擎，工种只写差异

所有工种共用 `.design/rules/` 下的交互节奏、状态机、评审、产物规范、人格与通用红线；
工种自己的 `SKILL.md` 只写阶段表、产物与参考路由。

- **第 0 阶段**：先确认现状（现有设计系统 / 品牌 / 参考 / 媒介 / 场地约束），拿不到就问，问不到就停。
- **一次一问**：沿决策树推进，安全默认值不占提问额度。
- **收口**：对话内出结论卡片 → 落盘驱动卡 `00-summary.md` → **确认后才进生产**。
- **不编造**：审批人、数据、期限、案例一律标 `[缺失·阻塞]`；字体 / 图片 / 素材授权必须核验。
- **不假交付**：给不出的施工图、打样件、可印制原文件如实说明。

## 快速开始

> **前置**：Node.js `>= 22.20.0`（`skills` CLI 要求）；渲染脚本用 Python 3 标准库，无第三方依赖。
> 本仓库是**技能源**，不是可执行的 npm CLI。

在**目标项目根目录**：

```bash
# <REPO_URL> 换成本包实际发布地址；不硬编码、不猜
npx skills@latest add <REPO_URL>
```

然后在 AI 工具里：

```text
/apply-design-skills     # 只确认启用哪些工种 → 生成 .design/
/install-design-skills   # 扫描项目内所有 AI 工具目录 → 注册，命令立即可用
/update-design-skills    # 或直接说「更新设计技能」
```

> `/apply-design-skills` 只问一次工种（默认 19 个 core），确认后直接渲染；
> 不会再追问公司、产品、责任人、术语表等信息。想装子集：`--disciplines ui-design,brand-design`。

## 多 AI 工具安装（本包的关键改造）

参考项目 `shuhe-role-skills` 的 `/install-role-skills` 是「按目录特征检测，**取第一个匹配**」——
只装到第一个工具目录，多 AI 工具并用时其余工具读不到命令。本包改为：

```text
扫描项目内所有已存在的 AI 工具目录
  → 检测到的每一个都建软链、各自做声明式对账
  → 未检测到的目录一律不写、不擅自创建
```

```bash
python3 <install-design-skills 技能目录>/scripts/reconcile-skills.py \
  --project . --scan
```

| 工具 | 检测特征 | 技能目录 |
|---|---|---|
| Claude Code / Cline | `.claude/` | `.claude/skills/` |
| Codex | `.codex/` | `.codex/skills/` |
| 通用 Agent Skills | `.agents/` | `.agents/skills/` |
| Cursor | `.cursor/` | `.cursor/skills/` |
| OpenClaw | `.openclaw/` | `.openclaw/skills/` |
| CodeBuddy | `.codebuddy/` | `.codebuddy/skills/` |
| Qoder | `.qoder/` | `.qoder/skills/` |
| Reasonix | `.reasonix/` | `.reasonix/skills/` |

对账是**声明式、幂等**的：多退少补、清孤儿、不清用户自己的技能；清单 `.design-managed.json`
按技能记录真实安装模式（修掉旧版幂等时把 `copy` 误记成 `symlink` 的问题）。
详见 [多 AI 工具安装指南](docs/install-by-tool.md)。

## 版本与升级

版本事实源是 `skills/apply-design-skills/VERSION`（`npx skills add` 只拷技能目录，仓库根的
`package.json` 带不过去）。升级三层、顺序固定：

| 层 | 内容 | 方式 |
|---|---|---|
| ① 入口技能包 | 三个公开入口 | `npx skills add`（`update` 补不上新增技能） |
| ② 项目工种包 | `.design/` 管理区 | 替换式重渲染，`artifacts/` **绝不覆盖** |
| ③ 工具注册 | 所有检测到的工具目录 | `--scan` 对账，多退少补 |

仓库地址优先读目标项目的 `skills-lock.json`，其次环境变量 `AI_DESIGN_SKILLS_REPO`；
**都没有就明确报错，不编地址**。版本分流含未初始化 / 补档 / 升级 / 已最新 / **拒绝降级** 五种模式。

## 目录结构（技能源仓库）

```text
skills/
├── apply-design-skills/              # 公开入口①
│   ├── SKILL.md  VERSION  agents/
│   ├── scripts/
│   │   ├── build-disciplines.py      # 从注册表生成工种模板（维护者用，含 --check）
│   │   ├── render-design-package.py  # 渲染 + 逐字保真核对 + 结构校验
│   │   └── verify-render.py
│   └── capabilities/                 # 隐藏层（CAPABILITY.md / .md.tpl，不可被发现）
│       ├── design-core/              #   公共引擎 + disciplines.json 注册表
│       └── design-disciplines/       #   19 core 技能 + 2 入口 + 9 参考 + 产物模板
├── install-design-skills/            # 公开入口②
│   └── scripts/reconcile-skills.py   #   扫描多工具 + 声明式对账
└── update-design-skills/             # 公开入口③
```

渲染产物在项目里：

```text
.design/
├── design.json  disciplines.json
├── rules/  templates/  references/
├── skills/<工种>/{SKILL.md, agents/}
└── artifacts/                        # ⚠️ 用户作品，升级绝不覆盖
```

## 与 shuhe-role-skills 共存

| | 角色技能包 | 本包 |
|---|---|---|
| 产物目录 | `.roles/` | `.design/` |
| 组织 | 一个项目一个角色（5 选 1） | 一个项目一个包，包内按工种分技能 |
| 注册清单 | `.roles-managed.json` | `.design-managed.json` |
| 注册命令 | `/install-role-skills` | `/install-design-skills` |

两者**互不依赖、互不覆盖、互不清理对方的注册项**，可在同一项目同时安装。
5 份工种无关的引擎规则复用自 `shuhe-role-skills`（MIT），**并把产物路径对齐到 `.design/`、
把「角色」措辞对齐为「工种」**（否则渲染后 AI 会按旧路径读不存在的文件）；2 份设计参考逐字复用。
`npm run check` 会拦截渲染内容里残留的旧包路径与失效引用。

## 发布前校验

```bash
npm run check:all
# check-version / 包结构 / 触发词 / 评测自洽 / 多工具安装回归 / 渲染 dry-run / 仓库卫生
```

单项：`npm run check`、`npm run check-triggers`、`npm run check-evals`、
`npm run check-install`、`npm run verify-render`、`npm run audit`。
其中 `check-install` 是**真跑**的端到端回归（临时项目 → 渲染 → 扫描安装 → 30 项断言）；
`check-evals` 校验触发金标集覆盖与评测断言结构。

行为评测（给一段真实人话，验产出对不对）见 `evals/`；它需要在装好技能的项目里真跑，
仓库里的校验只保证评测文件本身没写坏。

## 文档

- [工种全景](docs/工种全景.md) — 37 工种清单与分层口径
- [设计流水线](docs/设计流水线.md) — 公共底座与各域阶段表
- [多 AI 工具安装指南](docs/install-by-tool.md)
- [快速上手](docs/quickstart.md)
- [开源资料与致谢](docs/开源资料与致谢.md) — GitHub 调研结果与许可红线
- [开发待办](docs/todo.md)

## 许可

MIT。第三方开源资料的许可边界见 [开源资料与致谢](docs/开源资料与致谢.md) 与
`.design/references/许可与来源规范.md`：**MIT / Apache-2.0 可借鉴表达与结构，
NC-SA / 待核实 / 无 LICENSE 只借方法论**。

---

> **作者：zhenghx**
