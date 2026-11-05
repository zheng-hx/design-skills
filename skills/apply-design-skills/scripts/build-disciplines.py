#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build-disciplines.py — 从 disciplines.json 生成工种技能模板与索引。

注册表是单一事实源：改工种只改 JSON，然后跑本脚本重生成，不要手改模板。

生成物（都入库，运行时不需要 Python）：
    capabilities/design-disciplines/skills/<core-key>/SKILL.md.tpl
    capabilities/design-disciplines/skills/<core-key>/agents/openai.yaml.tpl
    capabilities/design-disciplines/references/工种索引.md
    capabilities/design-disciplines/references/开源资料索引.md

用法:
    python3 build-disciplines.py            # 生成
    python3 build-disciplines.py --check    # 只校验（CI 用）：生成物与注册表一致则 0，否则 1
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
REGISTRY = SKILL_DIR / "capabilities" / "design-core" / "disciplines.json"
DISC = SKILL_DIR / "capabilities" / "design-disciplines"


def load():
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def validate(data) -> list[str]:
    """注册表自检。返回错误列表。"""
    errs = []
    ds = data["disciplines"]
    keys = [d["key"] for d in ds]
    for k, c in collections.Counter(keys).items():
        if c > 1:
            errs.append(f"工种 key 重复: {k} ({c} 次)")

    trig_owner = {}
    for d in ds:
        for t in d["triggers"]:
            if t in trig_owner:
                errs.append(f"触发词冲突: 「{t}」同时属于 {trig_owner[t]} 与 {d['key']}")
            trig_owner[t] = d["key"]

    for d in ds:
        if d["tier"] not in ("core", "extended"):
            errs.append(f"{d['key']}: tier 非法 {d['tier']}")
        if d["domain"] not in data["domains"]:
            errs.append(f"{d['key']}: domain 未登记 {d['domain']}")
        if d["tier"] == "core":
            for f in ("summary", "pipeline", "artifacts", "references", "sources", "triggers"):
                if not d.get(f):
                    errs.append(f"{d['key']}: core 缺字段 {f}")
            for r in d["references"]:
                if r not in data["shared_references"]:
                    errs.append(f"{d['key']}: 引用未登记的 reference {r}")
    return errs


def skill_md(d, data) -> str:
    others = [x["name"] for x in data["disciplines"]
              if x["tier"] == "core" and x["domain"] == d["domain"] and x["key"] != d["key"]][:3]
    not_for = "、".join(others) if others else "其他工种"
    triggers = " / ".join(d["triggers"])

    stages = "\n".join(
        f"| {i} | **{s}** | 上一阶段产物 `confirmed` | 本阶段结论有来源、无 `[缺失·阻塞]` | "
        f"`{i:02d}-` 产物 |"
        for i, s in enumerate(d["pipeline"], 1)
    )
    artifacts = "\n".join(f"| {i} | {a} | `draft` |" for i, a in enumerate(d["artifacts"], 1))
    ref_rows = "\n".join(
        f"| 涉及「{r[:-3]}」时 | `{{{{DESIGN_ROOT}}}}/references/{r}` |"
        for r in d["references"]
    )
    sources = "\n".join(f"- {s}" for s in d["sources"])

    return f"""---
name: {d['key']}
description: {d['name']}：{d['summary']} 当用户说「{triggers}」时使用。不用于 {not_for}；跨工种任务交给 /design-router 分流。
---

# {d['name']}（{d['en']}）

> 工种域：**{d['domain']}**　·　分层：`core`（独立技能）　·　技能包版本 {{{{PACKAGE_VERSION}}}}

## 定位与边界

**{d['summary']}**

- **不负责**：{not_for} 等相邻工种——遇到时明确告诉用户该用哪个技能，不要硬接。
- **跨工种**：一个需求同时涉及多个工种时，用 `/design-router` 分流，各自出产物，不合并成一份四不像的稿。
- **长尾工种**（室内 / 建筑 / 服装 / 珠宝等）没有独立技能，用 `/design-any` 走通用流水线，见 `工种索引.md`。

## 前置：本技能自包含

渲染后的 `.design/` 里，本技能读得到：

- `.design/rules/交互模式.md`（一次一问·决策树·对话内展示）
- `.design/rules/状态机与收口.md`（六态状态机、收口与门禁）
- `.design/rules/产物与来源规范.md`（frontmatter / dossier / 来源标记）
- `.design/rules/设计通用规范.md`（所有设计工种共用的红线）
- `.design/references/` 下按路由表**按需加载**，不要一次全读

> `rules/` 与 `references/` 是**工种包级**的，位于 `.design/` 下，不随技能复制进工具目录；
> 工具目录里只有 `SKILL.md` 与 `agents/`，这是正常的。

## 第 0 阶段：先确认现状（硬门禁）

**{d['pipeline'][0]}**。

一次只问**一个**最该问的问题，回答决定下一个问题；安全默认值不占提问额度，收口时一次性列出供否决。
拿不到现状就停，**不许 best-guess 视觉方向、品牌、对外承诺与业务规则**。

## 流水线（{len(d['pipeline'])} 步）

| # | 阶段 | 输入 | 出口门禁 | 产物 |
|---|---|---|---|---|
{stages}

- 线性主干：**上一阶段 `confirmed` 才进下一阶段**；门禁不过就退回或请示，不跳步。
- 收敛时在**对话内**出结论卡片 → 落盘 `.design/artifacts/<feature>/00-summary.md`（`status: analyzing`）→ 请用户确认；**确认后才改 `producing` 进入生产**。
- 关键内容（结构、状态、视觉语言、组件规格）必须出现在对话里，不能只给文件路径。

## 产物与状态

| # | 产物 | 起始 status |
|---|---|---|
{artifacts}

每个产物 frontmatter 带 `status`：`draft → proposed → reviewing → confirmed → delivered`，支持断点续传。
`00-summary.md` 是驱动卡：`draft → analyzing → producing → reviewing → confirmed → delivered`。

## 门禁红线（违反即停）

1. **未确认不生产**：用户没拍板，不得开始出稿、不得写「已生成完成」。
2. **不编造**：审批人、数据、金额、期限、用户量、调研结论一律标 `[缺失·阻塞]`，不写成事实。
3. **来源要落盘**：用户口述 / 粘贴 / 截图都是来源，按《产物与来源规范》§6 原样存 `sources/`，记出处与日期。
4. **授权要核验**：字体、图片、图库素材、参考稿的授权状态必须核对；拿不到就标待授权，不得默认可用。
5. **AI 生成物要排查**：用宿主原生生成能力或外部模型出图时，逐项过 `AI生成设计缺陷清单.md`。
6. **可访问性是底线**：涉及界面时按 `可访问性细则.md` 逐条核验，不以「看起来还行」代替实测值。
7. **不越界交付**：本工种给不出的实体产物（打样、施工图、可印制文件）如实说明，不假装已交付。

## 参考文件路由表

| 什么时候 | 读哪个 |
|---|---|
{ref_rows}
| 用户提到的工种不在 core 列表 | `.design/references/工种索引.md` |
| 长尾工种要走通用流水线 | `.design/references/工种通用流水线.md` |
| 用开源资料前确认许可边界 | `.design/references/许可与来源规范.md` |

## 交付前四步

**AI 自检 → 独立评审 → 用户审核 → 回退重跑**（见 `状态机与收口.md` §11）。
独立评审派**只读**子智能体分 Spec / Standards 两轴，不合并不排序；宿主无子智能体原语时**必须标注「降级模式」**；主会话自审不算独立评审。

---

> **登记来源**（借鉴方法论与结构，许可边界见 `许可与来源规范.md`）：
{sources}
>
> 工种 key：`{d['key']}`　·　由 `build-disciplines.py` 从 `disciplines.json` 生成，请勿手改。
"""


def openai_yaml(d) -> str:
    triggers = " / ".join(d["triggers"])
    desc = (
        f"{d['name']}：{d['summary']} 当用户说「{triggers}」时使用。"
    )
    return (
        'interface:\n'
        f'  display_name: "{d["name"]}"\n'
        f'  short_description: "{desc}"\n'
        'policy:\n'
        '  allow_implicit_invocation: true\n'
    )


def discipline_index(data) -> str:
    lines = [
        "# 工种索引（全行业）",
        "",
        "> 本文件由 `build-disciplines.py` 从 `disciplines.json` 生成，请勿手改。",
        f"> 共 **{len(data['disciplines'])}** 个工种：`core` "
        f"{sum(1 for x in data['disciplines'] if x['tier']=='core')} 个做独立技能，"
        f"`extended` {sum(1 for x in data['disciplines'] if x['tier']=='extended')} 个由 `/design-any` 兜底。",
        "",
        "## 分层口径",
        "",
        "| 层 | 含义 | 怎么调用 |",
        "|---|---|---|",
        "| `core` | 高频、AI 能给出可验收产物的工种 | 直接 `/<工种 key>` |",
        "| `extended` | 长尾，或强依赖 CAD / 打样 / 材料 / 资质的线下工种 | `/design-any <工种名> <需求>`，按通用流水线走 |",
        "",
        "> **为什么不都做成技能**：30+ 斜杠命令会让触发词互相抢；室内、服装、建筑这类工种"
        " AI 给不出可施工 / 可打样的交付物，做成完整技能等于假交付。"
        " 索引登记 + 通用兜底既能覆盖，又不撒谎。",
        "",
    ]
    for domain in data["domains"]:
        rows = [x for x in data["disciplines"] if x["domain"] == domain]
        lines += [f"## {domain}（{len(rows)}）", "",
                  "| 工种 | key | 层 | 触发词 | 职责 |", "|---|---|---|---|---|"]
        for x in rows:
            lines.append(
                f"| {x['name']} | `{x['key']}` | `{x['tier']}` | "
                f"{' / '.join(x['triggers'])} | {x['summary']} |"
            )
        lines.append("")
    lines += [
        "## 找不到对应工种时",
        "",
        "1. 先按 `domain` 找最接近的 core 工种，用它的流水线；",
        "2. 都不贴切 → `/design-any`，并在产物里注明「按通用流水线处理，非专属工种」；",
        "3. 跨多个工种 → `/design-router` 拆分，各自出产物；",
        "4. **不要**为了覆盖而硬套一个不相关的工种模板。",
        "",
    ]
    return "\n".join(lines)


def source_index(data) -> str:
    repos = collections.defaultdict(list)
    for x in data["disciplines"]:
        for s in x["sources"]:
            repos[s].append(x["name"])
    lines = [
        "# 开源资料索引",
        "",
        "> 由 `build-disciplines.py` 从 `disciplines.json` 的 `sources` 聚合生成，请勿手改。",
        "> **许可红线**：MIT / Apache-2.0 可借鉴具体表达与结构；标注「待核实」或无 LICENSE 的"
        "只借鉴方法论，不搬文字与模板。详情见 `许可与来源规范.md`。",
        "",
        "| 项目 / 许可 | 借鉴它的工种 |",
        "|---|---|",
    ]
    for repo in sorted(repos):
        names = "、".join(sorted(set(repos[repo])))
        lines.append(f"| {repo} | {names} |")
    lines += [
        "",
        "## 接入规则",
        "",
        "1. 新增参考资料必须登记进 `disciplines.json` 的 `shared_references`，否则渲染校验判为死文件。",
        "2. 只搬「可检索的规则 / 结构 / 检查表」，不整包塞进技能目录——工种包是自包含的，"
        "整包塞会串引用、破校验。",
        "3. 外部规则与本包门禁冲突时，以 `.design/rules/设计通用规范.md` 为准。",
        "",
    ]
    return "\n".join(lines)


def build(data, check: bool) -> int:
    errs = validate(data)
    if errs:
        for e in errs:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1

    wanted = {}
    for d in data["disciplines"]:
        if d["tier"] == "core":
            base = DISC / "skills" / d["key"]
            wanted[base / "SKILL.md.tpl"] = skill_md(d, data)
            wanted[base / "agents" / "openai.yaml.tpl"] = openai_yaml(d)
    wanted[DISC / "references" / "工种索引.md"] = discipline_index(data)
    wanted[DISC / "references" / "开源资料索引.md"] = source_index(data)

    if check:
        diff = []
        for p, content in wanted.items():
            if not p.is_file():
                diff.append(f"缺失 {p.relative_to(SKILL_DIR)}")
            elif p.read_text(encoding="utf-8") != content:
                diff.append(f"与注册表不一致（请重跑生成）{p.relative_to(SKILL_DIR)}")
        # 注册表里已删掉的工种不应残留技能目录
        core_keys = {d["key"] for d in data["disciplines"] if d["tier"] == "core"}
        for p in (DISC / "skills").iterdir() if (DISC / "skills").is_dir() else []:
            if p.is_dir() and p.name not in core_keys and p.name not in ("design-router", "design-any"):
                diff.append(f"残留未登记技能目录 {p.name}")
        if diff:
            for x in diff:
                print(f"ERROR: {x}", file=sys.stderr)
            return 1
        print(f"生成物与注册表一致（{len(wanted)} 个文件）")
        return 0

    for p, content in wanted.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    print(f"已生成/刷新 {len(wanted)} 个文件："
          f"{sum(1 for d in data['disciplines'] if d['tier']=='core')} 个 core 技能 + 2 份索引")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="从工种注册表生成技能模板与索引")
    ap.add_argument("--check", action="store_true", help="只校验，不写文件")
    args = ap.parse_args()
    return build(load(), args.check)


if __name__ == "__main__":
    sys.exit(main())
