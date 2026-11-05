#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-evals.py — 行为评测与触发金标集的静态自洽校验。

不做审美评分，只保证「金标与评测文件本身没写坏、没漂移」：
  1. triggers.md 每条金标的期望技能必须真实存在（core 工种 / design-router / design-any）；
  2. 19 个 core 工种 + 2 个入口必须各至少有一条金标（覆盖）；
  3. 每份 eval 必备章节齐全，机器可判断言是合法 JSON 且 checks 结构正确；
  4. evals/README.md 里登记的评测文件都存在（不多不少）。

用法: python3 scripts/check-evals.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"
REGISTRY = ROOT / "skills" / "ai-design-skills" / "capabilities" / "design-core" / "disciplines.json"
TRIGGERS = EVALS / "triggers.md"
README = EVALS / "README.md"

ENTRIES = ("design-router", "design-any")
GOLD_ROW = re.compile(r"^\|\s*(\d+)\s*\|([^|]*)\|\s*/([a-z0-9-]+)\s*\|", re.M)
JSON_BLOCK = re.compile(r"```json\s*(.*?)\s*```", re.S)
JUDGES = {"exists", "sections", "match", "not_match", "if_match", "then_match", "min_count"}


def main() -> int:
    errs: list[str] = []
    if not TRIGGERS.is_file():
        print("ERROR: 缺 evals/triggers.md", file=sys.stderr)
        return 1

    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    core = {d["key"] for d in data["disciplines"] if d["tier"] == "core"}
    allowed = core | set(ENTRIES)

    # 1+2. 金标集
    seen: set[str] = set()
    rows = 0
    for num, phrase, skill in GOLD_ROW.findall(TRIGGERS.read_text(encoding="utf-8")):
        rows += 1
        if skill not in allowed:
            errs.append(f"triggers.md 第 {num} 条：期望技能 /{skill} 不存在（也不是 core 工种或入口）")
        if not phrase.strip():
            errs.append(f"triggers.md 第 {num} 条：用户会说为空")
        seen.add(skill)
    if rows == 0:
        errs.append("triggers.md 没解析到任何金标行")
    for k in sorted((core | set(ENTRIES)) - seen):
        errs.append(f"触发金标集缺覆盖：{k} 没有任何一条「用户会说」")

    # 3. eval 文件结构
    eval_files = sorted(p for p in EVALS.glob("*.md") if p.name not in ("README.md", "triggers.md"))
    if not eval_files:
        errs.append("evals/ 下没有任何评测文件")
    for p in eval_files:
        text = p.read_text(encoding="utf-8")
        for sec in ("## 输入", "## 期望", "### 结构断言", "### 门禁断言",
                    "### 反例", "## 机器可判断言", "## 判定"):
            if sec not in text:
                errs.append(f"{p.name}: 缺必备章节 {sec}")
        blocks = JSON_BLOCK.findall(text)
        if not blocks:
            errs.append(f"{p.name}: 缺 ```json 机器可判断言块")
            continue
        try:
            obj = json.loads(blocks[0])
        except json.JSONDecodeError as e:
            errs.append(f"{p.name}: 机器可判断言不是合法 JSON: {e}")
            continue
        checks = obj.get("checks")
        if not isinstance(checks, list) or not checks:
            errs.append(f"{p.name}: checks 必须是非空数组")
            continue
        for i, c in enumerate(checks, 1):
            if not isinstance(c, dict) or not c.get("file"):
                errs.append(f"{p.name}: checks[{i}] 缺 file")
                continue
            if not (JUDGES & set(c)):
                errs.append(f"{p.name}: checks[{i}] 没有任何有效判据")
            if "if_match" in c and "then_match" not in c:
                errs.append(f"{p.name}: checks[{i}] 有 if_match 但缺 then_match")

    # 4. README 登记的评测对账
    if README.is_file():
        linked = set(re.findall(r"\[[^\]]+\]\(([a-z0-9-]+\.md)\)",
                                README.read_text(encoding="utf-8")))
        linked.discard("triggers.md")
        have = {p.name for p in eval_files}
        for name in sorted(linked - have):
            errs.append(f"evals/README.md 登记了不存在的评测: {name}")
        for name in sorted(have - linked):
            errs.append(f"评测 {name} 未登记进 evals/README.md")

    if errs:
        for e in errs:
            print(f"ERROR: {e}", file=sys.stderr)
        print(f"评测自洽校验失败：{len(errs)} 项", file=sys.stderr)
        return 1
    print(f"✅ 评测自洽通过：金标 {rows} 条（覆盖 {len(seen)} 个技能）/ "
          f"{len(eval_files)} 份评测 / 机器断言结构合法")
    return 0


if __name__ == "__main__":
    sys.exit(main())
