#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-triggers.py — 触发词纪律校验。

抓三类问题：
  1. 注册表里两个工种用了完全相同的触发词（会互相抢触发）；
  2. core 技能的 description 没带自己的触发词（用户很可能命中不了它）；
  3. 技能 description / agents short_description 缺「触发式」写法，或 skills 与注册表脱节。

用法: python3 scripts/check-triggers.py
"""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "skills" / "ai-design-skills" / "capabilities" / "design-core" / "disciplines.json"
SKILLS = ROOT / "skills" / "ai-design-skills" / "capabilities" / "design-disciplines" / "skills"
ENTRIES = ("design-router", "design-any")


def frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return ""
    end = text.find("\n---\n", 4)
    return text[4:end if end > 0 else len(text)]


def desc(text: str) -> str:
    m = re.search(r"^description:\s*(.+)$", frontmatter(text), re.M)
    return m.group(1).strip() if m else ""


def main() -> int:
    errs: list[str] = []
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    ds = data["disciplines"]

    # 1. 触发词冲突
    owner: dict[str, str] = {}
    for d in ds:
        for t in d["triggers"]:
            if t in owner:
                errs.append(f"触发词冲突：「{t}」同时属于 {owner[t]} 与 {d['key']}")
            owner[t] = d["key"]

    # 2. key 唯一
    for k, c in collections.Counter(d["key"] for d in ds).items():
        if c > 1:
            errs.append(f"工种 key 重复: {k}")

    core = [d for d in ds if d["tier"] == "core"]
    present = {p.name for p in SKILLS.iterdir() if p.is_dir()} if SKILLS.is_dir() else set()

    # 3. core 技能齐全 + 触发式描述 + 触发词可命中
    for d in core:
        key = d["key"]
        if key not in present:
            errs.append(f"core 工种缺技能目录: {key}")
            continue
        f = SKILLS / key / "SKILL.template.md"
        if not f.is_file():
            errs.append(f"{key}: 缺 SKILL.template.md")
            continue
        text = f.read_text(encoding="utf-8")
        fm = frontmatter(text)
        name = re.search(r"^name:\s*(\S+)", fm, re.M)
        if not name or name.group(1) != key:
            errs.append(f"{key}: frontmatter name 与目录名不一致")
        dsc = desc(text)
        if "当用户说「" not in dsc or "时使用" not in dsc:
            errs.append(f"{key}: description 不是触发式写法（缺「当用户说…时使用」）")
        hit = [t for t in d["triggers"] if t in dsc]
        if not hit:
            errs.append(f"{key}: description 未包含任何本工种触发词")

        y = SKILLS / key / "agents" / "openai.template.yaml"
        if not y.is_file():
            errs.append(f"{key}: 缺 agents/openai.template.yaml")
        else:
            yt = y.read_text(encoding="utf-8")
            sm = re.search(r"short_description:\s*\"([^\"]+)\"", yt)
            if not sm:
                errs.append(f"{key}: openai.yaml 缺 short_description")
            elif "当用户说" not in sm.group(1):
                errs.append(f"{key}: short_description 不是触发式写法")

    # 4. 入口技能也要触发式
    for e in ENTRIES:
        f = SKILLS / e / "SKILL.template.md"
        if not f.is_file():
            errs.append(f"缺入口技能 {e}")
            continue
        dsc = desc(f.read_text(encoding="utf-8"))
        if "当用户说「" not in dsc:
            errs.append(f"{e}: description 不是触发式写法")

    # 5. 未登记的残留技能
    allowed = {d["key"] for d in core} | set(ENTRIES)
    for extra in sorted(present - allowed):
        errs.append(f"技能目录未登记在注册表: {extra}")

    print(f"工种 {len(ds)}（core {len(core)} / extended {len(ds) - len(core)}）· "
          f"触发词 {len(owner)} 条 · 技能目录 {len(present)} 个")
    if errs:
        for e in errs:
            print(f"ERROR: {e}", file=sys.stderr)
        print(f"触发词校验失败：{len(errs)} 项", file=sys.stderr)
        return 1
    print("✅ 触发词无冲突、描述均为触发式、技能与注册表一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
