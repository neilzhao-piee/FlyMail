# 自建部署（Docker）

飞牛应用中心里的版本是另一套闭源 Go 实现（2.0.2）；本仓库是 **1.0.7 Python 版**，
可以用下面的方式自建部署，不依赖飞牛应用中心。

## 快速开始

```bash
git clone git@github.com:<you>/FlyMail.git
cd FlyMail
docker compose up -d --build
```

打开 `http://<host>:8080` 即可（首次进入后添加邮箱账号）。

- 数据卷：`./data`（SQLite、日志、索引），备份这个目录即可
- OAuth 回调：`51010`（Gmail / Outlook 网页登录用；只用应用专用密码/授权码可不开）
- 前端已打进镜像（`backend/ui`），无需单独跑 node

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `FLYMAIL_DATA_DIR` | `/data` | 数据目录（SQLite + 日志） |
| `HTTP_PORT` | `8080` | 主应用 HTTP 端口（自建模式；飞牛应用内不设） |
| `HTTP_HOST` | `0.0.0.0` | 监听地址 |
| `OAUTH_PORT` | `51010` | OAuth 回调端口 |
| `SOCKET_PATH` | `/tmp/flymail.sock` | Unix Socket（飞牛网关使用；容器内保留无妨） |
| `FLYMAIL_FULL_SYNC_PAGE_SIZE` | `500` | 全量同步每页 UID 数 |
| `FLYMAIL_FULL_SYNC_MAX_PAGES` | `40` | 全量同步页数上限（默认约 2 万封/文件夹，大邮箱可放大） |
| `FLYMAIL_MAX_FETCH_ATTEMPTS` | `3` | 单封拉取失败重试上限，超过后跳过并记录到 `failed_messages` |
| `FLYMAIL_FETCH_BATCH_PAUSE_MS` | `0` | 每批之间的主动让出毫秒数（限速/省资源用） |

## 鉴权说明（重要）

自建模式没有飞牛网关，应用读不到 `X-Trim-Userid`，所有请求都会归到 `default` 用户，
**不要直接暴露到公网**。放到内网，或用带认证的反向代理：

```nginx
location /app/flymail/ {
    auth_basic "flymail";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://127.0.0.1:8080/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 3600;
}
```

## 数据库与索引

- `flymail.db`：账号、缓存、归档元数据、失败邮件表
- `cached_messages_fts`：FTS5 trigram 全文索引，随缓存自动维护；启动时只补缺失行
- 搜索接口：`GET /api/search?q=关键词&account_id=&folder=&date_from=&date_to=&sort=date|relevance`
  - 中文 ≥3 字走全文索引；更短的词自动回退 LIKE
  - 返回 `snippet` 带 `<mark>` 高亮
- 诊断接口：`GET /api/sync/failed` 查看被跳过的坏邮件

## 升级

```bash
git pull
docker compose up -d --build
```

数据卷不变，直接覆盖镜像即可。
