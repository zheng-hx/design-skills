# AI 工具技能目录规则（安装前必读）

> **为什么有这篇**：技能写对了、装错目录 = 不生效。这是「全局技能没生效」最常见的根因。
> 本包安装前**先探测**各工具真实的全局 / 项目技能目录，再决定往哪装；规则单一事实源是
> `skills/install-design-skills/tool-dirs.json`，脚本与本文都从它读。
>
> 调研日期：2026-11-05。本机实测 + 官方文档双证据。

---

## 1. 两个作用域

| 作用域 | 含义 | 本包默认 |
|---|---|---|
| **user（用户全局）** | 装一次，这个用户的所有项目都能用 | ✅ **默认** |
| **project（项目级）** | 只在当前项目生效，通常可提交进 Git 给团队共享 | 可选，`--scope project` |

设计师技能是**人的能力**，不是某个项目的配置——所以本包默认全局。
但**产物不是**：设计稿、驱动卡、来源一律写当前工作目录的 `.design/artifacts/`，
全局工作台只放规则与技能，避免 A 项目的稿子跑到 B 项目。

```text
~/.design/                     ← 全局工作台（共享引擎，一份）
├── design.json / disciplines.json
├── rules/  templates/  references/  skills/
└── README.md
        │ 软链
        ├── ~/.workbuddy/skills/<工种>/     ← WorkBuddy 用户全局
        ├── ~/.agents/skills/<工种>/        ← Codex 用户全局
        └── ~/.claude/skills/<工种>/        ← Claude Code 用户全局

<当前项目>/.design/artifacts/  ← 用户作品，按项目隔离，升级绝不覆盖
```

---

## 2. 规则表（按工具真实约定）

| 工具 | 用户全局技能目录 | 项目级技能目录 | 检测依据（用户全局） | 标准 |
|---|---|---|---|---|
| **WorkBuddy** | `~/.workbuddy/skills` | `.workbuddy/skills` | `~/.workbuddy/` | WorkBuddy 内置约定 |
| **Codex**（OpenAI / ChatGPT Desktop） | **`~/.agents/skills`** | `.agents/skills` | `~/.codex/` 或 `~/.agents/` | Agent Skills 开放标准 |
| **Claude Code / Cline** | `~/.claude/skills` | `.claude/skills` | `~/.claude/` | Claude Code Skills |
| **Cursor** | `~/.cursor/skills`（也读 `~/.agents/skills`、`~/.claude/skills`） | `.cursor/skills`、`.agents/skills` | `~/.cursor/` | Cursor Agent Skills |
| **CodeBuddy** | `~/.codebuddy/skills` | `.codebuddy/skills` | `~/.codebuddy/` | 原生 SKILL.md |
| **OpenClaw** | `~/.openclaw/skills` | `.openclaw/skills` | `~/.openclaw/` | Agent Skills 开放标准 |
| **Qoder** | `~/.qoder/skills` | `.qoder/skills` | `~/.qoder/` | SKILL.md 兼容（未实测） |
| **Reasonix** | `~/.reasonix/skills` | `.reasonix/skills` | `~/.reasonix/` | 原生 SKILL.md（未实测） |

> 完整字段（环境变量、官方出处、备注）在 `tool-dirs.json`。加新工具只改 JSON，脚本与本文表格靠校验对账。

### 三个最容易踩的坑

1. **Codex 不是 `~/.codex/skills`**。OpenAI 官方《Build skills》写得很清楚：
   `USER = $HOME/.agents/skills`，`REPO = $CWD/.agents/skills`（从 cwd 一路扫到 repo root），
   `ADMIN = /etc/codex/skills`。`~/.codex/skills` 只是旧版遗留，`$skill-installer` 放技能的地方，
   不是发现目录。本机实测也印证：`~/.codex/skills/` 是空的，`~/.agents/skills/` 有 33 个技能。
2. **工具根目录 ≠ 技能目录**。`~/.workbuddy/` 是工具根目录，技能必须放 `~/.workbuddy/skills/`，
   少一层就不会被扫到。
3. **`~/.agents/skills` 会被多个工具读**（Codex / Cursor / Windsurf），
   所以它是事实上的「一份装、多工具生效」目录；但 Claude Code 仍只认 `~/.claude/skills`，
   WorkBuddy 仍只认 `~/.workbuddy/skills`——**不能只装一个目录就指望全生效**。

---

## 3. 本机实测（2026-11-05）

| 用户全局目录 | 存在 | 已有技能数 |
|---|---|---|
| `~/.workbuddy/skills` | ✅ | 19 |
| `~/.agents/skills` | ✅ | 33 |
| `~/.codebuddy/skills` | ✅ | 38 |
| `~/.openclaw/skills` | ✅ | 7 |
| `~/.claude/skills` | ✅ | 3（其中 3 个是软链，指向 `~/.agents/skills`） |
| `~/.codex/skills` | ✅ | **0** |
| `~/.cursor/skills`、`~/.qoder/skills`、`~/.reasonix/skills` | ❌ | — |

项目里则几乎**没有**任何 `.claude/`、`.cursor/`、`.agents/` 之类的点目录。
这解释了旧版为什么一个工具都检测不到：它看的是项目内 marker，而真实生效的是用户全局目录。

---

## 4. 探测与安装

```bash
# ① 先查看规则与本机检测结果（只读，不写任何文件）
python3 <install-design-skills>/scripts/probe-tool-dirs.py

# ② 只看某几个工具（模拟「只用 WorkBuddy」）
python3 probe-tool-dirs.py --tool workbuddy
python3 probe-tool-dirs.py --tool workbuddy --tool codex

# ③ 按探测结果安装（默认用户全局）
python3 <install-design-skills>/scripts/reconcile-skills.py --scope user

# ④ 项目级（可选）
python3 reconcile-skills.py --scope project --project <项目根>
```

**硬规则**：

- ✅ 检测到的工具，才往它对应的目录装；
- ❌ 未检测到的工具，**一个目录都不创建**——只用 WorkBuddy 时绝不出现 `~/.agents/`；
  同时用了 Codex，才写 `~/.agents/skills`；
- ❌ 不写工具根目录本身、不写旧版目录（如 `~/.codex/skills`）；
- ❌ 不碰用户自己放进技能目录的技能；
- ✅ 每个目录独立对账、独立清单（`.design-managed.json`），幂等、多退少补。

---

## 5. 官方出处

| 来源 | 结论 |
|---|---|
| OpenAI Codex《Build skills》 | USER `$HOME/.agents/skills`，REPO `.agents/skills`，ADMIN `/etc/codex/skills`；支持软链技能目录 |
| Claude Code Skills 文档 | 个人 `~/.claude/skills`，项目 `.claude/skills`；同名优先级 企业 > 个人 > 项目 |
| Cursor Agent Skills 文档 | `~/.cursor/skills`、`~/.agents/skills`，项目 `.cursor/skills`；也读 `~/.claude/skills` |
| agentskills.io 规范 | SKILL.md 格式、`~/.agents/skills` 与 `.agents/skills` |
| WorkBuddy 内置约定 | 用户级技能默认 `~/.workbuddy/skills`，项目级 `{workspace}/.workbuddy/skills` |
| 本机 `install-skill` 技能 | 「Codex 项目本地技能目录必须使用 `.agents/skills/`，`.codex/skills/` 不是技能发现目录」 |

---

## 6. 加新工具

1. 先查官方文档确认**用户全局**与**项目级**两个路径，不要凭目录名猜；
2. 改 `tool-dirs.json`：加 `key / name / detect_user / detect_project / env / user_skills / project_skills / standard / note`；
3. 同步在本文第 2 节加一行——`npm run audit` 会校验「规则表里的工具与目录是否都在本文列出」；
4. 跑 `npm run check:all`，其中 `check-install` 会在临时 HOME 里真跑一遍安装。

---

> **作者：zhenghx**
