#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sync-version.py — 版本号单一事实源同步。

事实源：package.json 的 version。
同步到：.claude-plugin/plugin.json 的 version、skills/ai-design-skills/version.json、
skills/ai-design-skills/SKILL.md frontmatter 的 version（SkillHub 发布要求）。

为什么需要 version.json：`npx skills add` **只拷贝技能目录**，
仓库根的 package.json 带不过去——运行时版本戳必须住在技能目录里。
（不用无扩展名的 VERSION：SkillHub 发布 API 拒收无扩展名文件。）

用法:
    python3 scripts/sync-version.py            # 同步
    python3 scripts/sync-version.py --check    # 只检查（CI 用），不一致退出码 1
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "package.json"
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
VERSION = ROOT / "skills" / "ai-design-skills" / "version.json"
SKILL_MD = ROOT / "skills" / "ai-design-skills" / "SKILL.md"


def main() -> int:
    check_only = "--check" in sys.argv
    pkg = json.loads(PKG.read_text(encoding="utf-8"))
    version = pkg.get("version")
    if not version:
        print("ERROR: package.json 缺少 version", file=sys.stderr)
        return 1

    plugin = json.loads(PLUGIN.read_text(encoding="utf-8"))
    runtime = ""
    if VERSION.is_file():
        try:
            runtime = json.loads(VERSION.read_text(encoding="utf-8"))["version"]
        except (ValueError, KeyError):
            runtime = VERSION.read_text(encoding="utf-8").strip()  # 兼容旧版裸文本

    skill_text = SKILL_MD.read_text(encoding="utf-8")
    m = re.search(r"^version:\s*(\S+)\s*$", skill_text, flags=re.MULTILINE)
    skill_version = m.group(1) if m else ""

    if plugin.get("version") == version and runtime == version and skill_version == version:
        print(f"版本已一致：{version}")
        return 0

    if check_only:
        print(
            f"ERROR: 版本不一致 —— package.json={version}, "
            f"plugin.json={plugin.get('version')}, VERSION={runtime or '<缺失>'}, "
            f"SKILL.md={skill_version or '<缺失>'}",
            file=sys.stderr,
        )
        return 1

    plugin["version"] = version
    PLUGIN.write_text(json.dumps(plugin, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    VERSION.write_text(json.dumps({"version": version}, ensure_ascii=False) + "\n", encoding="utf-8")
    if m:
        skill_text = skill_text[:m.start()] + f"version: {version}" + skill_text[m.end():]
    else:
        # frontmatter 缺 version：插到 name 行之后
        skill_text = re.sub(r"(?m)^(name: .*)$", rf"\1\nversion: {version}", skill_text, count=1)
    SKILL_MD.write_text(skill_text, encoding="utf-8")
    print(f"已同步 plugin.json、VERSION 与 SKILL.md 到 {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
