#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify-render.py — 渲染产物的结构校验（在暂存树或真实项目上运行）。

抓的是旧包踩过的坑：引用不可达、串内容、占位符残留、技能缺 agents、
驱动卡门禁缺失；本包另加工种注册表与产物一致性对账。

用法:
    python3 verify-render.py --project <项目根，内含 .design/>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_]+\}\}")
REQUIRED_RULES = ("交互模式.md", "状态机与收口.md", "产物与来源规范.md",
                  "人格.md", "设计通用规范.md")
ENTRY_SKILLS = ("design-router", "design-any")


def main() -> int:
    ap = argparse.ArgumentParser(description="校验 .design/ 渲染产物")
    ap.add_argument("--project", required=True)
    args = ap.parse_args()

    root = Path(args.project).resolve() / ".design"
    errs: list[str] = []
    warns: list[str] = []

    def need(cond, msg):
        if not cond:
            errs.append(msg)

    if not root.is_dir():
        print(f"ERROR: 未找到 {root}", file=sys.stderr)
        return 1

    # 1. 配置
    cfg_path = root / "design.json"
    need(cfg_path.is_file(), "缺少 .design/design.json")
    cfg = {}
    if cfg_path.is_file():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errs.append(f"design.json 不是合法 JSON: {e}")
        need(cfg.get("package") == "ai-design-skills", "design.json 的 package 不正确")
        need(bool(cfg.get("package_version")), "design.json 缺 package_version")
        need(cfg.get("scope") in ("user", "project"), "design.json 的 scope 必须是 user / project")
        need(bool(cfg.get("workbench")), "design.json 缺 workbench 工作台路径")
        need(bool(cfg.get("design_root")), "design.json 缺 design_root 共享资产路径")
        need(isinstance(cfg.get("disciplines"), list) and bool(cfg.get("disciplines")),
             "design.json 的 disciplines 必须是非空数组")

    reg_path = root / "disciplines.json"
    need(reg_path.is_file(), "缺少 .design/disciplines.json")
    registry = {}
    if reg_path.is_file():
        try:
            registry = json.loads(reg_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errs.append(f"disciplines.json 不是合法 JSON: {e}")
        need(registry.get("schema_version") == 1, "disciplines.json 的 schema_version 不正确")

    # 2. rules
    rules = root / "rules"
    for name in REQUIRED_RULES:
        need((rules / name).is_file(), f"rules/ 缺 {name}")

    # 3. references 与注册表对账
    refs = root / "references"
    need(refs.is_dir(), "缺少 .design/references/")
    have_refs = {p.name for p in refs.glob("*.md")} if refs.is_dir() else set()
    want_refs = set(registry.get("shared_references", []))
    for r in sorted(want_refs - have_refs):
        errs.append(f"references/ 缺少注册表登记的文件: {r}")
    for r in sorted(have_refs - want_refs):
        errs.append(f"references/ 存在未登记的死文件: {r}")

    # 4. 驱动卡
    summary = root / "templates" / "00-summary.md"
    need(summary.is_file(), "templates/ 缺 00-summary.md 驱动卡")
    if summary.is_file():
        text = summary.read_text(encoding="utf-8")
        need("status" in text, "驱动卡缺 status 状态字段")

    # 5. artifacts 用户区
    need((root / "artifacts").is_dir(), "缺少 .design/artifacts/（用户区必须存在）")

    # 6. skills
    skills_root = root / "skills"
    need(skills_root.is_dir(), "缺少 .design/skills/")
    skill_names = set()
    if skills_root.is_dir():
        for d in sorted(p for p in skills_root.iterdir() if p.is_dir()):
            skill_md = d / "SKILL.md"
            need(skill_md.is_file(), f"skills/{d.name}/ 缺 SKILL.md")
            need((d / "agents" / "openai.yaml").is_file(),
                 f"skills/{d.name}/ 缺 agents/openai.yaml")
            skill_names.add(d.name)
            if skill_md.is_file():
                text = skill_md.read_text(encoding="utf-8")
                if not text.startswith("---\n"):
                    errs.append(f"skills/{d.name}/SKILL.md 缺 frontmatter")
                else:
                    end = text.find("\n---\n", 4)
                    fm = text[4:end if end > 0 else len(text)]
                    m = re.search(r"^name:\s*(\S+)", fm, re.M)
                    need(bool(m), f"skills/{d.name}/SKILL.md frontmatter 缺 name")
                    if m:
                        need(m.group(1) == d.name,
                             f"skills/{d.name}/SKILL.md 的 name={m.group(1)} 与目录名不一致")

        for e in ENTRY_SKILLS:
            need(e in skill_names, f"缺入口技能 {e}")

        # 选中的 core 工种必须都渲染出来
        core_keys = {d["key"] for d in registry.get("disciplines", []) if d["tier"] == "core"}
        for k in cfg.get("disciplines", []):
            if k in core_keys:
                need(k in skill_names, f"选中工种 {k} 未渲染成技能")

    # 7. 占位符残留 + 引用可达（渲染过的文本文件）
    #    工作台可能是 ~/.design（全局）或 .design（项目级），两种前缀都要认。
    rules_have = {p.name for p in (root / "rules").glob("*.md")} if (root / "rules").is_dir() else set()
    ref_in_skill = re.compile(
        r"(?:~/\.design|\.design)/(references|rules)/([^\s`)、，。|]+\.md)"
    )
    scan = [root / "design.json", root / "README.md"]
    scan += list((root / "rules").glob("*.md")) if (root / "rules").is_dir() else []
    scan += list((root / "templates").glob("*.md")) if (root / "templates").is_dir() else []
    scan += list(skills_root.rglob("*")) if skills_root.is_dir() else []
    for p in scan:
        if not p.is_file() or p.suffix not in (".md", ".json", ".yaml", ".tpl"):
            continue
        text = p.read_text(encoding="utf-8")
        left = PLACEHOLDER_RE.findall(text)
        if left:
            errs.append(f"{p.relative_to(root)}: 占位符未替换 {sorted(set(left))}")
        for kind, name in ref_in_skill.findall(text):
            pool = have_refs if kind == "references" else rules_have
            if name not in pool:
                errs.append(f"{p.relative_to(root)}: 引用了不存在的 {kind}/{name}")

    # 8. README 存在
    need((root / "README.md").is_file(), "缺少 .design/README.md")

    for w in warns:
        print(f"WARN: {w}")
    if errs:
        for e in errs:
            print(f"ERROR: {e}", file=sys.stderr)
        print(f"结构校验失败：{len(errs)} 项", file=sys.stderr)
        return 1
    print(f"结构校验通过：rules {len(REQUIRED_RULES)} / references {len(have_refs)} / "
          f"skills {len(skill_names)} / 0 占位符残留 / 引用全部可达")
    return 0


if __name__ == "__main__":
    sys.exit(main())
