---
name: install-design-skills
description: 当目标项目已生成 .design/skills 且需要把工种技能注册到 AI 工具时使用：扫描项目内所有已存在的 AI 工具目录，只向检测到的目录建软链并做声明式对账。当用户说「安装设计技能/技能没生效/换个工具也要能用」时使用。
---

# Install Design Skills — 扫描并注册到所有在用的 AI 工具

> **本包最关键的改造点**：旧版「按目录特征检测，取第一个匹配」只装一个工具目录，
> 用户多 AI 工具并用时其余工具读不到命令。本版**扫描到的全装**。

---

## 为什么需要这个命令

`/apply-design-skills` 只把技能写进 `.design/skills/`，各 AI 工具**不会自动扫描** `.design/` 来注册斜杠命令。
分工：`.design/` 是项目可提交、可评审的资产；工具目录是本地生成物，随时可重新注册。

## 工作流程

### Step 1: 扫描项目内的 AI 工具目录（不是选第一个）

**按 marker 目录是否存在**判断这个工具在本项目里是否被使用，检测特征与技能目录成对：

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

**规则（硬约束）**：

- ✅ **检测到的每一个目录都装**，各自做对账、各自建软链；
- ❌ **未检测到的目录一律不写、不擅自创建**——这正是「只安装对应目录」的含义；
- 一个都没检测到 → 明确报错并提示用 `--tool-dir` 指定，或先初始化对应工具；**不默认挑一个创建**；
- 只写**当前项目内**的目录；目标路径解析后若位于用户主目录，立即停止。

### Step 2: 一律调用对账脚本，不要手拍

```bash
python3 <本技能目录>/scripts/reconcile-skills.py \
  --project <目标项目根目录> --scan
```

可选参数：`--mode auto|symlink|copy`（默认 `auto`，优先软链、失败回退复制）、`--dry-run`（预演）、
`--tool-dir <目录>`（显式补充，可多次）。

脚本对每个检测到的目录做**声明式对账**（幂等、可重复执行）：

| # | 做什么 |
|---|---|
| 1 | 期望集合 = `.design/skills/` 下所有含 `SKILL.md` 的技能（名字取 frontmatter `name`） |
| 2 | 识别「本技能拥有」的项：`.design-managed.json` 记录的 + 指向本项目 `.design/skills` 的软链（**含断链**） |
| 3 | **多退少补**：缺的装上、过期/不一致的重建、不再属于期望集合的删除（清孤儿） |
| 4 | 落 `.design-managed.json`，**按技能记录真实安装模式**（修掉旧版幂等时把 copy 误记成 symlink 的问题） |

| 现状 | 期望 | 动作 |
|---|---|---|
| 存在且指向正确源 | 在集合内 | 保留 |
| 存在但源过期 / 内容不一致 | 在集合内 | 删除后重建 |
| 不存在 | 在集合内 | 新建 |
| 存在（本技能拥有） | 不在集合内 | 删除 |
| 存在但**不是**本技能拥有 | — | **绝不碰**（用户自己的技能） |

> 软链模式下**不改动** `.design/skills/` 任何文件。技能目录只含 `SKILL.md` + `agents/`
> （以及自带的 `scripts/`）；`rules/` `templates/` `references/` 是包级资产，留在 `.design/`，
> 技能通过 `.design/...` 相对路径读取——工具目录里没有它们**是正常的**。

### Step 3: 输出安装摘要

```text
╔══════════════════════════════════════════════════╗
║   ✅ 设计技能已注册到 3 个 AI 工具                ║
╠══════════════════════════════════════════════════╣
║  Claude Code  .claude/skills/    21 个 ✅ 软链     ║
║  Cursor       .cursor/skills/    21 个 ✅ 软链     ║
║  Codex        .codex/skills/     21 个 ✅ 软链     ║
║  未检测到、已跳过：.agents/ .openclaw/ …           ║
╚══════════════════════════════════════════════════╝
日常一个命令即可：/ui-design 帮我做登录页
```

> 工具未即时刷新时，重启会话或重新加载即可。

---

## 与 `shuhe-role-skills` 共存

两个包产物目录不同（`.design/` vs `.roles/`），清单文件也不同
（`.design-managed.json` vs `.roles-managed.json`），**互不覆盖、互不清理对方的项**，可在同一项目同时安装。

## 约束

- ❌ 不修改 `.design/skills/` 内容（只软链或复制，不移动）
- ❌ 不把本命令自身当作要安装的技能
- ❌ 不写用户全局目录、不向未检测到的工具目录写任何东西
- ✅ `.design/skills/` 不存在时提示先运行 `/apply-design-skills`
- ✅ 对账式：多退少补，不残留孤儿、不留断链
- ✅ 优先软链，回退复制，并记录真实模式

---

> **作者：zhenghx**
