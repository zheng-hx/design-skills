---
name: install-design-skills
description: 当已生成设计工作台、需要把工种技能注册到 AI 工具时使用：先按各工具真实规则探测用户全局/项目级技能目录，只向检测到的工具目录建软链并做声明式对账，三个全局初始化入口一并注册。当用户说「安装设计技能/技能没生效/换个工具也要能用/命令没出现」时使用。
---

# Install Design Skills — 按工具真实规则注册到全局

> **先查看规则，再安装**。装错目录 = 技能不生效，这是「全局技能没生效」最常见的根因。
> 本技能默认 `--scope user`（用户全局）：装一次，所有项目都能用。

---

## 为什么需要这个命令

`/apply-design-skills` 只把技能写进共享工作台 `~/.design/skills/`，
AI 工具**不会自动扫描**它。分工：

| 位置 | 角色 |
|---|---|
| `~/.design/` | 共享工作台，规则与技能的单一事实源 |
| 各工具用户全局技能目录 | 本地注册产物（软链），随时可重新对账 |
| `<项目>/.design/artifacts/` | 用户作品，与注册无关 |

### 最容易踩的三个坑（先记住）

1. **Codex 的全局目录是 `~/.agents/skills`，不是 `~/.codex/skills`**（后者是旧版遗留）。
2. **WorkBuddy 是 `~/.workbuddy/skills`**——旧版工具表完全漏了它。
3. **看项目内有没有 `.claude/` 是错的判据**：真实生效的是用户全局目录，
   而多数项目里根本没有这些点目录。检测依据应是 `~/.<工具>/` 是否存在。

完整规则与官方出处见 [AI 工具目录规则](../../docs/AI工具目录规则.md) 与
`skills/install-design-skills/tool-dirs.json`（**单一事实源**）。

---

## 工作流程

### Step 1: 先探测（只读，不写任何文件）

```bash
python3 <本技能目录>/scripts/probe-tool-dirs.py
```

输出每个工具：检测依据、该写哪个技能目录、目录是否已存在、本次是否写入。
`--scope project` 看项目级；`--tool workbuddy` 只看指定工具；`--json` 供脚本消费。

| 工具 | 用户全局技能目录 | 项目级技能目录 |
|---|---|---|
| **WorkBuddy** | `~/.workbuddy/skills` | `.workbuddy/skills` |
| **Codex** | **`~/.agents/skills`** | `.agents/skills` |
| Claude Code / Cline | `~/.claude/skills` | `.claude/skills` |
| Cursor | `~/.cursor/skills` | `.cursor/skills` |
| CodeBuddy | `~/.codebuddy/skills` | `.codebuddy/skills` |
| OpenClaw | `~/.openclaw/skills` | `.openclaw/skills` |
| Qoder / Reasonix | `~/.qoder/skills` / `~/.reasonix/skills` | 同名项目级 |

**硬规则**：

- ✅ **检测到的工具才写**，每个工具写自己对应的目录；
- ❌ **未检测到的一律不写、不创建目录**——只用 WorkBuddy 时绝不出现 `~/.agents/`；
  同时用了 Codex，才创建 `~/.agents/skills`；
- ❌ 不写工具根目录本身、不写 `~/.codex/skills` 这类旧版目录；
- ✅ 检测到的工具如果 `skills/` 子目录还不存在，**允许创建**它（很多工具从没建过）。

### Step 2: 一律调用对账脚本，不要手拍

```bash
python3 <本技能目录>/scripts/reconcile-skills.py --scope user
```

| 参数 | 作用 |
|---|---|
| `--scope user\|project` | 默认 `user`；项目级需显式指定 |
| `--tool <key>` | 只装指定工具，可多次；显式指定视为检测到 |
| `--home` / `--project` / `--workbench` | 覆盖路径（测试用，不碰真实主目录） |
| `--mode auto\|symlink\|copy` | 默认 `auto`，优先相对软链、失败回退复制 |
| `--no-entries` | 不注册三个公开入口命令（**默认注册**） |
| `--dry-run` | 只报告不落盘 |

**期望集合** = 工作台 `skills/` 下所有含 `SKILL.md` 的工种技能
**+ 三个公开入口命令**（`apply` / `install` / `update`）。
入口一起注册，是为了换到任何项目都能调用「全局初始化」这条命令。

对账是**声明式、幂等**的：

| 现状 | 动作 |
|---|---|
| 在集合内且软链指向正确 | 保留 |
| 在集合内但过期 / 类型不一致 | 删除后重建 |
| 在集合内、工具目录里没有 | 新建 |
| 本包拥有但已不在集合 | 删除（清孤儿） |
| **不是本包拥有**（用户自己的技能） | **绝不碰**；同名冲突也跳过并告警 |

清单 `.design-managed.json` 记录 `scope`、`workbench`、`managed` 和**按技能记录真实 mode**
（修掉旧版幂等时把 `copy` 误记成 `symlink` 的问题）。

### Step 3: 输出安装摘要

```text
╔════════════════════════════════════════════════════╗
║   ✅ 设计技能已注册到 2 个 AI 工具（用户全局）      ║
╠════════════════════════════════════════════════════╣
║  WorkBuddy  ~/.workbuddy/skills   24 个 ✅ 软链      ║
║  Codex      ~/.agents/skills      24 个 ✅ 软链      ║
║  未检测到、未创建：Cursor / Qoder / Reasonix …       ║
║  工作台：~/.design/   作品：<当前项目>/.design/artifacts/ ║
╚════════════════════════════════════════════════════╝
重启会话或重载窗口后，/ui-design 等命令即可使用。
```

> 工作台不存在时脚本会明确报错，提示先跑 `/apply-design-skills`。

---

## 与 `shuhe-role-skills` 共存

两个包工作台不同（本包 `~/.design/`，角色包用项目内目录），
清单文件也不同（`.design-managed.json` vs `.roles-managed.json`），
**互不覆盖、互不清理对方的注册项**，可在同一环境同时安装。

## 约束

- ❌ 不修改工作台 `~/.design/skills/` 内容（只软链或复制，不移动）
- ❌ 不向未检测到的工具目录写任何东西、不创建无关目录
- ❌ 不碰用户自己的技能、不写工具根目录、不写旧版目录
- ✅ 三个公开入口命令默认一并注册
- ✅ 对账式：多退少补，不残留孤儿、不留断链
- ✅ 优先相对软链，回退复制，并记录真实模式

---

> **作者：zhenghx**
