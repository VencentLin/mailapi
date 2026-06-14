# 宝塔 Docker + Nginx 部署说明

## 部署结构

- Docker 容器：运行 MailAPI 后端、前端静态页面、容器内 Redis。
- 容器端口：`8000`。
- 服务器绑定：`127.0.0.1:8000`，不直接暴露公网。
- 宝塔 Nginx：对外绑定 `mail.example.com`，反向代理到 `http://127.0.0.1:8000`。

这个项目已经把前后端打进同一个镜像。浏览器访问 `/` 时返回前端页面，访问 `/api/*` 和 `/auth/*` 时进入后端接口，所以宝塔里只需要配置一个反向代理。

## 服务器 `.env`

服务器项目目录里需要放 `.env`。关键配置如下：

```env
DATABASE_URL=postgresql+asyncpg://mailapi:你的密码@DB_HOST:DB_PORT/mailapi
REDIS_URL=redis://127.0.0.1:6379/0
RUN_MIGRATIONS=true

MICROSOFT_OAUTH_CLIENT_ID=你的 Microsoft 应用 Client ID
MICROSOFT_OAUTH_CLIENT_SECRET=
MICROSOFT_OAUTH_REDIRECT_URI=https://mail.example.com/api/oauth/microsoft/callback
MICROSOFT_OAUTH_SCOPES=offline_access User.Read Mail.Read
MICROSOFT_OAUTH_TENANT=consumers
MICROSOFT_OAUTH_PROMPT=select_account

SECRET_KEY=请换成长随机字符串
TOKEN_ENCRYPTION_KEY=必须和旧环境保持一致，否则旧 refresh token 无法解密
```

`MICROSOFT_OAUTH_REDIRECT_URI` 必须和 Microsoft 应用后台里配置的回调地址完全一致。

## Docker 启动

在服务器项目目录执行：

```bash
docker compose up -d --build
```

查看状态：

```bash
docker compose ps
docker compose logs -f mailapi
```

健康检查：

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/health/db
```

## 宝塔 Nginx 反向代理

宝塔面板操作：

1. 网站 -> 添加站点，域名填 `mail.example.com`。
2. 给站点申请并启用 SSL。
3. 进入站点设置 -> 反向代理。
4. 添加反向代理：
   - 代理名称：`mailapi`
   - 目标 URL：`http://127.0.0.1:8000`
   - 发送域名：`$host`
   - 开启 WebSocket 可选。

如果需要手动写 Nginx 配置，可用：

```nginx
server {
    listen 80;
    server_name mail.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name mail.example.com;

    # 宝塔通常会自动生成 ssl_certificate / ssl_certificate_key。

    client_max_body_size 20m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

## Microsoft 应用回调地址

Microsoft Azure 应用注册中添加：

```text
https://mail.example.com/api/oauth/microsoft/callback
```

权限建议包含：

```text
offline_access
User.Read
Mail.Read
```

## 更新版本

拉取新代码后执行：

```bash
docker compose up -d --build
docker compose logs -f mailapi
```

如果迁移失败，先查看日志，不要直接删库：

```bash
docker compose logs mailapi
```
