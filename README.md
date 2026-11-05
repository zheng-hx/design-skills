# 全行业设计师技能包（ai-design-skills）

> **设计师技能是人的能力，默认装到用户全局**：共享工作台 `~/.design/` + 注册到各 AI 工具的**用户全局技能目录**。
> 装一次，这台机器上所有项目、所有已用的 AI 工具都能调用。
>
> 覆盖 4 域 **37 个设计工种**，共用一套设计引擎；支持版本升级，支持按**各 AI 工具真实的技能目录规则**扫描安装。
>
> 本包只公开一个入口：`/ai-design-skills`（初始化生成工作台 / 注册到工具 / 更新，三件事合一）。
> 工种技能本身是**渲染出来的自包含模板**，生成后落在全局工作台。

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

所有工种共用 `~/.design/rules/` 下的交互节奏、状态机、评审、产物规范、人格与通用红线；
工种自己的 `SKILL.md` 只写阶段表、产物与参考路由。

- **第 0 阶段**：先确认现状（现有设计系统 / 品牌 / 参考 / 媒介 / 场地约束），拿不到就问，问不到就停。
- **一次一问**：沿决策树推进，安全默认值不占提问额度。
- **收口**：对话内出结论卡片 → 落盘驱动卡 `00-summary.md` → **确认后才进生产**。
- **不编造**：审批人、数据、期限、案例一律标 `[缺失·阻塞]`；字体 / 图片 / 素材授权必须核验。
- **不假交付**：给不出的施工图、打样件、可印制原文件如实说明。

## 快速开始

> **前置**：Node.js `>= 22.20.0`（`skills` CLI 要求）；渲染脚本用 Python 3 标准库，无第三方依赖。
> 本仓库是**技能源**，不是可执行的 npm CLI。

```bash
# <REPO_URL> 换成本包实际发布地址；不硬编码、不猜
npx skills@latest add <REPO_URL>
```

然后在任意 AI 工具里（**装一次，所有项目可用**）：

```text
/ai-design-skills     # 确认工种 → 渲染全局工作台 ~/.design/ → 按各工具真实目录规则探测并注册；或直接说「更新设计技能」
```

> `/ai-design-skills` 只问一次工种（默认 19 个 core），确认后直接渲染；
> 不会再追问公司、产品、责任人、术语表等信息。想装子集：`--disciplines ui-design,brand-design`。

## 全局安装（本包的关键改造）

**先查看规则，再安装**。装错目录 = 技能不生效，这是「全局技能没生效」最常见的根因。
安装前 `reconcile-skills.py` 先按 `tool-dirs.json`（**单一事实源**）探测本机用户全局目录下有哪些工具，
只向检测到的工具目录建软链；未检测到的一律不创建。

```bash
python3 <ai-design-skills 技能目录>/scripts/probe-tool-dirs.py   # 只看本机有哪些工具
python3 <ai-design-skills 技能目录>/scripts/reconcile-skills.py --scope user
```

三个最常见坑（完整规则见 [多 AI 工具安装指南](docs/install-by-tool.md)）：

1. **Codex 的全局目录是 `~/.agents/skills`，不是 `~/.codex/skills`**（后者是旧版遗留，不是技能发现目录）；
2. **WorkBuddy 是 `~/.workbuddy/skills`**——旧版工具表完全漏了它；
3. 检测依据是**用户全局工具根是否存在**（如 `~/.workbuddy`），不是「项目里有没有 `.claude/`」。

| 工具 | 用户全局技能目录 | 项目级技能目录 |
|---|---|---|
| **WorkBuddy** | `~/.workbuddy/skills` | `.workbuddy/skills` |
| **Codex** | **`~/.agents/skills`** | `.agents/skills` |
| Claude Code / Cline | `~/.claude/skills` | `.claude/skills` |
| Cursor | `~/.cursor/skills` | `.cursor/skills` |
| CodeBuddy | `~/.codebuddy/skills` | `.codebuddy/skills` |
| OpenClaw | `~/.openclaw/skills` | `.openclaw/skills` |
| Qoder | `~/.qoder/skills` | `.qoder/skills` |
| Reasonix | `~/.reasonix/skills` | `.reasonix/skills` |

> 只用 WorkBuddy 时**绝不出现 `~/.agents/`**；同时用了 Codex，才创建 `~/.agents/skills`。
> 唯一公开入口命令（`ai-design-skills`）默认一并注册，保证换到任何项目都能调用「全局初始化」。

对账是**声明式、幂等**的：多退少补、清孤儿、不清用户自己的技能；清单 `.design-managed.json`
按技能记录真实安装模式（修掉旧版幂等时把 `copy` 误记成 `symlink` 的问题）。

## 版本与升级

版本事实源是 `skills/ai-design-skills/VERSION`（住在技能目录里，因为
`npx skills add` 只拷技能目录，仓库根的 `package.json` 带不过去）。升级三层、顺序固定：

| 层 | 内容 | 方式 |
|---|---|---|
| ① 入口技能包 | 唯一公开入口 | `npx skills add`（`update` 补不上新增技能） |
| ② 共享工作台 | `~/.design/` 管理区 | 替换式重渲染，`<项目>/.design/artifacts/` **绝不覆盖** |
| ③ 工具注册 | 所有检测到的工具**用户全局**目录 | `--scope user` 对账，多退少补 |

仓库地址优先读 `~/.design/design.json` 的 `source`，其次环境变量 `AI_DESIGN_SKILLS_REPO`，
再次目标项目 `skills-lock.json`；**都没有就明确报错，不编地址**。版本分流含未初始化 / 补档 / 升级 /
已最新 / **拒绝降级** 五种模式。

## 目录结构（技能源仓库）

```text
skills/
└── ai-design-skills/                # 唯一公开入口（初始化 / 注册 / 更新 合一）
    ├── SKILL.md  VERSION  agents/
    ├── tool-dirs.json                #   AI 工具目录规则（单一事实源）
    ├── scripts/
    │   ├── build-disciplines.py      # 从注册表生成工种模板（维护者用，含 --check）
    │   ├── render-design-package.py  # 渲染 + 逐字保真核对 + 结构校验
    │   ├── verify-render.py
    │   ├── reconcile-skills.py       # 按工具真实目录规则对账注册
    │   ├── probe-tool-dirs.py        # 只读探测本机 AI 工具
    │   └── tool_dirs.py              # 规则读取口
    └── capabilities/                 # 隐藏层（CAPABILITY.md / .md.tpl，不可被发现）
        ├── design-core/              #   公共引擎 + disciplines.json 注册表
        └── design-disciplines/       #   19 core 技能 + 2 入口 + 9 参考 + 产物模板
```

渲染产物（全局工作台 + 当前项目作品）：

```text
~/.design/                            # 用户全局工作台（共享引擎，只存一份）
├── design.json  disciplines.json
├── rules/  templates/  references/
├── skills/<工种>/{SKILL.md, agents/}
└── （不含用户作品）

<当前项目>/.design/artifacts/         # ⚠️ 用户作品，按项目隔离，升级绝不覆盖
```

## 发布前校验

```bash
npm run check:all
# check-version / 包结构 / 触发词 / 评测自洽 / 多工具安装回归 / 渲染 dry-run / 仓库卫生
```

单项：`npm run check`、`npm run check-triggers`、`npm run check-evals`、
`npm run check-install`、`npm run verify-render`、`npm run audit`。
其中 `check-install` 是**真跑**的端到端回归（临时 HOME → 渲染 → 按规则安装 → 35 项断言）；
`check-evals` 校验触发金标集覆盖与评测断言结构。

行为评测（给一段真实人话，验产出对不对）见 `evals/`；它需要在装好技能的项目里真跑，
仓库里的校验只保证评测文件本身没写坏。

## 文档

- [工种全景](docs/工种全景.md) — 37 工种清单与分层口径
- [设计流水线](docs/设计流水线.md) — 公共底座与各域阶段表
- [AI 工具目录规则](docs/AI工具目录规则.md) — **安装前必读**：全局 / 项目技能目录真实规则与官方出处
- [多 AI 工具安装指南](docs/install-by-tool.md) — 探测、软链对账、幂等与版本升级
- [快速上手](docs/quickstart.md)
- [开源资料与致谢](docs/开源资料与致谢.md) — GitHub 调研结果与许可红线
- [开发待办](docs/todo.md)

## 许可

MIT。第三方开源资料的许可边界见 [开源资料与致谢](docs/开源资料与致谢.md) 与
`~/.design/references/许可与来源规范.md`：**MIT / Apache-2.0 可借鉴表达与结构，
NC-SA / 待核实 / 无 LICENSE 只借方法论**。

---

> **作者：zhenghx**
