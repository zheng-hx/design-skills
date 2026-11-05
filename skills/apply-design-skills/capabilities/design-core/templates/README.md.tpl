# .design — 设计师工作区

> 由 `ai-design-skills` {{PACKAGE_VERSION}} 于 {{GENERATED_AT}} 生成。
> 本目录是**项目资产**（可提交、可评审、可版本化）；AI 工具目录里的技能是**注册产物**，随时可重新注册。

## 本次启用的工种

`{{DISCIPLINE_MODE}}` 模式，共 {{SELECTED_COUNT}} 个：

```text
{{DISCIPLINE_LIST}}
```

> 完整工种清单（{{DISCIPLINE_COUNT}} 个）见 `references/工种索引.md`。
> 想增删工种：重新执行 `/apply-design-skills`，或改 `design.json` 后由 `/update-design-skills` 重渲染。

## 目录

```text
.design/
├── design.json          # 配置：版本 / 启用工种 / 产物目录
├── disciplines.json     # 全行业工种注册表（供运行时查询）
├── rules/               # 公共引擎 + 设计通用规范 + 人格（工种包级）
├── templates/           # 产物模板
├── references/          # 按需加载的深度参考
├── skills/              # 本次启用的工种技能
├── artifacts/           # ⚠️ 你的作品，升级时绝不覆盖
└── README.md
```

## 常用命令

| 场景 | 命令 |
|---|---|
| 不知道找哪个工种 / 跨工种 | `/design-router` |
| 明确的 core 工种 | `/<工种 key>`，如 `/ui-design`、`/brand-design` |
| 长尾工种（室内、建筑、Logo、印前…） | `/design-any` |
| 自动推进流水线 | 见 `rules/循环引擎.md` |

## 升级契约

| 类别 | 路径 | 升级时 |
|---|---|---|
| 管理区 | `rules/`、`templates/`、`references/`、`skills/`、`design.json`、`disciplines.json`、本文件 | 整体重建 |
| 用户区 | **`artifacts/`** | **绝不覆盖、绝不删除** |

升级前旧目录会备份到 `.design.bak/`，成功后删除。
版本分流、拒绝降级等规则见 `/update-design-skills`。

## 与 shuhe-role-skills 共存

本包用 `.design/`，角色技能包用另一套独立目录，两者互不覆盖，可在同一项目同时安装。
注册到 AI 工具时各自维护自己的清单文件（本包是 `.design-managed.json`），互不清理对方的注册项。
