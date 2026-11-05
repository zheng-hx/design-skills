#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render-design-package.py — 把设计工种包渲染成共享工作台。

保留两条最有价值的纪律（源自上游改造经验）：
  · 渲染由脚本固化，**除 {{PLACEHOLDER}} 替换外源文件逐行逐字保真**，不符即退出；
  · 先在暂存树构建并跑结构校验，通过后才整体替换，用户作品绝不覆盖。

作用域（本包默认全局）：
  · `--scope user`（默认）→ 工作台 `~/.design/`，装一次所有项目都能用；
  · `--scope project`     → 工作台 `<项目>/.design/`，仅当前项目。
  两种作用域下**用户作品都写当前项目的 `.design/artifacts/`**，不进全局工作台，避免跨项目串稿。

其他：
  · 按 `--disciplines` 过滤工种子集（core / all / 逗号分隔的 key）；
  · 注入工作台占位符 `{{DESIGN_ROOT}}` 与注册表统计类占位符；
  · `disciplines.json` 逐字复制进工作台，供 router / design-any 运行时查询；
  · `--dry-run` 在系统暂存区渲染，**对目标项目与用户主目录零写入**。

用法:
    python3 render-design-package.py --project <目标项目根> \
        [--scope user|project] [--home <用户主目录>] \
        [--disciplines core|all|ui-design,brand-design] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
CAPS = SKILL_DIR / "capabilities"
REGISTRY = CAPS / "design-core" / "disciplines.json"
VERIFY = SKILL_DIR / "scripts" / "verify-render.py"

PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_]+\}\}")
ENTRY_SKILLS = ("design-router", "design-any")  # 与工种无关，始终渲染
PRESERVE = ("artifacts",)


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def package_version() -> str:
    vf = SKILL_DIR / "VERSION"
    return vf.read_text(encoding="utf-8").strip() if vf.is_file() else "unknown"


def resolve_selection(spec: str | None, cfg: dict, data: dict) -> tuple[list[str], str]:
    """返回（选中的工种 key 列表, 模式标签）。"""
    all_keys = [d["key"] for d in data["disciplines"]]
    core_keys = [d["key"] for d in data["disciplines"] if d["tier"] == "core"]

    if spec is None:
        saved = cfg.get("disciplines")
        if isinstance(saved, list) and saved:
            spec_saved = ",".join(saved)
            return [k for k in saved if k in all_keys], cfg.get("discipline_mode", "custom")
        return core_keys, "core"

    spec = spec.strip()
    if spec == "core":
        return core_keys, "core"
    if spec == "all":
        return all_keys, "all"
    keys = [k.strip() for k in spec.split(",") if k.strip()]
    unknown = [k for k in keys if k not in all_keys]
    if unknown:
        fail(f"未知工种 key: {', '.join(unknown)}；可用值见 .design/disciplines.json 或 --disciplines core|all")
    if not keys:
        fail("--disciplines 不能为空")
    return keys, "custom"


def main() -> None:
    ap = argparse.ArgumentParser(description="渲染设计工种包到共享工作台")
    ap.add_argument("--project", required=True, help="当前项目根目录（决定用户作品落盘位置）")
    ap.add_argument("--scope", choices=["user", "project"], default="user",
                    help="user=~/.design/ 全局工作台（默认）；project=<项目>/.design/")
    ap.add_argument("--home", default=None, help="覆盖用户主目录（测试用；也读 HOME 环境变量）")
    ap.add_argument("--disciplines", help="core | all | 逗号分隔工种 key；省略时读已有 design.json，否则默认 core")
    ap.add_argument("--dry-run", action="store_true", help="只渲染+校验，不写目标项目或用户主目录")
    args = ap.parse_args()

    ver = package_version()
    if ver == "unknown":
        fail("技能包不完整：缺少 skills/ai-design-skills/VERSION——无法确定版本，不继续")

    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    all_disciplines = data["disciplines"]
    core_keys = [d["key"] for d in all_disciplines if d["tier"] == "core"]
    extended_count = len(all_disciplines) - len(core_keys)

    project = Path(args.project).resolve()
    home = Path(args.home).resolve() if args.home else Path.home().resolve()
    scope = args.scope
    # 工作台：全局放用户主目录，项目级放项目内；产物目录始终按 project 落盘。
    dst = (home / ".design").resolve() if scope == "user" else (project / ".design").resolve()
    design_root_spec = "~/.design" if scope == "user" else ".design"
    cfg_path = dst / "design.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.is_file() else {}
    selected, mode = resolve_selection(args.disciplines, cfg, data)

    # 实际渲染的技能目录 = 选中列表里的 core 工种 + 两个入口技能
    selected_skills = [k for k in selected if k in core_keys] + list(ENTRY_SKILLS)

    ph = {
        "{{PACKAGE_VERSION}}": ver,
        "{{GENERATED_AT}}": date.today().isoformat(),
        # 工作台路径：共享资产按作用域定位；用户作品始终按当前工作目录落盘。
        "{{DESIGN_ROOT}}": design_root_spec,
        "{{SCOPE}}": scope,
        "{{WORKBENCH_SPEC}}": dst.as_posix(),
        "{{ARTIFACT_DIR}}": ".design/artifacts/",
        "{{DISCIPLINES_JSON}}": json.dumps(selected, ensure_ascii=False),
        "{{DISCIPLINE_MODE}}": mode,
        "{{SELECTED_COUNT}}": str(len(selected)),
        # 必须是单行：保真核对按行比对，占位符行展开成多行会误判为「内容被增删」。
        "{{DISCIPLINE_LIST}}": "、".join(
            d["key"] for d in all_disciplines if d["key"] in selected
        ),
        "{{DISCIPLINE_COUNT}}": str(len(all_disciplines)),
        "{{CORE_COUNT}}": str(len(core_keys)),
        "{{EXTENDED_COUNT}}": str(extended_count),
    }

    def render(text: str, where: str) -> str:
        for k, v in ph.items():
            text = text.replace(k, v)
        left = PLACEHOLDER_RE.findall(text)
        if left:
            fail(f"{where}: 占位符未替换 {left}")
        return text

    # 暂存树：dry-run 放系统暂存区（对目标项目零写入），正式渲染放项目内（同盘便于 rename）
    if args.dry_run:
        build = Path(tempfile.mkdtemp(prefix="ai-design-dryrun-"))
    else:
        build = Path(tempfile.mkdtemp(prefix=".design-build-", dir=str(project)))
    stage = build / ".design"
    stage.mkdir(parents=True)
    rendered: list[tuple[Path, Path]] = []

    def render_file(src: Path, out: Path) -> None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(src.read_text(encoding="utf-8"), str(src)), encoding="utf-8")
        rendered.append((src, out))

    try:
        # 0. 保留用户区
        if not args.dry_run:
            for name in PRESERVE:
                src = dst / name
                if src.exists():
                    if src.is_dir():
                        shutil.copytree(src, stage / name, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, stage / name)

        # 1. 配置：design.json 出到 .design/ 根，注册表逐字复制
        render_file(CAPS / "design-core/templates/design.json.tpl", stage / "design.json")
        shutil.copyfile(REGISTRY, stage / "disciplines.json")
        print("配置: design.json + disciplines.json")

        # 2. rules/：core 先写，工种层同名覆盖
        n = 0
        for sub in ("design-core/rules", "design-disciplines/rules"):
            d = CAPS / sub
            if not d.is_dir():
                continue
            for f in sorted(d.glob("*.md")):
                render_file(f, stage / "rules" / f.name)
                n += 1
        print(f"rules/: {n} 个")

        # 3. templates/ + README.md
        tdir = stage / "templates"
        tdir.mkdir(parents=True, exist_ok=True)
        n = 0
        for sub in ("design-core/templates", "design-disciplines/templates"):
            d = CAPS / sub
            if not d.is_dir():
                continue
            for f in sorted(d.glob("*.md.tpl")):
                out = (stage / "README.md") if f.name == "README.md.tpl" else (tdir / f.name[:-4])
                render_file(f, out)
                n += 1
        print(f"templates/: {n} 个")

        # 4. references/（也过占位符：索引里会写 {{DESIGN_ROOT}}，不能留未替换的字面量）
        rdir = stage / "references"
        rdir.mkdir(parents=True, exist_ok=True)
        n = 0
        for sub in ("design-core/references", "design-disciplines/references"):
            d = CAPS / sub
            if not d.is_dir():
                continue
            for f in sorted(d.glob("*.md")):
                render_file(f, rdir / f.name)
                n += 1
        print(f"references/: {n} 个")

        # 5. skills/：按选定工种过滤
        skills_src = CAPS / "design-disciplines" / "skills"
        if not skills_src.is_dir():
            fail(f"工种技能目录不存在: {skills_src}")
        for key in sorted(set(selected_skills)):
            sdir = skills_src / key
            if not sdir.is_dir():
                fail(f"选中工种缺少技能目录: {key}")
            out_dir = stage / "skills" / key
            (out_dir / "agents").mkdir(parents=True, exist_ok=True)
            render_file(sdir / "SKILL.md.tpl", out_dir / "SKILL.md")
            agents = sdir / "agents" / "openai.yaml.tpl"
            if agents.is_file():
                render_file(agents, out_dir / "agents" / "openai.yaml")
        print(f"skills/: {len(set(selected_skills))} 个（模式 {mode}，选中工种 {len(selected)}）")

        # 6. 工作台里的 artifacts/ 只是结构占位；用户作品写当前项目的 .design/artifacts/。
        artifacts = stage / "artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        (artifacts / ".gitkeep").touch()
        (stage / ".gitignore").write_text(
            "# 工作台管理区由 /ai-design-skills 生成；用户作品不在这里。\n"
            "# 作品在当前项目 .design/artifacts/，请勿把该目录加入忽略。\n",
            encoding="utf-8",
        )

        # 7. 保真核对
        checked = skipped = 0
        for src, out in rendered:
            rel = src.relative_to(CAPS)
            a_lines = src.read_text(encoding="utf-8").splitlines()
            b_lines = out.read_text(encoding="utf-8").splitlines()
            if len(a_lines) != len(b_lines):
                fail(f"保真核对失败: {rel} 行数 {len(a_lines)} -> {len(b_lines)}")
            for i, (a, b) in enumerate(zip(a_lines, b_lines), 1):
                if PLACEHOLDER_RE.search(a):
                    skipped += 1
                    continue
                if a != b:
                    fail(f"保真核对失败: {rel} 第 {i} 行被改动\n  源: {a}\n  渲染: {b}")
                checked += 1
        print(f"保真核对: {checked} 行逐字一致，{skipped} 行占位符已替换")

        # 8. 结构校验（在暂存树上跑）
        if VERIFY.is_file():
            print(f"结构校验: {VERIFY.name} --project（暂存树）")
            r = subprocess.run([sys.executable, str(VERIFY), "--project", str(build)])
            if r.returncode != 0:
                fail("结构校验未通过（见上）——.design/ 未改动，修复后重跑")
        else:
            print(f"警告: 未找到 {VERIFY}，跳过结构校验", file=sys.stderr)

        if args.dry_run:
            print(f"DRY-RUN OK（目标工作台 {dst} 与用户主目录均未写入）")
            return

        # 9. 校验通过 → 整体替换工作台（备份 + 工作台内 artifacts 保留）
        backup = dst.parent / ".design.bak"
        if backup.exists():
            shutil.rmtree(backup)
        if dst.exists():
            dst.rename(backup)
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            stage.rename(dst)
        except OSError:
            if backup.exists() and not dst.exists():
                backup.rename(dst)
            fail(f"跨卷移动失败：无法把暂存树落到 {dst}；请把工作台与项目放在同一卷，或改用 --scope project")
        if backup.exists():
            shutil.rmtree(backup)
        print(f"落盘: 工作台 {dst} 已整体替换（scope={scope}）")

        # 10. 用户作品目录始终按当前项目建，全局工作台不放作品
        art = project / ".design" / "artifacts"
        art.mkdir(parents=True, exist_ok=True)
        (art / ".gitkeep").touch()
        print(f"用户作品: {art}（按项目隔离，升级绝不覆盖）")
        print("下一步: 执行本技能的 ② 注册步骤，把工种技能注册到检测到的 AI 工具全局目录")
    finally:
        if build.exists():
            shutil.rmtree(build, ignore_errors=True)

    print("DONE")


if __name__ == "__main__":
    main()
