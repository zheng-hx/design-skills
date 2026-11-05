# 多 AI 工具安装指南

> 关键词：**扫描到的全装，未检测到的一律不写**。
> 本文对应 `skills/install-design-skills/scripts/reconcile-skills.py` 的实际行为；两者不一致时以脚本为准。

---

## 1. 与旧包的关键差异

参考项目 `shuhe-role-skills` 的 `/install-role-skills` 是「按目录特征检测，**取第一个匹配**」。
一个人同时用 Claude Code + Cursor + Codex 时，只有第一个工具目录装上了命令，其余工具读不到。

本包改为：

```text
扫描项目内所有已存在的 AI 工具目录
  → 检测到的每一个都做一次声明式对账、都建软链
  → 未检测到的目录一律不写、不擅自创建
```

第二个修正是**幂等模式不误报**：旧版在无任何安装动作时把清单里的 `mode` 统一写成 `symlink`，
实际可能是 `copy`。本版按技能逐个记录真实模式，重复执行结果恒定。

---

## 2. 扫描路径表

判据是 **marker 目录存在**，不是「这个工具是否装在本机」。只认项目内的目录，不写用户全局目录。

| # | 工具 | 检测特征（marker） | 技能目录 |
|---|---|---|---|
| 1 | Claude Code / Cline | `.claude/` | `.claude/skills` |
| 2 | Codex | `.codex/` | `.codex/skills` |
| 3 | 通用 Agent Skills | `.agents/` | `.agents/skills` |
| 4 | Cursor | `.cursor/` | `.cursor/skills` |
| 5 | OpenClaw | `.openclaw/` | `.openclaw/skills` |
| 6 | CodeBuddy | `.codebuddy/` | `.codebuddy/skills` |
| 7 | Qoder | `.qoder/` | `.qoder/skills` |
| 8 | Reasonix | `.reasonix/` | `.reasonix/skills` |

> 表里 8 个目录与脚本里的 `TOOL_DIRS` 一一对应；`npm run audit` 会校验「脚本支持的目录是否都在本文列出」，
> 加新工具时**两边都要改**。

用法上是 marker 决定、技能目录落盘：marker 存在即认为该工具在此项目被使用，
在对应技能目录下建软链；marker 不存在则整个跳过，连空目录都不创建。

---

## 3. 安装命令

在**目标项目根目录**执行（通常不需要手敲，`/install-design-skills` 会代劳）：

```bash
python3 <install-design-skills 技能目录>/scripts/reconcile-skills.py \
  --project . --scan
```

| 参数 | 作用 |
|---|---|
| `--project` | 目标项目根目录，必填 |
| `--scan` | 扫描上表所有 marker，**检测到的全装** |
| `--tool-dir <路径>` | 显式指定技能目录，可多次；与 `--scan` 可并用 |
| `--mode auto\|symlink\|copy` | 默认 `auto`：优先软链，不支持时自动回退 `copy` |
| `--dry-run` | 只报告不落盘，用来先看会动哪些文件 |

显式指定（不依赖扫描）：

```bash
python3 reconcile-skills.py --project . \
  --tool-dir .claude/skills --tool-dir .cursor/skills
```

**一个工具目录都没检测到时脚本会报错并退出**，不会自作主张创建 `.claude/` 之类的目录。
要么先初始化对应工具，要么用 `--tool-dir` 明确指定。

---

## 4. 声明式对账规则

对每一个被检测到的工具目录，独立算一次：

```text
期望集合   = <project>/.design/skills/ 下所有含 SKILL.md 的技能（名字取 frontmatter name）
本包拥有   = .design-managed.json 记录的 + 指向本项目 .design/skills 的软链（含断链）
```

| 情况 | 动作 |
|---|---|
| 在期望集合内且类型 / 目标正确 | 保留，不计入变更 |
| 在期望集合内但过期或类型不一致 | 删除后重建 |
| 在期望集合内、工具目录里没有 | 新建软链 |
| 本包拥有但已不在期望集合 | 删除（清孤儿） |
| 不是本包拥有（用户自己的技能） | **绝不碰** |

要点：

- **软链目标用相对路径** `os.path.relpath(...)`，项目整体移动 / 换机器后仍可用；
- 软链创建失败（Windows 无开发者模式、部分文件系统）自动回退 `copy`；`--mode symlink` 则会明确报错，不静默降级；
- `copy` 模式用目录内容哈希判断是否过期，内容没变就不重建；
- 每个工具目录各写一份 `.design-managed.json`，互不干扰。

清单结构：

```json
{
  "package": "ai-design-skills",
  "managed": ["design-router", "design-any", "ui-design"],
  "modes": {"design-router": "symlink", "ui-design": "copy"}
}
```

`modes` 按技能记录真实类型——这条是幂等复跑时不会把 `copy` 误报成 `symlink` 的关键。

---

## 5. 幂等与验收

重复执行 `--scan`，输出应当是 `新增 0 / 更新 0 / 移除 0`，且清单内容不变。

```bash
# 先看会动什么
python3 reconcile-skills.py --project . --scan --dry-run

# 真跑
python3 reconcile-skills.py --project . --scan

# 幂等复跑
python3 reconcile-skills.py --project . --scan
```

手工验收三条：

1. 每个检测到的工具目录下，技能名与 `.design/skills/` 一一对应，没有孤儿、没有断链；
2. 未检测到的目录仍然不存在（没有被「顺手」创建）；
3. 工具目录里你自己放的技能还在。

`npm run check-install` 是**真跑**的端到端回归：临时建项目 → 渲染 → 扫描安装 → 30 项断言，
覆盖多工具软链、未检测目录不创建、幂等、清孤儿、用户技能共存、旧包清单共存、
`copy` 模式不误报、升级后 `artifacts/` 保留。

---

## 6. 与角色技能包共存

| | 角色技能包 | 本包 |
|---|---|---|
| 产物目录 | 另一套独立目录 | `.design/` |
| 注册清单 | 另一份清单 | `.design-managed.json` |
| 入口 | `/install-role-skills` | `/install-design-skills` |

两者**互不依赖、互不覆盖、互不清理对方的注册项**，可在同一项目同时安装。
本包对账时只认自己的清单和指向 `.design/skills/` 的软链，别的一概不动。

---

## 7. 版本升级时的注册

`/update-design-skills` 的三层顺序固定：

| 层 | 内容 | 方式 |
|---|---|---|
| ① 入口技能包 | 三个公开入口 | `npx skills add`（`update` 补不上新增技能） |
| ② 项目工种包 | `.design/` 管理区 | 替换式重渲染，`artifacts/` **绝不覆盖** |
| ③ 工具注册 | 所有检测到的工具目录 | `--scan` 对账，多退少补 |

工种集合改了（比如从 19 个 core 缩到 2 个子集）后，第 ③ 层会自动清掉多出来的孤儿；
新增工种会自动补上。仓库地址优先读 `skills-lock.json`，其次环境变量 `AI_DESIGN_SKILLS_REPO`，
**都没有就明确报错，不编地址**。

---

## 8. 故障排查

| 现象 | 原因 / 处理 |
|---|---|
| 报「未找到 .design/skills/」 | 还没跑 `/apply-design-skills`，先生成再注册 |
| 报「项目内没有检测到任何 AI 工具目录」 | 项目里没有对应 marker 目录；先初始化工具，或用 `--tool-dir` 指定 |
| 命令在新工具里不出现 | 该工具的 marker 目录是后来才建的；重跑一次 `--scan` 即可 |
| 软链变成实体目录 | 文件系统不支持软链，脚本回退了 `copy`；查清单 `modes` 确认 |
| 改了工种，旧命令还在 | 只重渲染没重跑安装；补一次 `--scan` 清孤儿 |
| 用户自己写的技能被删了 | 不应发生。请提交 issue 并附上 `.design-managed.json` 与目录结构 |
| Windows 上软链创建失败 | 开开发者模式，或显式 `--mode copy` |

---

> **作者：zhenghx**
