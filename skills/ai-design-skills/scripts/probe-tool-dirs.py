#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe-tool-dirs.py — 安装前先「查看」各 AI 工具的全局 / 项目技能目录规则。

用法:
    python3 probe-tool-dirs.py                          # 默认用户全局
    python3 probe-tool-dirs.py --scope project         # 项目级
    python3 probe-tool-dirs.py --tool workbuddy --tool codex --json
    HOME=/tmp/fake-home python3 probe-tool-dirs.py    # 用临时 HOME 真跑验证，不碰真实全局目录
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tool_dirs import artifacts_dir, load_rules, probe, render_table, workbench


def main() -> int:
    ap = argparse.ArgumentParser(description="探测 AI 工具真实的技能安装目录")
    ap.add_argument("--scope", choices=["user", "project"], default=None,
                    help="默认取 tool-dirs.json 的 default_scope（user）")
    ap.add_argument("--home", default=None, help="覆盖用户主目录（测试用）")
    ap.add_argument("--project", default=None, help="覆盖项目根目录（默认 cwd）")
    ap.add_argument("--tool", action="append", default=[],
                    help="只探测指定工具 key，可多次；显式指定视为检测到")
    ap.add_argument("--json", action="store_true", help="输出 JSON 供脚本消费")
    args = ap.parse_args()

    rules = load_rules()
    scope = args.scope or rules["default_scope"]
    home = Path(args.home).resolve() if args.home else Path.home().resolve()
    project = Path(args.project).resolve() if args.project else Path.cwd().resolve()

    try:
        rows = probe(scope, home, project, only=set(args.tool) or None)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    wb = workbench(scope, home, project)
    if args.json:
        print(json.dumps({
            "scope": scope,
            "home": str(home),
            "project": str(project),
            "workbench": str(wb),
            "artifacts": str(artifacts_dir(project)),
            "tools": [{**r, "skills_dir": str(r["skills_dir"])} for r in rows],
        }, ensure_ascii=False, indent=2))
    else:
        print(render_table(rows, home))
        print(f"\n  共享工作台: {wb}")
        print(f"  用户作品:   {artifacts_dir(project)}（始终按当前项目落盘）")
        picked = [r["name"] for r in rows if r["will_write"]]
        print(f"  本次目标:   {'、'.join(picked) if picked else '无（未检测到任何工具，不会创建目录）'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
