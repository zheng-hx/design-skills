---
role: design
feature: <feature slug>
artifact: component-spec
status: draft
version: v0.1
created: <日期>
---

**创建日期：** {{GENERATED_AT}}　·　**版本：** v0.1

# 组件规格 — <特性名>

> 每个组件写到**尺寸 · 变体 · 状态**，可直接开发。

| 组件 | 尺寸 | 变体 | 间距 / 圆角 | 状态 |
|---|---|---|---|---|
| 输入框 | | | | default / focus / error / disabled / readonly |
| 主按钮 | | | | default / hover / active / loading / disabled |
| 次要按钮 | | | | |
| 链接 | | | | default / hover / visited / focus |
| 错误提示 | | | | inline / summary |
| 验证码 | | | | idle / sending / countdown / error |

## 状态覆盖（全局）
loading / error / empty / disabled / success / 网络异常 / 超长内容

## 交互反馈时限
| 档位 | 时限 | 表现 |
|---|---|---|
| 即时 | ≤100ms | |
| 常规 | ≤1s | |
| 长任务 | ≤10s | |
