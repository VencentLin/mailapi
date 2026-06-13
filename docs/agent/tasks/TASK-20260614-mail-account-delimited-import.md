# TASK-20260614-mail-account-delimited-import

Status: DONE
Owner: Codex
Created by: Codex
Created at: 2026-06-14

## 背景

用户后续邮箱凭据来源格式为：

```text
邮箱----密码----客户端ID----刷新令牌
```

真实样例包含敏感密码和 refresh token，不能写入文档、代码、测试或 git 历史。

## 完成内容

- 新增 `POST /api/mail-accounts/import`。
- 每行使用 `split("----", 3)` 解析，确保 refresh token 后续内容不被误切。
- 密码字段仅用于兼容格式解析，不落库、不返回、不写日志。
- 普通用户导入到自己名下；管理员可选择导入到用户或公共池。
- 已存在邮箱和同批重复邮箱跳过；格式错误或邮箱无效逐行返回失败。
- 前端邮箱管理页新增“批量导入”弹窗和导入结果表。
- README 增加导入格式说明。

## 验证结果

- `.venv\Scripts\python.exe -m pytest tests/backend/test_mail_accounts_api.py -v`：11 passed。
- `.venv\Scripts\ruff.exe check backend tests/backend`：All checks passed。
- `cd frontend && npm run build`：构建成功；保留 Vite 对依赖 PURE 注释和大 chunk 的 warning。
