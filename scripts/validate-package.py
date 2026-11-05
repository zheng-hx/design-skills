#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate-package.py — 技能源仓库的结构校验。

管的是「装得上、结构对、公开/隐藏边界不破、生成物不漂移」：
  1. 公开入口（单技能）：SKILL.md + frontmatter(name/description) + agents/openai.yaml
  2. 隐藏层边界：capabilities/ 下不得出现 SKILL.md（必须叫 CAPABILITY.md），
     技能模板必须是 .md.tpl，不能被工具直接扫成命令
  3. 注册表 → 生成物不漂移（跑 build-disciplines.py --check）
  4. references 与 shared_references 完全对账
  5. 占位符全覆盖：capabilities 里出现的每个 {{XXX}} 都必须在渲染脚本里有定义
     （这条抓的正是「复用旧包规则漏注入 ARTIFACT_DIR」那类事故）
  6. plugin.json 的 skills 数组与实际入口对账

用法: python3 scripts/validate-package.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
CAPS = SKILLS / "ai-design-skills" / "capabilities"
REGISTRY = CAPS / "design-core" / "disciplines.json"
DISC_SKILLS = CAPS / "design-disciplines" / "skills"
REFS = CAPS / "design-disciplines" / "references"
RENDER = SKILLS / "ai-design-skills" / "scripts" / "render-design-package.py"
BUILD = SKILLS / "ai-design-skills" / "scripts" / "build-disciplines.py"
ENTRIES = ("ai-design-skills",)

PLACEHOLDER_RE = re.compile(r"\{\{([A-Z_]+)\}\}")


def main() -> int:
    errs: list[str] = []

    # 1. 公开入口
    for e in ENTRIES:
        d = SKILLS / e
        sm = d / "SKILL.md"
        if not sm.is_file():
            errs.append(f"入口 {e}: 缺 SKILL.md")
            continue
        text = sm.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            errs.append(f"入口 {e}: SKILL.md 缺 frontmatter")
        else:
            end = text.find("\n---\n", 4)
            fm = text[4:end if end > 0 else len(text)]
            if not re.search(r"^name:\s*\S+", fm, re.M):
                errs.append(f"入口 {e}: frontmatter 缺 name")
            if not re.search(r"^description:\s*\S+", fm, re.M):
                errs.append(f"入口 {e}: frontmatter 缺 description")
        if not (d / "agents" / "openai.yaml").is_file():
            errs.append(f"入口 {e}: 缺 agents/openai.yaml")

    # 公开层不该有第四个入口（隐藏层除外）
    public = {p.name for p in SKILLS.iterdir() if p.is_dir()}
    for extra in sorted(public - set(ENTRIES)):
        errs.append(f"skills/ 下出现未登记的公开目录: {extra}")

    # 2. 隐藏层边界
    if not CAPS.is_dir():
        errs.append("缺 capabilities/ 隐藏层")
    else:
        for p in CAPS.rglob("SKILL.md"):
            errs.append(f"隐藏层出现可发现的 SKILL.md: {p.relative_to(ROOT)}")
        for p in CAPS.rglob("*.md.tpl"):
            if "skills" not in p.parts and "templates" not in p.parts:
                errs.append(f"模板放错目录: {p.relative_to(ROOT)}")
        for cap in ("design-core", "design-disciplines"):
            if not (CAPS / cap / "CAPABILITY.md").is_file():
                errs.append(f"capabilities/{cap} 缺 CAPABILITY.md")

    # 3. 注册表 → 生成物不漂移
    r = subprocess.run([sys.executable, str(BUILD), "--check"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        errs.append(f"生成物与注册表不一致: {(r.stdout + r.stderr).strip()}")

    data = json.loads(REGISTRY.read_text(encoding="utf-8"))

    # 4. references 对账
    have = {p.name for p in REFS.glob("*.md")} if REFS.is_dir() else set()
    want = set(data["shared_references"])
    for x in sorted(want - have):
        errs.append(f"references/ 缺登记文件: {x}")
    for x in sorted(have - want):
        errs.append(f"references/ 存在未登记死文件: {x}")

    # 5. 占位符全覆盖
    render_src = RENDER.read_text(encoding="utf-8")
    defined = set(re.findall(r'"\{\{([A-Z_]+)\}\}"\s*:', render_src))
    used: set[str] = set()
    for p in CAPS.rglob("*"):
        if p.is_file() and p.suffix in (".md", ".tpl", ".json"):
            used |= set(PLACEHOLDER_RE.findall(p.read_text(encoding="utf-8")))
    for ph in sorted(used - defined):
        errs.append(f"占位符 {{{{ {ph} }}}} 在 capabilities 中出现但渲染脚本未定义")

    # 6. plugin.json 对账
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    declared = {s.rstrip("/").split("/")[-1] for s in plugin.get("skills", [])}
    if declared != set(ENTRIES):
        errs.append(f"plugin.json skills 与入口不一致: {sorted(declared)}")

    # 7. 技能目录完整性
    core = [d["key"] for d in data["disciplines"] if d["tier"] == "core"]
    for k in core:
        if not (DISC_SKILLS / k / "SKILL.md.tpl").is_file():
            errs.append(f"core 工种 {k} 缺 SKILL.md.tpl")
        if not (DISC_SKILLS / k / "agents" / "openai.yaml.tpl").is_file():
            errs.append(f"core 工种 {k} 缺 agents/openai.yaml.tpl")

    # 8. 渲染内容不得残留旧包路径；.design/rules|references 引用必须可达
    #    （抓的是「复用规则时忘了把 .roles/ 改成 .design/」这类路径残留事故）
    rule_files = {p.name for p in (CAPS / "design-core" / "rules").glob("*.md")}
    ref_files = {p.name for p in REFS.glob("*.md")}
    scanned = 0
    for p in CAPS.rglob("*"):
        if not p.is_file() or p.suffix not in (".md", ".tpl") or p.name == "CAPABILITY.md":
            continue
        scanned += 1
        text = p.read_text(encoding="utf-8")
        if ".roles/" in text:
            errs.append(f"{p.relative_to(ROOT)}: 渲染内容残留旧包路径 .roles/（复用规则未改路径）")
        # 源模板用 {{DESIGN_ROOT}} 占位，渲染后变成 ~/.design 或 .design；三种前缀都认。
        for kind, name in re.findall(
            r"(?:\{\{DESIGN_ROOT\}\}|~/\.design|\.design)/(rules|references)/"
            r"([^\s`)、，。|]+\.md)", text
        ):
            pool = rule_files if kind == "rules" else ref_files
            if name not in pool:
                errs.append(f"{p.relative_to(ROOT)}: 引用了不存在的 {kind}/{name}")

    if errs:
        for e in errs:
            print(f"ERROR: {e}", file=sys.stderr)
        print(f"包结构校验失败：{len(errs)} 项", file=sys.stderr)
        return 1
    print(f"✅ 包结构通过：{len(ENTRIES)} 个公开入口 / {len(core)} 个 core 工种 / "
          f"{len(have)} 份参考 / {len(used)} 个占位符全部已定义 / 生成物无漂移 / "
          f"{scanned} 份渲染内容路径与引用可达")
    return 0


if __name__ == "__main__":
    sys.exit(main())
