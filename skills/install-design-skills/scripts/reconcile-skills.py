#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reconcile-skills.py — 按 AI 工具扫描路径，把 .design/skills/ 对账注册到工具目录。

与 shuhe-role-skills 旧版的两点关键差异（本包的改造点）：

1. **扫描到的全装**：不再「取第一个匹配」。检测项目内**所有**已存在的 AI 工具目录，
   每个都做一次声明式对账并建软链；**未检测到的目录一律不写**。
   用户多 AI 工具并用（Claude Code + Cursor + Codex …）时，每个工具都能读到命令。
2. **幂等模式不误报**：旧版在无任何安装动作时把 used_mode 写成 "symlink"，
   但实际可能是 copy。本版按技能逐个记录真实 mode 并落进清单，重复执行结果恒定。

对账规则（幂等）：
    期望集合 = <project>/.design/skills/ 下所有含 SKILL.md 的技能（名字取 frontmatter name）
    本技能拥有 = <tool-dir>/.design-managed.json 记录的 + 指向本项目 .design/skills 的软链（含断链）
    多退少补：
      在集合内且正确         → 保留
      在集合内但过期/不一致   → 删除后重建
      不在工具目录           → 新建
      本技能拥有但不在集合    → 删除（清孤儿）
      不是本技能拥有（用户自己的技能）→ 绝不碰

用法:
    python3 reconcile-skills.py --project <项目根> --scan
    python3 reconcile-skills.py --project <项目根> --tool-dir .claude/skills --tool-dir .cursor/skills
        [--mode auto|symlink|copy] [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

MANIFEST = ".design-managed.json"

# 检测特征与技能目录成对：marker 目录存在，才认为这个工具在该项目里被使用。
# 顺序只影响输出顺序，不再影响「装哪个」——检测到的全装。
TOOL_DIRS = [
    ("Claude Code / Cline", ".claude", ".claude/skills"),
    ("Codex", ".codex", ".codex/skills"),
    ("通用 Agent Skills", ".agents", ".agents/skills"),
    ("Cursor", ".cursor", ".cursor/skills"),
    ("OpenClaw", ".openclaw", ".openclaw/skills"),
    ("CodeBuddy", ".codebuddy", ".codebuddy/skills"),
    ("Qoder", ".qoder", ".qoder/skills"),
    ("Reasonix", ".reasonix", ".reasonix/skills"),
]


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


def expected(project: Path) -> dict[str, Path]:
    root = project / ".design" / "skills"
    if not root.is_dir():
        die(f"未找到 .design/skills/ —— 请先运行 /apply-design-skills")
    out: dict[str, Path] = {}
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        skill_md = d / "SKILL.md"
        if not skill_md.is_file():
            continue
        out[frontmatter_name(skill_md) or d.name] = d
    return out


def read_manifest(tool_dir: Path) -> tuple[set[str], dict[str, str]]:
    """返回（已登记的技能名集合, 每个技能的实际模式）。兼容旧版只有 managed 的清单。"""
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
        # 旧格式：只有顶层 mode。信息不足时留空，由对账重新探测实际类型。
        modes = {}
    return managed, modes


def owned(tool_dir: Path, project: Path, managed: set[str]) -> set[str]:
    """本技能拥有的技能名：清单记录的 + 指向本项目 .design/skills 的软链（含断链）。"""
    result = set(managed)
    if tool_dir.is_dir():
        for p in tool_dir.iterdir():
            if not p.is_symlink():
                continue
            try:
                real = p.resolve()
            except OSError:
                result.add(p.name)  # 断链：算我们拥有，才能清掉
                continue
            if str(real).startswith(str((project / ".design" / "skills").resolve())):
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
        return False  # 期望软链但当前是实体目录 → 重建
    if not target.is_dir():
        return False
    return dir_hash(target) == dir_hash(src)


def remove(target: Path) -> None:
    if target.is_symlink() or target.is_file():
        target.unlink()
    elif target.is_dir():
        shutil.rmtree(target)


def install(target: Path, src: Path, mode: str) -> str:
    """返回实际使用的模式。"""
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


def reconcile_one(project: Path, tool_rel: str, label: str, exp: dict[str, Path],
                  mode: str, dry_run: bool) -> dict:
    tool_dir = (project / tool_rel).resolve()
    if not str(tool_dir).startswith(str(project)):
        die(f"工具目录必须在项目内（禁止写用户全局目录）：{tool_dir}")

    managed, known_modes = read_manifest(tool_dir)
    have = owned(tool_dir, project, managed)
    added = updated = removed = 0
    modes: dict[str, str] = {}

    if not dry_run:
        tool_dir.mkdir(parents=True, exist_ok=True)

    # 1) 清孤儿（我们拥有、但已不在期望集合里）
    for name in sorted(have - set(exp)):
        if not dry_run:
            remove(tool_dir / name)
        removed += 1

    # 2) 新建 / 更新 / 保留
    for name, src in sorted(exp.items()):
        target = tool_dir / name
        exists = target.exists() or target.is_symlink()
        if exists and is_correct(target, src, mode):
            # 幂等路径：探测真实类型，不猜。
            modes[name] = "symlink" if target.is_symlink() else (
                known_modes.get(name) or "copy"
            )
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

    # 3) 落清单（按技能记录真实 mode，幂等不再误报）
    if not dry_run:
        (tool_dir / MANIFEST).write_text(
            json.dumps(
                {"package": "ai-design-skills", "managed": sorted(exp), "modes": modes},
                ensure_ascii=False, indent=2,
            ) + "\n",
            encoding="utf-8",
        )

    used = sorted(set(modes.values()))
    return {
        "label": label, "tool_dir": tool_rel,
        "added": added, "updated": updated, "removed": removed,
        "mode": "/".join(used) if used else "-",
        "count": len(exp),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="扫描 AI 工具目录并对账注册设计技能")
    ap.add_argument("--project", required=True, help="目标项目根目录")
    ap.add_argument("--scan", action="store_true",
                    help="扫描项目内所有已存在的 AI 工具目录，只向检测到的目录安装")
    ap.add_argument("--tool-dir", action="append", default=[],
                    help="显式指定工具技能目录（可多次）；与 --scan 可并用")
    ap.add_argument("--mode", choices=["auto", "symlink", "copy"], default="auto")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.scan and not args.tool_dir:
        die("请指定 --scan（推荐）或至少一个 --tool-dir")

    project = Path(args.project).resolve()
    exp = expected(project)

    targets: list[tuple[str, str]] = []
    if args.scan:
        for label, marker, skills in TOOL_DIRS:
            if (project / marker).is_dir():
                targets.append((skills, label))
    for t in args.tool_dir:
        if (t, "显式指定") not in targets:
            targets.append((t, "显式指定"))

    if not targets:
        die("项目内没有检测到任何 AI 工具目录（.claude/ .codex/ .cursor/ 等）。"
            "按「只装检测到的目录」原则，不擅自创建。请先用 --tool-dir 指定，或先初始化对应工具。")

    results = []
    for tool_rel, label in targets:
        results.append(reconcile_one(project, tool_rel, label, exp, args.mode, args.dry_run))

    prefix = "[dry-run] " if args.dry_run else ""
    print(f"{prefix}扫描到 {len(targets)} 个 AI 工具目录；期望技能 {len(exp)} 个")
    for r in results:
        print(f"  {r['label']:<22} {r['tool_dir']:<24} "
              f"新增 {r['added']} / 更新 {r['updated']} / 移除 {r['removed']} "
              f"（mode={r['mode']}）")
    if args.scan:
        all_tools = [s for _, _, s in TOOL_DIRS]
        skipped = [s for s in all_tools if s not in {t for t, _ in targets}]
        if skipped:
            print(f"  未检测到、已跳过：{', '.join(skipped)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
