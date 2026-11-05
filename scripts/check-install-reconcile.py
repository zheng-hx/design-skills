#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-install-reconcile.py — 全局安装（用户级）的端到端回归测试（真跑，不 mock）。

临时建一个 HOME + 项目 → 真实渲染工作台到 ~/.design/ → 真实按工具真实规则对账注册 →
逐项断言 → 清理。覆盖 8 个场景：

  1. 自动探测、只装检测到的工具（默认 user 作用域）：只用 WorkBuddy 时绝不出现 ~/.agents/
  2. 用户同时用 Codex 时，才创建 ~/.agents/skills；已装的 WorkBuddy 不受影响
  3. 幂等复跑 0/0/0，且清单按技能记录真实 mode（修掉旧包把 copy 误报 symlink 的 bug）
  4. 改工种集合后清孤儿（多退少补）
  5. 用户自己放进工具目录的技能绝不被删
  6. 与 shuhe-role-skills 的 .roles-managed.json 共存互不干扰
  7. copy 模式幂等不误报 mode
  8. 升级重渲染后 <项目>/.design/artifacts/ 里的作品一个不少

用法:
    python3 scripts/check-install-reconcile.py
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "skills" / "install-design-skills" / "tool-dirs.json"
RENDER = ROOT / "skills" / "apply-design-skills" / "scripts" / "render-design-package.py"
RECON = ROOT / "skills" / "install-design-skills" / "scripts" / "reconcile-skills.py"

# 本机实测的 8 个工具 user 根目录；检测依据是「用户全局根目录是否存在」。
ALL_USER_ROOTS = [
    "~/.workbuddy", "~/.codex", "~/.agents", "~/.claude", "~/.cursor",
    "~/.codebuddy", "~/.openclaw", "~/.qoder", "~/.reasonix",
]

passed = 0
failed: list[str] = []


def check(cond: bool, label: str) -> None:
    global passed
    if cond:
        passed += 1
        print(f"  ✅ {label}")
    else:
        failed.append(label)
        print(f"  ❌ {label}", file=sys.stderr)


def run(script: Path, *args: str) -> str:
    r = subprocess.run([sys.executable, str(script), *args],
                       capture_output=True, text=True)
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0:
        raise RuntimeError(f"命令失败 {script.name} {' '.join(args)}\n{out}")
    return out


def skill_count(tool_skills: Path) -> int:
    return len([p for p in tool_skills.iterdir() if p.is_dir()])


def counts(out: str) -> list[tuple[int, int, int]]:
    return [(int(a), int(b), int(c)) for a, b, c in
            re.findall(r"新增 (\d+) / 更新 (\d+) / 移除 (\d+)", out)]


def setup_home(home: Path, present: list[str]) -> None:
    """按 present 列表在临时 HOME 下创建工具根目录；其余一律不创建（模拟本机未装）。"""
    for rel in ALL_USER_ROOTS:
        p = (home / rel.lstrip("~/")).resolve()
        if rel in present:
            p.mkdir(parents=True, exist_ok=True)
        else:
            # 确保不存在
            if p.exists():
                shutil.rmtree(p, ignore_errors=True)


def main() -> int:
    rules = json.loads(RULES.read_text(encoding="utf-8"))
    wb_skills = "~/.workbuddy/skills"
    agents_skills = "~/.agents/skills"

    with tempfile.TemporaryDirectory(prefix="ai-design-install-") as td:
        home = Path(td) / "home"
        proj = Path(td) / "project"
        home.mkdir()
        proj.mkdir()

        # ---------- 场景 1：只用 WorkBuddy（自动探测） ----------
        print("\n[场景 1] 自动探测 + 仅 WorkBuddy：不创建 ~/.agents 等无关目录")
        setup_home(home, ["~/.workbuddy"])
        run(RENDER, "--project", str(proj), "--scope", "user", "--home", str(home),
            "--disciplines", "core")
        out = run(RECON, "--scope", "user", "--home", str(home), "--project", str(proj))
        wbs = (home / ".workbuddy/skills").resolve()
        check(wbs.is_dir(), "WorkBuddy 全局技能目录已创建")
        check(skill_count(wbs) == 24, f"WorkBuddy 装了 24 个技能（实际 {skill_count(wbs)}）")
        check((wbs / ".design-managed.json").is_file(), "写了 .design-managed.json 清单")
        for rel in [agents_skills, "~/.claude/skills", "~/.cursor/skills", "~/.codex/skills",
                    "~/.openclaw/skills", "~/.codebuddy/skills", "~/.qoder/skills",
                    "~/.reasonix/skills"]:
            p = (home / rel.lstrip("~/")).resolve()
            check(not p.exists(), f"未创建无关目录 {rel}")
        # 工作台作用域正确
        design_json = json.loads((home / ".design" / "design.json").read_text(encoding="utf-8"))
        check(design_json.get("scope") == "user", "工作台 design.json 的 scope=user")

        # ---------- 场景 2：同时用 Codex，才建 ~/.agents/skills ----------
        print("\n[场景 2] 加 Codex：才创建 ~/.agents/skills，WorkBuddy 不受影响")
        setup_home(home, ["~/.workbuddy", "~/.codex"])  # Codex 检测依据含 ~/.codex
        out = run(RECON, "--scope", "user", "--home", str(home), "--project", str(proj),
                  "--tool", "workbuddy", "--tool", "codex")
        ags = (home / ".agents/skills").resolve()
        check(ags.is_dir(), "Codex 的全局技能目录 ~/.agents/skills 已创建")
        check(skill_count(ags) == 24, f"Codex 装了 24 个技能（实际 {skill_count(ags)}）")
        check(skill_count(wbs) == 24, f"WorkBuddy 仍 24 个（实际 {skill_count(wbs)}）")
        # 注意：~/.codex/skills 不是技能发现目录，不应写入
        check(not (home / ".codex" / "skills").exists(), "未向旧版遗留 ~/.codex/skills 写入")

        # ---------- 场景 3：幂等复跑 0/0/0，mode 真实 ----------
        print("\n[场景 3] 幂等复跑：0/0/0，清单记录真实 mode")
        out = run(RECON, "--scope", "user", "--home", str(home), "--project", str(proj),
                  "--tool", "workbuddy", "--tool", "codex")
        cs = counts(out)
        check(all(a == 0 and b == 0 and c == 0 for a, b, c in cs), f"对账 0/0/0（实际 {cs}）")
        man = json.loads((wbs / ".design-managed.json").read_text(encoding="utf-8"))
        check(man.get("scope") == "user", "清单 scope=user")
        check(man.get("modes", {}).get("ui-design") == "symlink", "清单按技能记录真实 mode=symlink")
        check(len(man.get("managed", [])) == 24, f"清单 managed 24 项（实际 {len(man.get('managed', []))}）")

        # ---------- 场景 4：改工种集合后清孤儿 ----------
        print("\n[场景 4] 缩小工种集合到 ui-design：清掉 18 个孤儿")
        run(RENDER, "--project", str(proj), "--scope", "user", "--home", str(home),
            "--disciplines", "ui-design")
        out = run(RECON, "--scope", "user", "--home", str(home), "--project", str(proj),
                  "--tool", "workbuddy", "--tool", "codex")
        cs = counts(out)
        # 期望 6 = ui-design + design-router + design-any + 3 入口命令；移除 24-6=18
        check(skill_count(wbs) == 6, f"WorkBuddy 现 6 个（实际 {skill_count(wbs)}）")
        check(skill_count(ags) == 6, f"Codex 现 6 个（实际 {skill_count(ags)}）")
        check(any(c == 18 for _, _, c in cs), f"移除 18 个孤儿（实际 {cs}）")

        # ---------- 场景 5：用户自己的技能绝不碰 ----------
        print("\n[场景 5] 用户自己的技能：保留、跳过、告警")
        own = wbs / "my-own-skill"
        own.mkdir(parents=True)
        (own / "SKILL.md").write_text("---\nname: my-own-skill\n---\n", encoding="utf-8")
        out = run(RECON, "--scope", "user", "--home", str(home), "--project", str(proj),
                  "--tool", "workbuddy")
        check(own.is_dir(), "用户自己的 my-own-skill 仍在")
        check((own / "SKILL.md").is_file(), "用户技能文件未动")
        check("my-own-skill" not in (home / ".workbuddy/skills/.design-managed.json").read_text(encoding="utf-8"),
              "用户技能不在本包清单（本包绝不碰）")

        # ---------- 场景 6：与角色包的 .roles-managed.json 共存 ----------
        print("\n[场景 6] 与角色包 .roles-managed.json 共存互不干扰")
        roles_man = wbs / ".roles-managed.json"
        roles_man.write_text(json.dumps({"package": "shuhe-role-skills", "managed": ["foo"]},
                                        ensure_ascii=False), encoding="utf-8")
        run(RECON, "--scope", "user", "--home", str(home), "--project", str(proj),
            "--tool", "workbuddy")
        check(roles_man.is_file(), ".roles-managed.json 未被删除")
        check(json.loads(roles_man.read_text(encoding="utf-8")).get("package") == "shuhe-role-skills",
              ".roles-managed.json 内容未变")

        # ---------- 场景 7：copy 模式幂等 ----------
        print("\n[场景 7] copy 模式幂等：不误报 mode")
        out = run(RECON, "--scope", "user", "--home", str(home), "--project", str(proj),
                  "--tool", "workbuddy", "--mode", "copy")
        cs = counts(out)
        # copy 模式首次会把已有软链重建为目录副本，计入 更新（不是 新增）
        check(any(b > 0 for _, b, _ in cs), f"copy 首次会重建（实际 {cs}）")
        out2 = run(RECON, "--scope", "user", "--home", str(home), "--project", str(proj),
                   "--tool", "workbuddy", "--mode", "copy")
        cs2 = counts(out2)
        check(all(a == 0 and b == 0 and c == 0 for a, b, c in cs2), f"copy 复跑 0/0/0（实际 {cs2}）")
        man2 = json.loads((wbs / ".design-managed.json").read_text(encoding="utf-8"))
        check(man2.get("modes", {}).get("ui-design") == "copy", "清单 mode 记为 copy（不再误报 symlink）")
        # 还原成 symlink 以便后续场景
        run(RECON, "--scope", "user", "--home", str(home), "--project", str(proj),
            "--tool", "workbuddy", "--tool", "codex")

        # ---------- 场景 8：升级重渲染保留用户作品 ----------
        print("\n[场景 8] 升级重渲染：<项目>/.design/artifacts 作品保留")
        art = proj / ".design" / "artifacts"
        art.mkdir(parents=True, exist_ok=True)
        keep = art / "keep-me.md"
        keep.write_text("用户的设计稿，升级不能丢", encoding="utf-8")
        # 用 core 重新渲染（模拟升级到更多工种），再对账注册
        run(RENDER, "--project", str(proj), "--scope", "user", "--home", str(home),
            "--disciplines", "core")
        run(RECON, "--scope", "user", "--home", str(home), "--project", str(proj),
            "--tool", "workbuddy", "--tool", "codex")
        check(keep.is_file(), "用户在 artifacts/ 的作品升级后仍在")
        # 24 个期望技能 + 用户自己的 my-own-skill（始终保留）= 25
        check(skill_count(wbs) == 25, f"升级后 WorkBuddy 回到 24 个+用户技能（实际 {skill_count(wbs)}）")
        check((wbs / "brand-design").is_dir(), "升级后新增的 core 工种已注册")
        check(own.is_dir(), "用户自己的技能在升级后仍在")

        # 临时目录整体删除，真实 HOME 不动
        print(f"\n结果：{passed} 项通过，{len(failed)} 项失败")

    if failed:
        print("❌ 失败的断言：", file=sys.stderr)
        for f in failed:
            print(f"   - {f}", file=sys.stderr)
        return 1
    print("✅ 全局安装（用户级）端到端回归全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
