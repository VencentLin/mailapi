# MailAPI Agent 协作入口

## 协作方式

本项目采用“Codex 负责方案与任务拆解，Claude 负责按任务执行”的协作方式。

Codex 负责：

- 分析新需求、bug、技术风险和影响范围。
- 阅读现有文档与代码，形成设计方案。
- 把方案拆成清晰、可执行、可验收的 Claude 任务。
- 审查 Claude 完成记录，确认测试、风险和遗留问题。
- 在用户确认后更新任务索引、文档和后续计划。

Claude 负责：

- 优先阅读本文件，再打开当前任务文件。
- 严格按任务文件执行，不擅自扩大范围。
- 修改代码、运行测试、验证结果。
- 完成后把任务文件顶部 `Status: TODO` 或 `Status: IN_PROGRESS` 改为 `Status: DONE`。
- 在任务文件底部填写“Claude 完成记录”，写明修改摘要、验证命令和验证结果。

重要规则：

- Codex 默认不直接修改业务源码，除非用户明确授权或任务只涉及文档/流程维护。
- 如果用户直接要求 Codex 实现，Codex 可以执行，但仍需遵守当前项目文档、测试和提交规则。
- Claude 不要默认读取归档历史；只有需要追溯旧决策时再看 `docs/agent/archive/`。
- Claude 不要猜测用户意图；需求、凭据、部署环境或验收标准不清楚时，标记 `BLOCKED` 并说明缺口。
- 涉及 Outlook OAuth2、权限、token 加密、数据库迁移、Docker 部署的改动必须重点写清验证过程。
- 本机开发默认不使用 Docker；Claude 应直接运行 FastAPI、Vite、pytest、ruff 等本机命令。Docker 只用于最终服务器部署打包。

## 执行粒度与恢复规则

- 即使用户说“按任务列表执行”，Claude 也只执行当前第一个 `TODO` 或 `IN_PROGRESS` 任务，完成并提交后停止，等待下一次指令。
- 开始前必须先运行 `git status --short --branch`。如果已有未提交改动，先判断是否属于当前 `IN_PROGRESS` 任务；属于则继续，不属于则停止询问。
- 不要因为会话恢复而从头重做任务；先阅读当前任务文件的完成记录、中断记录和 git diff，再从未完成的 checkpoint 继续。
- 大任务必须按任务文件里的 checkpoint 执行。每完成一个 checkpoint，就运行对应验证；如果需要退出，先在任务文件底部写清“已完成到哪里、下一步做什么、是否有错误”。
- 不要一次连续执行多个活跃任务。只有当前任务 `DONE`、验证通过并提交后，下一次会话才开始下一个任务。

## Claude 读取顺序

1. 读本文件的“当前活跃任务”。
2. 打开对应的 `docs/agent/tasks/*.md`。
3. 阅读相关设计文档，优先看中文文档，必要时对照英文原文：
   - `docs/superpowers/specs/2026-06-13-mailapi-design.zh-CN.md`
   - `docs/superpowers/specs/2026-06-13-mailapi-design.md`
4. 按任务文件执行，过程中只读取必要文件。
5. 完成任务后，把任务文件状态改为 `DONE`。
6. 在任务文件底部填写“Claude 完成记录”。
7. 如任务完成且用户确认，可移动到 `docs/agent/archive/YYYY-MM/`。

## 当前活跃任务

| ID | 状态 | 负责人 | 任务文件 |
|---|---|---|---|
| TASK-20260613-phase2-cloud-db-config | DONE | Claude | `docs/agent/tasks/TASK-20260613-phase2-cloud-db-config.md` |
| TASK-20260613-phase2-auth-backend | DONE | Claude | `docs/agent/tasks/TASK-20260613-phase2-auth-backend.md` |
| TASK-20260613-phase2-frontend-login-guard | TODO | Claude | `docs/agent/tasks/TASK-20260613-phase2-frontend-login-guard.md` |
| TASK-20260613-phase2-management-navigation | TODO | Claude | `docs/agent/tasks/TASK-20260613-phase2-management-navigation.md` |
| TASK-20260613-phase2-user-management | TODO | Claude | `docs/agent/tasks/TASK-20260613-phase2-user-management.md` |

## 状态约定

- `TODO`：等待 Claude 执行。
- `IN_PROGRESS`：Claude 正在执行。
- `BLOCKED`：Claude 被阻塞，需要用户或 Codex 补充信息。
- `DONE`：Claude 已完成，并写明验证结果。
- `ARCHIVED`：任务已确认完成并归档。

## 文件大小规则

- `Agent.md` 只保留协作规则和活跃任务索引，目标控制在 150 行以内。
- 每个需求、bug 或阶段任务单独一个任务文件。
- 当前活跃任务最多保留 5 个。
- 已完成并确认的任务移动到 `docs/agent/archive/YYYY-MM/`。
- 长期设计与背景资料放到 `docs/superpowers/specs/` 或其他专门文档，不堆在 `Agent.md`。

## Git 与回退规则

- 默认使用轻量流程：每个完成任务保留清晰 commit。
- 小任务可直接在 `main` 上提交。
- 大任务、高风险任务、实验任务先创建独立分支。
- 只有用户明确要求，或涉及数据库迁移、登录权限、token 加密、部署等高风险内容时，才需要 PR。
- 每次任务完成后必须说明验证命令和结果，方便出问题时按 commit 回退。

## 新任务模板

新任务请放到：

```text
docs/agent/tasks/TASK-YYYYMMDD-short-name.md
```

任务文件模板：

```md
# TASK-YYYYMMDD-short-name

Status: TODO
Owner: Claude
Created by: Codex
Created at: YYYY-MM-DD

## 背景

说明问题或需求。

## 目标

明确要完成什么，以及不做什么。

## 修改范围

- `path/to/file.py`

## 建议方案

给出具体改法、关键边界和注意事项。

## 测试建议

列出必须覆盖的测试或手工验证。

## 验收标准

1. ...

## 风险与回退

说明潜在风险，以及如果出问题如何回退。

## Claude 完成记录

Status:
Summary:
Verification:
Notes:
```
