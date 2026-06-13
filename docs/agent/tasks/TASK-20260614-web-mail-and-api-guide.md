# TASK-20260614-web-mail-and-api-guide

Status: DONE
Owner: Codex
Created by: Codex
Created at: 2026-06-14

## 背景

用户需要在网页端直接查看邮件列表，不只做验证码取件测试；同时需要在前端提供 API 使用说明，方便复制调用示例。

## 完成内容

- 新增前端邮件取件 API 封装：`/api/mail_new`、`/api/mail_all`。
- 新增“网页取件”页面：
  - 可选择已托管邮箱，也可手动输入临时 `client_id` 和 `refresh_token`。
  - 支持 `INBOX` / `Junk`。
  - 支持最新一封和邮件列表模式。
  - 展示协议、邮箱状态、Trace ID、邮件数量。
  - 邮件表格可展开查看纯文本正文预览。
- 新增“API 使用说明”页面：
  - API Key 请求头示例。
  - body `user_token` 示例。
  - `/api/mail_new`、`/api/mail_all`、`/api/verification-code`。
  - `/api/mail-accounts/import` 批量导入格式。
  - `/api/process-mailbox` 清空邮箱示例，并标注风险。
- 更新前端菜单和路由。

## 验证结果

- `cd frontend && npm run build`：构建成功；保留 Vite 对依赖 PURE 注释和大 chunk 的 warning。
