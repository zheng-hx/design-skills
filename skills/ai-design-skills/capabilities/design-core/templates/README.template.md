# 设计师共享工作台

> 由 `ai-design-skills` {{PACKAGE_VERSION}} 于 {{GENERATED_AT}} 生成。
> **作用域：`{{SCOPE}}`**　·　工作台路径：`{{WORKBENCH_SPEC}}`　·　共享资产根：`{{DESIGN_ROOT}}`
>
> 工作台只放**规则与技能**；AI 工具全局技能目录里的条目是注册产物（软链指向这里），随时可重新注册。
> **用户作品不在这里**，一律写当前项目的 `.design/artifacts/`。

## 本次启用的工种

`{{DISCIPLINE_MODE}}` 模式，共 {{SELECTED_COUNT}} 个：

```text
{{DISCIPLINE_LIST}}
```

> 完整工种清单（{{DISCIPLINE_COUNT}} 个）见 `{{DESIGN_ROOT}}/references/工种索引.md`。
> 想增删工种：重新执行 `/ai-design-skills`（初始化 / 更新步骤）。

## 目录

```text
{{WORKBENCH_SPEC}}/
├── design.json          # 版本 / 作用域 / 启用工种 / 工作台与产物路径
├── disciplines.json     # 全行业工种注册表（供运行时查询）
├── rules/               # 公共引擎 + 设计通用规范 + 人格
├── templates/           # 产物模板
├── references/          # 按需加载的深度参考
├── skills/              # 本次启用的工种技能（被各工具全局目录软链引用）
├── artifacts/           # 结构占位，不放作品
└── README.md

<当前项目>/.design/artifacts/   ← ⚠️ 你的作品在这里，按项目隔离，升级绝不覆盖
```

## 常用命令

| 场景 | 命令 |
|---|---|
| 不知道找哪个工种 / 跨工种 | `/design-router` |
| 明确的 core 工种 | `/<工种 key>`，如 `/ui-design`、`/brand-design` |
| 长尾工种（室内、建筑、Logo、印前…） | `/design-any` |
| 重新初始化 / 换工种 | `/ai-design-skills` |
| 技能没生效 / 换了 AI 工具 | `/ai-design-skills` |
| 更新版本 | `/ai-design-skills` |

## 升级契约

| 类别 | 路径 | 升级时 |
|---|---|---|
| 工作台管理区 | `rules/`、`templates/`、`references/`、`skills/`、`design.json`、`disciplines.json`、本文件 | 整体重建 |
| 用户作品 | **当前项目 `.design/artifacts/`** | **绝不覆盖、绝不删除** |
| 工具注册 | 各 AI 工具用户全局技能目录 | `--scan` 对账，多退少补 |

升级前旧工作台会备份到 `<工作台同级>/.design.bak`，成功后删除。
版本分流、拒绝降级等规则见 `/ai-design-skills`（更新步骤）。

