#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit-repo.py — 仓库卫生校验（文档链接、目录树自洽、无残留）。

用法: python3 scripts/audit-repo.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_DIRS = ROOT / "skills" / "install-design-skills" / "tool-dirs.json"
DOC_TOOL = ROOT / "docs" / "install-by-tool.md"

REQUIRED_FILES = (
    "README.md", "CHANGELOG.md", "LICENSE", "package.json",
    ".gitignore", ".npmignore", ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    "skills/apply-design-skills/VERSION",
    "skills/apply-design-skills/SKILL.md",
    "skills/install-design-skills/SKILL.md",
    "skills/update-design-skills/SKILL.md",
)

LINK_RE = re.compile(r"\[[^\]]+\]\(([^)#]+\.md)(?:#[^)]*)?\)")


def main() -> int:
    errs: list[str] = []

    for rel in REQUIRED_FILES:
        if not (ROOT / rel).is_file():
            errs.append(f"缺必需文件: {rel}")

    # 文档里的 .md 相对链接可达
    md_files = [ROOT / "README.md"] + sorted((ROOT / "docs").glob("*.md"))
    for f in md_files:
        if not f.is_file():
            continue
        for link in LINK_RE.findall(f.read_text(encoding="utf-8")):
            if link.startswith("http"):
                continue
            target = (f.parent / link).resolve()
            if not target.is_file():
                errs.append(f"{f.relative_to(ROOT)}: 链接不可达 -> {link}")

    # .gitignore 关键项
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for key in (".design/", "__pycache__/"):
        if key not in gi:
            errs.append(f".gitignore 缺关键项: {key}")

    # 工具目录表与文档一致：tool-dirs.json（单一事实源）里每个技能目录都要在
    # docs/install-by-tool.md 出现；同时文档必须显式点名旧版遗留目录 ~/.codex/skills 不可写。
    if TOOL_DIRS.is_file() and DOC_TOOL.is_file():
        rules = json.loads(TOOL_DIRS.read_text(encoding="utf-8"))
        doc = DOC_TOOL.read_text(encoding="utf-8")
        seen: set[str] = set()
        for tool in rules["tools"]:
            for spec in (tool.get("user_skills", ""), tool.get("project_skills", "")):
                if spec and spec not in seen:
                    seen.add(spec)
                    if spec not in doc:
                        errs.append(f"docs/install-by-tool.md 未列出工具目录规则: {spec}")
        for legacy in rules.get("not_skill_dirs", {}):
            if legacy not in doc:
                errs.append(f"docs/install-by-tool.md 未说明不可写目录: {legacy}")
    else:
        errs.append("缺 tool-dirs.json 或 docs/install-by-tool.md")

    # 残留物：只查「不该出现在技能源仓库里的渲染产物」。
    # Python 运行缓存（__pycache__ / *.pyc）已被 .gitignore 和 .npmignore 排除，
    # 是跑校验时自然产生的副产物，不该让 check:all 因此变红。
    if (ROOT / ".design").exists():
        errs.append("技能源仓库里出现 .design/（渲染只应发生在目标项目）")
    for p in ROOT.glob(".design-build-*"):
        errs.append(f"存在渲染暂存残留: {p.name}")
    if (ROOT / ".design.bak").exists():
        errs.append("存在 .design.bak 残留")

    if errs:
        for e in errs:
            print(f"ERROR: {e}", file=sys.stderr)
        print(f"仓库卫生校验失败：{len(errs)} 项", file=sys.stderr)
        return 1
    print(f"✅ 仓库卫生通过：{len(md_files)} 份文档链接全可达 / 工具表自洽 / 无残留")
    return 0


if __name__ == "__main__":
    sys.exit(main())
