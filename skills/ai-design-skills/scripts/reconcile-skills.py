#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reconcile-skills.py — 按 AI 工具真实目录规则，把共享工作台的技能注册到工具技能目录。

与旧版的三点关键差异：

1. **默认用户全局**（`--scope user`）：设计师技能是人的能力，装一次所有项目能用。
   旧版只写项目内目录、还明确禁止写用户主目录，导致「全局技能没生效」。
2. **按工具真实规则探测**：规则在 ../tool-dirs.json，安装前先 probe 出
   「本机有哪些工具、各自全局/项目级技能目录在哪」，再决定往哪装。
   Codex 的全局目录是 ~/.agents/skills，不是 ~/.codex/skills；WorkBuddy 是 ~/.workbuddy/skills。
3. **只写检测到的目录，未检测到的一律不创建**：只用 WorkBuddy 时绝不出现 ~/.agents/；
   同时用了 Codex 才写 ~/.agents/skills。

对账规则（幂等、声明式）：
    期望集合 = 工作台 skills/ 下所有含 SKILL.md 的工种技能 + 唯一公开入口命令
    本包拥有 = .design-managed.json 记录的 + 指向工作台/入口源的软链（含断链）
    多退少补：在集合内且正确→保留 / 过期→重建 / 缺失→新建 / 不在集合→清孤儿
    不是本包拥有的（用户自己的技能）→ 绝不碰；同名冲突也跳过并告警

用法:
    python3 reconcile-skills.py --scope user                 # 默认：用户全局、自动探测
    python3 reconcile-skills.py --tool workbuddy --tool codex
    python3 reconcile-skills.py --scope project --project <项目根>
    HOME=/tmp/fake-home python3 reconcile-skills.py --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

from tool_dirs import artifacts_dir, load_rules, probe, render_table, workbench

MANIFEST = ".design-managed.json"
ENTRIES = ("ai-design-skills",)
SKILLS_SRC = Path(__file__).resolve().parents[2]  # <技能源>/skills/


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def frontmatter_name(skill_md: Path) -> str | None:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    for line in text[4:end if end > 0 else len(text)].splitlines():
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip()
    return None


def dir_hash(d: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(p for p in d.rglob("*") if p.is_file()):
        h.update(str(f.relative_to(d)).encode())
        h.update(f.read_bytes())
    return h.hexdigest()


def expected(wb: Path, include_entries: bool) -> tuple[dict[str, Path], list[Path]]:
    """返回（技能名→源目录, 允许的软链源根列表）。"""
    root = wb / "skills"
    if not root.is_dir():
        die(f"未找到工作台技能目录 {root} —— 请先运行 /ai-design-skills 生成共享工作台")
    sources = [root.resolve()]
    out: dict[str, Path] = {}
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        sm = d / "SKILL.md"
        if sm.is_file():
            out[frontmatter_name(sm) or d.name] = d

    # 唯一公开入口（含「全局初始化」命令）也要注册到工具全局目录，
    # 否则换到别的项目就没法调用 /ai-design-skills。
    if include_entries:
        added = False
        for name in ENTRIES:
            d = SKILLS_SRC / name
            sm = d / "SKILL.md"
            if sm.is_file():
                out[frontmatter_name(sm) or name] = d
                added = True
        if added:
            sources.append(SKILLS_SRC.resolve())
    return out, sources


def read_manifest(tool_dir: Path) -> tuple[set[str], dict[str, str]]:
    mf = tool_dir / MANIFEST
    if not mf.is_file():
        return set(), {}
    try:
        data = json.loads(mf.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set(), {}
    managed = set(data.get("managed", []))
    modes = data.get("modes")
    if not isinstance(modes, dict):
        modes = {}
    return managed, modes


def owned(tool_dir: Path, sources: list[Path], managed: set[str]) -> set[str]:
    """本包拥有的技能名：清单记录的 + 指向工作台/入口源的软链（含断链）。"""
    result = set(managed)
    if not tool_dir.is_dir():
        return result
    for p in tool_dir.iterdir():
        if not p.is_symlink():
            continue
        try:
            real = p.resolve()
        except OSError:
            result.add(p.name)  # 断链：算我们拥有，才能清掉
            continue
        if any(str(real).startswith(str(s)) for s in sources):
            result.add(p.name)
    return result


def is_correct(target: Path, src: Path, mode: str) -> bool:
    if target.is_symlink():
        if mode == "copy":
            return False
        try:
            return target.resolve() == src.resolve()
        except OSError:
            return False
    if mode == "symlink":
        return False
    if not target.is_dir():
        return False
    return dir_hash(target) == dir_hash(src)


def remove(target: Path) -> None:
    if target.is_symlink() or target.is_file():
        target.unlink()
    elif target.is_dir():
        shutil.rmtree(target)


def install(target: Path, src: Path, mode: str) -> str:
    if mode in ("auto", "symlink"):
        try:
            rel = os.path.relpath(src.resolve(), target.parent.resolve())
            target.symlink_to(rel, target_is_directory=True)
            return "symlink"
        except (OSError, NotImplementedError):
            if mode == "symlink":
                die(f"无法创建软链：{target}（可用 --mode copy 回退）")
    shutil.copytree(src, target)
    return "copy"


def guard(tool_dir: Path, scope: str, home: Path, project: Path) -> None:
    """作用域门禁：只许写本作用域根目录下，且不许写工具根目录或旧版目录。"""
    allowed = home if scope == "user" else project
    if not str(tool_dir).startswith(str(allowed)):
        die(f"越界：{tool_dir} 不在 {'用户主目录' if scope == 'user' else '项目'} {allowed} 内")
    if tool_dir.name != "skills":
        die(f"{tool_dir} 不是 skills 目录（工具根目录本身不会被扫描）")
    # Codex 旧版遗留目录不是技能发现目录，禁止写入
    if tool_dir == home / ".codex" / "skills" or tool_dir == project / ".codex" / "skills":
        die(f"{tool_dir} 是旧版遗留目录，不是技能发现目录；请检查 tool-dirs.json")


def reconcile_one(tool_dir: Path, label: str, exp: dict[str, Path], sources: list[Path],
                  mode: str, dry_run: bool, scope: str, wb: Path) -> dict:
    managed, known_modes = read_manifest(tool_dir)
    have = owned(tool_dir, sources, managed)
    added = updated = removed = 0
    skipped: list[str] = []
    modes: dict[str, str] = {}

    if not dry_run:
        tool_dir.mkdir(parents=True, exist_ok=True)

    # 1) 清孤儿（我们拥有、但已不在期望集合里）
    for name in sorted(have - set(exp)):
        if not dry_run:
            remove(tool_dir / name)
        removed += 1

    # 2) 新建 / 更新 / 保留；用户自己的同名技能绝不碰
    for name, src in sorted(exp.items()):
        target = tool_dir / name
        exists = target.exists() or target.is_symlink()
        if exists and is_correct(target, src, mode):
            modes[name] = "symlink" if target.is_symlink() else (
                known_modes.get(name) or "copy"
            )
            continue
        if exists and name not in have:
            skipped.append(name)
            continue
        if exists:
            if not dry_run:
                remove(target)
            updated += 1
        else:
            added += 1
        if not dry_run:
            modes[name] = install(target, src, mode)
        else:
            modes[name] = "symlink" if mode != "copy" else "copy"

    # 3) 落清单（按技能记录真实 mode + 作用域，幂等不再误报）
    if not dry_run:
        (tool_dir / MANIFEST).write_text(
            json.dumps({
                "package": "ai-design-skills",
                "scope": scope,
                "workbench": str(wb),
                "managed": sorted(exp),
                "modes": modes,
            }, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    used = sorted(set(modes.values()))
    return {
        "label": label, "tool_dir": str(tool_dir),
        "added": added, "updated": updated, "removed": removed,
        "skipped": skipped,
        "mode": "/".join(used) if used else "-",
        "count": len(exp),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="按工具真实目录规则对账注册设计技能")
    ap.add_argument("--scope", choices=["user", "project"], default=None,
                    help="默认取 tool-dirs.json 的 default_scope（user = 用户全局）")
    ap.add_argument("--home", default=None, help="覆盖用户主目录（测试用）")
    ap.add_argument("--project", default=None, help="当前项目根目录（默认 cwd）")
    ap.add_argument("--workbench", default=None, help="覆盖共享工作台路径（测试用）")
    ap.add_argument("--tool", action="append", default=[],
                    help="只装指定工具 key，可多次；显式指定视为检测到")
    ap.add_argument("--tool-dir", action="append", default=[],
                    help="兼容参数：显式追加技能目录（相对项目根或绝对路径）")
    ap.add_argument("--mode", choices=["auto", "symlink", "copy"], default="auto")
    ap.add_argument("--no-entries", action="store_true",
                    help="不注册公开入口命令（默认注册）")
    ap.add_argument("--scan", action="store_true", help="兼容参数；默认行为就是扫描探测")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rules = load_rules()
    scope = args.scope or rules["default_scope"]
    home = Path(args.home).resolve() if args.home else Path.home().resolve()
    project = Path(args.project).resolve() if args.project else Path.cwd().resolve()
    wb = Path(args.workbench).resolve() if args.workbench else workbench(scope, home, project)

    exp, sources = expected(wb, include_entries=not args.no_entries)

    rows = probe(scope, home, project, only=set(args.tool) or None)
    targets: list[tuple[Path, str]] = [
        (r["skills_dir"], r["name"]) for r in rows if r["will_write"]
    ]
    for t in args.tool_dir:
        p = Path(t).resolve() if os.path.isabs(t) else (project / t).resolve()
        if (p, "显式指定") not in targets:
            targets.append((p, "显式指定"))

    print(render_table(rows, home))
    print(f"\n工作台: {wb}（scope={scope}）")
    print(f"用户作品: {artifacts_dir(project)}（按项目隔离，不进工作台）")
    print(f"期望技能: {len(exp)} 个（{'含' if not args.no_entries else '不含'}公开入口命令）")

    if not targets:
        die("未检测到任何 AI 工具目录。按「只装检测到的目录」原则，不擅自创建。"
            "请先用 --tool 指定，或先初始化对应工具。")

    results = []
    for tool_dir, label in targets:
        guard(tool_dir, scope, home, project)
        results.append(reconcile_one(tool_dir, label, exp, sources,
                                     args.mode, args.dry_run, scope, wb))

    prefix = "[dry-run] " if args.dry_run else ""
    print(f"\n{prefix}对账结果（{len(targets)} 个工具目录）：")
    for r in results:
        d = r["tool_dir"].replace(str(home), "~")
        print(f"  {r['label']:<34}{d:<38}"
              f"新增 {r['added']} / 更新 {r['updated']} / 移除 {r['removed']} "
              f"（mode={r['mode']}）")
        if r["skipped"]:
            print(f"    ⚠ 用户自己的同名技能，已跳过不碰：{', '.join(r['skipped'])}")
    skipped_tools = [r["name"] for r in rows if not r["will_write"]]
    if skipped_tools:
        print(f"  未检测到、未创建任何目录：{'、'.join(skipped_tools)}")
    print("  提示：部分工具需重启会话 / 重载窗口才能看到新命令。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
