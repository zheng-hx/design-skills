#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tool_dirs.py — AI 工具技能目录规则的单一读取口。

规则在 ../tool-dirs.json；探测（probe）与安装（reconcile-skills.py）共用这里的逻辑，
保证「先查看目录规则 → 再按规则安装」不是两句口号。

设计要点：
  * 默认 scope=user（用户全局），project 为可选；
  * 检测依据是**工具根目录是否存在**，不是「技能目录里有没有东西」；
  * 只写检测到的工具对应目录；未检测到的一律不写、不创建；
  * Codex 的全局目录是 ~/.agents/skills，不是 ~/.codex/skills（官方规则）。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

RULES_FILE = Path(__file__).resolve().parents[1] / "tool-dirs.json"


def load_rules() -> dict:
    return json.loads(RULES_FILE.read_text(encoding="utf-8"))


def expand(spec: str, home: Path, project: Path) -> Path:
    """把 ~/.xxx 或 .xxx 展开成绝对路径。不接受绝对路径规格（防止越界）。"""
    if spec.startswith("~/"):
        return (home / spec[2:]).resolve()
    if spec.startswith("~"):
        raise ValueError(f"不支持的路径规格: {spec}")
    if os.path.isabs(spec):
        raise ValueError(f"规则表不允许写绝对路径: {spec}")
    return (project / spec).resolve()


def detect(tool: dict, scope: str, home: Path, project: Path,
           forced: bool = False) -> tuple[bool, str]:
    """返回 (是否检测到, 依据说明)。scope=user 看用户全局工具根，project 看项目内标记目录。"""
    key = "detect_user" if scope == "user" else "detect_project"
    hits: list[str] = []
    for spec in tool.get(key, []):
        try:
            p = expand(spec, home, project)
        except ValueError:
            continue
        if p.is_dir():
            hits.append(spec)
    for var in tool.get("env", []):
        if os.environ.get(var):
            hits.append(f"${var}")
    if hits:
        return True, "、".join(hits)
    if forced:
        return True, "--tool 显式指定"
    return False, "未检测到工具根目录"


def probe(scope: str, home: Path, project: Path,
          only: set[str] | None = None) -> list[dict]:
    """探测所有工具，返回结构化结果。only 非空时只考虑这些 key，并视为显式指定。"""
    rules = load_rules()
    out: list[dict] = []
    for tool in rules["tools"]:
        key = tool["key"]
        if only and key not in only:
            continue
        forced = bool(only and key in only)
        ok, reason = detect(tool, scope, home, project, forced=forced)
        spec = tool["user_skills"] if scope == "user" else tool["project_skills"]
        skills_dir = expand(spec, home, project)
        out.append({
            "key": key,
            "name": tool["name"],
            "scope": scope,
            "detected": ok,
            "reason": reason,
            "skills_dir": skills_dir,
            "skills_spec": spec,
            "dir_exists": skills_dir.is_dir(),
            "will_write": ok,
            "standard": tool.get("standard", ""),
            "note": tool.get("note", ""),
        })
    if only:
        known = {r["key"] for r in out}
        for k in sorted(set(only) - known):
            raise ValueError(f"未知工具 key: {k}（见 tool-dirs.json）")
    return out


def workbench(scope: str, home: Path, project: Path) -> Path:
    """共享工作台（rules / references / templates / skills 的单一事实源）。"""
    spec = load_rules()["workbench"][scope]
    return expand(spec, home, project)


def artifacts_dir(project: Path) -> Path:
    """用户作品永远按当前工作目录落盘，不进全局工作台。"""
    spec = load_rules()["artifacts"]
    return (project / spec).resolve()


def render_table(rows: list[dict], home: Path | None = None) -> str:
    home = home or Path.home()
    lines = [f"AI 工具技能目录探测（scope={rows[0]['scope'] if rows else '-'}）", ""]
    lines.append(f"  {'工具':<34}{'检测依据':<24}{'技能目录':<34}{'存在':<6}本次")
    lines.append("  " + "-" * 108)
    for r in rows:
        mark = "✅" if r["will_write"] else "⏭ 跳过"
        exist = "✅" if r["dir_exists"] else "—"
        d = str(r["skills_dir"]).replace(str(home), "~")
        lines.append(f"  {r['name']:<34}{r['reason']:<24}{d:<34}{exist:<6}{mark}")
    skipped = [r["name"] for r in rows if not r["will_write"]]
    if skipped:
        lines += ["", f"  未检测到、不会创建任何目录：{'、'.join(skipped)}"]
    lines += ["", "  提示：装到用户全局目录后，部分工具需重启会话 / 重载窗口才生效。"]
    return "\n".join(lines)
