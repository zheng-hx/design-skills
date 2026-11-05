# 多 AI 工具安装指南

> 关键词：**先查看工具真实目录规则，再安装；只装检测到的工具目录，未检测到的不创建**。
> 本包默认把设计师技能装到**用户全局**，装一次所有项目都能用。
> 本文对应 `skills/install-design-skills/scripts/reconcile-skills.py` 与
> `tool-dirs.json` 的实际行为；两者不一致时以脚本与 `tool-dirs.json` 为准（`npm run audit` 会校验）。

---

## 1. 与旧包、与项目级模型的关键差异

- **默认用户全局**：旧版 `shuhe-role-skills` 只写**项目内**目录、还明确「禁止写用户主目录」，
  结果换个项目就找不到命令——这正是「全局技能没生效」的头号根因。
  本包改为：工作台 `~/.design/` 与注册到各工具**用户全局技能目录**，装一次全局可用。
- **按工具真实规则探测**：规则全部在 `tool-dirs.json`（单一事实源）。
  Codex 的全局目录是 **`~/.agents/skills`**，**不是 `~/.codex/skills`**（后者是旧版遗留，不是技能发现目录）；
  WorkBuddy 是 **`~/.workbuddy/skills`**——旧版工具表完全漏了它。
- **只写检测到的目录**：只用 WorkBuddy 时，绝不出现 `~/.agents/`；用户同时用了 Codex，才创建 `~/.agents/skills`。

第二个修正是**幂等模式不误报**：旧版在无任何安装动作时把清单里的 `mode` 统一写成 `symlink`，
实际可能是 `copy`。本版按技能逐个记录真实模式，重复执行结果恒定。

---

## 2. 扫描路径表（单一事实源 = `tool-dirs.json`）

判据是**用户全局工具根目录是否存在**（如 `~/.workbuddy`），不是「技能目录里有没有东西」，
也**不是「项目内有没有 `.claude/`」**（多数项目根本没这些点目录，旧判据会一个都检测不到）。

| # | 工具 | 用户全局技能目录 | 项目级技能目录 | 检测依据 | 说明 |
|---|---|---|---|---|---|
| 1 | **WorkBuddy** | `~/.workbuddy/skills` | `.workbuddy/skills` | `~/.workbuddy` | 本包首要目标，旧表漏了它 |
| 2 | **Codex**（OpenAI / ChatGPT Desktop） | **`~/.agents/skills`** | `.agents/skills` | `~/.codex` 或 `~/.agents` | 官方 USER 级是 `~/.agents/skills`；`~/.codex/skills` 是旧版遗留，**不可写** |
| 3 | Claude Code / Cline | `~/.claude/skills` | `.claude/skills` | `~/.claude` | Cline 兼容 `~/.claude/skills/` |
| 4 | Cursor | `~/.cursor/skills` | `.cursor/skills` | `~/.cursor` | Cursor 也读 `~/.agents/skills`/`~/.claude/skills`，仍写自己的目录 |
| 5 | CodeBuddy | `~/.codebuddy/skills` | `.codebuddy/skills` | `~/.codebuddy` | 原生 SKILL.md |
| 6 | OpenClaw | `~/.openclaw/skills` | `.openclaw/skills` | `~/.openclaw` | Agent Skills 开放标准 |
| 7 | Qoder | `~/.qoder/skills` | `.qoder/skills` | `~/.qoder` | 未本机实测，按同名约定 |
| 8 | Reasonix | `~/.reasonix/skills` | `.reasonix/skills` | `~/.reasonix` | 未本机实测，按同名约定 |

> **明令不可写的目录**（规则见 `tool-dirs.json` 的 `not_skill_dirs`）：
> `~/.codex/skills`（Codex 旧版遗留）、`~/.workbuddy`（工具根目录本身）、`.agents`（标记目录本身）。
> 表里的目录与 `tool-dirs.json` 一一对应；`npm run audit` 会校验「规则里每个目录是否都在本文列出」，
> 加新工具时**两边都要改**。

---

## 3. 安装命令

装到用户全局（默认），通常在 `/install-design-skills` 里自动跑，不需要手敲：

```bash
# 先探测本机有哪些工具（只读，不写任何文件）
python3 <install-design-skills 技能目录>/scripts/probe-tool-dirs.py

# 默认：用户全局、自动探测
python3 <install-design-skills 技能目录>/scripts/reconcile-skills.py --scope user

# 只装指定工具（显式指定即视为检测到）
python3 reconcile-skills.py --scope user --tool workbuddy --tool codex

# 项目级（团队共享、可提交 Git）：写项目内目录
python3 reconcile-skills.py --scope project --project .

# 测试隔离：用临时主目录，不碰真实 ~/.design/ 与全局工具目录
python3 reconcile-skills.py --scope user --home /tmp/fake-home --dry-run
```

| 参数 | 作用 |
|---|---|
| `--scope user\|project` | 默认取 `tool-dirs.json` 的 `default_scope`（user = 用户全局） |
| `--tool <key>` | 只装指定工具，可多次；显式指定视为检测到（即便根目录不存在也会建） |
| `--home` / `--project` | 覆盖主目录 / 项目根（测试用，不碰真实环境） |
| `--workbench` | 覆盖共享工作台路径（测试用） |
| `--mode auto\|symlink\|copy` | 默认 `auto`：优先软链，不支持时自动回退 `copy` |
| `--no-entries` | 不注册三个公开入口命令（默认注册） |
| `--dry-run` | 只报告不落盘，先看会动哪些文件 |

需要项目级工作台（团队共享）时加 `--scope project`，会把工作台放到 `<项目>/.design/`，
其余行为一致；项目级同样只写检测到的项目内标记目录。

---

## 4. 声明式对账规则

对每一个被检测到的工具目录，独立算一次：

```text
期望集合   = ~/.design/skills/ 下所有含 SKILL.md 的工种技能（19 core + 路由 + 长尾兜底）
            + 三个公开入口命令（apply / install / update）
本包拥有   = .design-managed.json 记录的 + 指向工作台/入口源的软链（含断链）
```

| 情况 | 动作 |
|---|---|
| 在期望集合内且类型 / 目标正确 | 保留，不计入变更 |
| 在期望集合内但过期或类型不一致 | 删除后重建 |
| 在期望集合内、工具目录里没有 | 新建软链 |
| 本包拥有但已不在期望集合 | 删除（清孤儿） |
| 不是本包拥有（用户自己的技能） | **绝不碰** |

要点：

- **软链目标用相对路径** `os.path.relpath(...)`，工作台整体移动 / 换机器后仍可用；
- 软链创建失败（Windows 无开发者模式、部分文件系统）自动回退 `copy`；`--mode symlink` 会明确报错，不静默降级；
- `copy` 模式用目录内容哈希判断是否过期，内容没变就不重建；
- 每个工具目录各写一份 `.design-managed.json`，互不干扰。

清单结构：

```json
{
  "package": "ai-design-skills",
  "scope": "user",
  "workbench": "/Users/you/.design",
  "managed": ["design-router", "design-any", "ui-design", "apply-design-skills"],
  "modes": {"design-router": "symlink", "ui-design": "copy"}
}
```

`modes` 按技能记录真实类型——这条是幂等复跑时不会把 `copy` 误报成 `symlink` 的关键。

---

## 5. 幂等与验收

重复执行同一命令，输出应当是 `新增 0 / 更新 0 / 移除 0`，且清单内容不变。

```bash
# 先看会动什么
python3 reconcile-skills.py --scope user --dry-run

# 真跑
python3 reconcile-skills.py --scope user

# 幂等复跑
python3 reconcile-skills.py --scope user
```

手工验收三条：

1. 每个检测到的工具目录下，技能名与 `~/.design/skills/` 一一对应，没有孤儿、没有断链；
2. 未检测到的目录仍然不存在（没有被「顺手」创建，如只用 WorkBuddy 时绝无 `~/.agents/`）；
3. 工具目录里你自己放的技能还在。

`npm run check-install` 是**真跑**的端到端回归：临时 HOME → 渲染工作台 → 按规则安装 →
多项断言，覆盖「只装检测到的目录 / 加 Codex 才建 ~/.agents / 幂等 / 清孤儿 /
用户技能共存 / 旧包清单共存 / copy 模式不误报 / 升级后 artifacts 保留」。

---

## 6. 与角色技能包共存

| | 角色技能包（`shuhe-role-skills`） | 本包 |
|---|---|---|
| 工作台 | 项目 / 用户目录 `角色相关` | 用户全局 `~/.design/` |
| 注册清单 | `.roles-managed.json` | `.design-managed.json` |
| 入口 | `/install-role-skills` | `/install-design-skills` |

两者**互不依赖、互不覆盖、互不清理对方的注册项**，可在同一环境同时安装。
本包对账时只认自己的清单和指向 `~/.design/skills/` 的软链，别的一概不动。

---

## 7. 版本升级时的注册

`/update-design-skills` 的三层顺序固定：

| 层 | 内容 | 方式 |
|---|---|---|
| ① 入口技能包 | 三个公开入口 | `npx skills add`（`update` 补不上新增技能） |
| ② 共享工作台 | `~/.design/` 管理区 | 替换式重渲染，`<项目>/.design/artifacts/` **绝不覆盖** |
| ③ 工具注册 | 所有检测到的工具**用户全局**目录 | `--scope user` 对账，多退少补 |

工种集合改了（比如从 19 个 core 缩到 2 个子集）后，第 ③ 层会自动清掉多出来的孤儿；
新增工种会自动补上。仓库地址优先读 `~/.design/design.json` 的 `source`，
其次环境变量 `AI_DESIGN_SKILLS_REPO`，都没有就明确报错，不编地址。

---

## 8. 故障排查

| 现象 | 原因 / 处理 |
|---|---|
| 报「未找到 ~/.design/skills/」 | 还没跑 `/apply-design-skills`，先生成工作台 |
| 报「未检测到任何 AI 工具目录」 | 本机用户全局下没有对应工具根；先初始化对应工具，或用 `--tool` 指定 |
| 命令在新工具里不出现 | 该工具是后来才装的；重跑一次 `--scope user` 即可 |
| 软链变成实体目录 | 文件系统不支持软链，脚本回退了 `copy`；查清单 `modes` 确认 |
| 改了工种，旧命令还在 | 只重渲染没重跑安装；补一次对账清孤儿 |
| 用户自己写的技能被删了 | 不应发生。请提交 issue 并附上 `.design-managed.json` 与目录结构 |
| Windows 上软链创建失败 | 开开发者模式，或显式 `--mode copy` |

---

> **作者：zhenghx**
