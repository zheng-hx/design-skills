#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-install-reconcile.py — 多 AI 工具扫描安装的端到端回归测试（真跑，不 mock）。

临时建一个项目 → 真实渲染 → 真实扫描安装 → 逐项断言 → 清理。覆盖 8 个场景：

  1. 扫描到的所有 AI 工具目录都装上软链（不是「取第一个匹配」）
  2. 未检测到的工具目录一律不创建
  3. 幂等复跑 0/0/0，且清单按技能记录真实 mode
  4. 改工种集合后清孤儿（多退少补）
  5. 用户自己放进工具目录的技能绝不被删
  6. 与 shuhe-role-skills 的 .roles-managed.json 共存互不干扰
  7. copy 模式幂等不误报 mode（旧包 bug 回归）
  8. 升级重渲染后 .design/artifacts/ 里的作品一个不少

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
RENDER = ROOT / "skills" / "apply-design-skills" / "scripts" / "render-design-package.py"
RECON = ROOT / "skills" / "install-design-skills" / "scripts" / "reconcile-skills.py"
DETECTED = (".claude", ".cursor", ".codex")
UNDETECTED = (".agents", ".openclaw", ".codebuddy", ".qoder", ".reasonix")

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


def counts(out: str) -> list[tuple[int, int, int]]:
    return [(int(a), int(b), int(c)) for a, b, c in
            re.findall(r"新增 (\d+) / 更新 (\d+) / 移除 (\d+)", out)]


def symlinks(p: Path) -> dict[str, Path]:
    d = p / "skills"
    if not d.is_dir():
        return {}
    return {x.name: x.resolve() for x in d.iterdir() if x.is_symlink()}


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="ai-design-check-"))
    print(f"临时项目: {tmp}\n")
    try:
        for t in DETECTED:
            (tmp / t).mkdir()

        # ---- 1/2/3: 渲染 + 扫描全装 + 未检测不创建 + 幂等 ----
        print("[1] 渲染与多工具扫描安装")
        run(RENDER, "--project", str(tmp), "--disciplines", "ui-design,brand-design")
        exp = {p.name for p in (tmp / ".design" / "skills").iterdir() if p.is_dir()}
        check(len(exp) == 4, f"渲染出 4 个技能（2 工种 + 路由 + 兜底），实际 {len(exp)}")

        out = run(RECON, "--project", str(tmp), "--scan")
        check(len(counts(out)) == 3, f"扫描到 3 个工具目录并各自对账，实际 {len(counts(out))}")
        # macOS 上 /var 是 /private/var 的软链：两边都 resolve 才能比较真实路径
        exp_root = str((tmp / ".design" / "skills").resolve())
        for t in DETECTED:
            got = set(symlinks(tmp / t))
            check(got == exp, f"{t}/skills 软链集合与期望一致（{len(got)} 个）")
            check(all(str(v).startswith(exp_root)
                      for v in symlinks(tmp / t).values()),
                  f"{t} 软链都指向本项目 .design/skills")

        print("[2] 未检测到的目录一律不创建")
        for t in UNDETECTED:
            check(not (tmp / t).exists(), f"{t}/ 未被创建")

        print("[3] 幂等 + 清单按技能记录真实 mode")
        mf = tmp / ".claude" / "skills" / ".design-managed.json"
        data = json.loads(mf.read_text(encoding="utf-8"))
        check(set(data["managed"]) == exp, "清单 managed 与期望集合一致")
        check(all(v == "symlink" for v in data["modes"].values()),
              "清单 modes 逐技能记录 symlink")
        out = run(RECON, "--project", str(tmp), "--scan")
        check(all(c == (0, 0, 0) for c in counts(out)), f"幂等复跑全 0/0/0（{counts(out)}）")

        # ---- 5/6: 用户技能与旧包清单共存 ----
        print("[5/6] 用户自己的技能与 shuhe-role-skills 清单共存")
        own = tmp / ".claude" / "skills" / "my-own-skill"
        own.mkdir()
        (own / "SKILL.md").write_text("---\nname: my-own-skill\n---\n\n# mine\n", encoding="utf-8")
        (tmp / ".claude" / "skills" / ".roles-managed.json").write_text(
            json.dumps({"managed": ["product-designer"]}), encoding="utf-8")
        out = run(RECON, "--project", str(tmp), "--scan")
        check(own.is_dir(), "用户自己的技能未被删")
        check((tmp / ".claude" / "skills" / ".roles-managed.json").is_file(),
              ".roles-managed.json 未被删")
        check(all(c == (0, 0, 0) for c in counts(out)), "共存场景下依旧幂等")

        # ---- 4: 清孤儿（改工种集合）----
        print("[4] 改工种集合后清孤儿")
        run(RENDER, "--project", str(tmp), "--disciplines", "ui-design")
        out = run(RECON, "--project", str(tmp), "--scan")
        check(all(c[2] == 1 for c in counts(out)),
              f"3 个工具目录各移除 1 个孤儿（{counts(out)}）")
        for t in DETECTED:
            check(not (tmp / t / "skills" / "brand-design").exists(),
                  f"{t} 已清掉 brand-design 孤儿")
        check(own.is_dir(), "清孤儿时用户技能仍未被删")

        # ---- 8: artifacts 升级保护 ----
        print("[8] 升级重渲染后 artifacts/ 作品保留")
        art = tmp / ".design" / "artifacts" / "login-page"
        art.mkdir(parents=True)
        (art / "01-design-brief.md").write_text("# 我的设计稿\n", encoding="utf-8")
        run(RENDER, "--project", str(tmp), "--disciplines", "ui-design,illustration-design")
        check((art / "01-design-brief.md").is_file(),
              "重渲染后 artifacts/ 里的设计稿还在")
        check((tmp / ".design" / "skills" / "illustration-design").is_dir(),
              "新工种 illustration-design 已渲染")
        cfg = json.loads((tmp / ".design" / "design.json").read_text(encoding="utf-8"))
        check(cfg["disciplines"] == ["ui-design", "illustration-design"],
              "design.json 工种集合已更新")

        # ---- 7: copy 模式幂等不误报 ----
        print("[7] copy 模式幂等不误报（旧包 bug 回归）")
        run(RECON, "--project", str(tmp), "--tool-dir", ".codex/skills", "--mode", "copy")
        mf2 = tmp / ".codex" / "skills" / ".design-managed.json"
        modes2 = json.loads(mf2.read_text(encoding="utf-8"))["modes"]
        check(bool(modes2) and all(v == "copy" for v in modes2.values()),
              "copy 模式清单逐技能记为 copy")
        out = run(RECON, "--project", str(tmp), "--tool-dir", ".codex/skills", "--mode", "copy")
        modes3 = json.loads(mf2.read_text(encoding="utf-8"))["modes"]
        check(all(v == "copy" for v in modes3.values()),
              "copy 幂等复跑后仍记为 copy（不误报 symlink）")
        check(all(c == (0, 0, 0) for c in counts(out)), "copy 模式幂等复跑 0/0/0")

        print(f"\n结果：{passed} 项通过，{len(failed)} 项失败")
        if failed:
            for f in failed:
                print(f"  FAILED: {f}", file=sys.stderr)
            return 1
        print("✅ 多工具扫描安装回归测试全部通过")
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
