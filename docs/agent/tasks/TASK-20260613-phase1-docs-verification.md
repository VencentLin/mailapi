# TASK-20260613-phase1-docs-verification

Status: IN_PROGRESS
Owner: Claude
Created by: Codex
Created at: 2026-06-13

## 背景

第一阶段完成后，需要一份 README 告诉用户如何安装、测试、构建和运行 Docker 镜像，同时要记录完整验证结果。

## 目标

完成 `docs/superpowers/plans/2026-06-13-mailapi-phase-1-foundation.md` 中的 Task 5。

不新增业务功能。

## 修改范围

- `README.md`
- `Agent.md`
- `docs/development-workflow.md`
- `docs/development-workflow.zh-CN.md`

## 建议方案

按 Phase 1 plan 的 Task 5 执行：

- 添加 README。
- 跑完整 Phase 1 验证命令。
- 如果 Docker 不可用，要在完成记录里明确说明未运行 Docker build 的原因。
- 不要归档任务，除非用户确认第一阶段已验收。

## 测试建议

- `pytest tests/backend -v`
- `ruff check backend tests/backend`
- `cd frontend && npm run build`
- `python -m compileall backend`
- Docker 可用时：`docker build -t mailapi:phase1 .`

## 验收标准

1. README 覆盖后端测试、前端构建、Docker 构建和运行方式。
2. 完整验证命令和结果写入 Claude 完成记录。
3. 提交信息为 `docs: add phase 1 verification guide` 或同等清晰信息。

## 风险与回退

文档风险较低。若验证失败，不要标记 DONE，应改为 BLOCKED 并写清失败命令和输出摘要。

## Claude 完成记录

Status:
Summary:
Verification:
Notes:
