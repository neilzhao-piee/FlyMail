<div align="center">

# FlyMail 飞邮 · 社区增强版

**自托管多邮箱客户端（飞牛 fnOS）——本仓库是 1.0.7 Python 版的社区 fork**

[![Version](https://img.shields.io/badge/version-1.0.7%2Bcommunity-blue?style=flat-square)](VERSION)
[![License](https://img.shields.io/badge/license-GPL--3.0-green?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-yellow?style=flat-square&logo=python)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3-brightgreen?style=flat-square&logo=vue.js)](https://vuejs.org/)
[![Docker](https://img.shields.io/badge/Docker-self--host-2496ED?style=flat-square&logo=docker)](SELFHOST.md)

[中文](#中文) · [English](#english) · [自建部署](SELFHOST.md) · [改动清单](#相对上游-107-的改动)

</div>

---

## 中文

### 这是什么

FlyMail（飞邮）是一个自托管邮件客户端：把 Gmail、Outlook、QQ/163、iCloud、新浪等邮箱集中到一个界面，
邮件数据存在你自己的 NAS 上。本仓库是 **1.0.7（Python 3.11 + FastAPI + Vue 3）** 的社区 fork，
在上游基础上补齐了搜索、同步健壮性、归档控制和自建部署能力，并持续维护。

### 与飞牛应用商店「牛邮 2.0.2」的关系

| | 本仓库 | 商店版「牛邮」 |
|---|---|---|
| 版本 | 1.0.7 + 社区补丁 | 2.0.2 |
| 实现 | Python / FastAPI / Vue 3 / SQLite | Go（闭源，仅通过 fnOS 应用中心分发） |
| 维护 | 本 fork | 作者 `cliii_one` |
| 关系 | 独立代码线 | 与本仓库**没有代码继承关系** |

商店版功能更多，但源码未公开；本仓库选择在开源的 1.0.7 上继续演进——所有改动可审计、可自行构建、
可用 Docker 部署到任意 Linux/NAS。二者可以并存（不同端口、不同数据目录）。

> 上游与商标：原项目版权归 **DinDing1**，GPL-3.0。`FlyMail` / `飞邮` 是原作者的未注册商标，
> 本 fork 不暗示与原作者或商店版的关联，仅用于说明代码来源。

### 相对上游 1.0.7 的改动

**搜索**
- 新增 `cached_messages_fts`（SQLite **FTS5 + trigram**）：中文 ≥3 字可直接命中正文，英文大小写不敏感；
  短词（如「发票」）自动回退 LIKE，不会搜不到。
- 新增 `GET /api/search`：**跨账号、跨文件夹**检索，支持日期范围、`date|relevance` 排序、`<mark>` 高亮片段。
- 前端新增全局搜索（**Ctrl/⌘ + K**），点结果直接跳到对应账号/文件夹并打开邮件。

**同步健壮性**
- 批量 FETCH 遇到畸形邮件（典型：`BODYSTRUCTURE` 解析失败、`imapwire: expected '(', got "N"`）不再整批失败：
  自动退化为逐封拉取，坏邮件记录 UID + 原因后跳过，其余照常入库；同一封连续失败 3 次后不再重试。
- 分页拉取失败（如 Gmail 第 31 页解析报错）自动回退到 UID 分批。
- 新增 `GET /api/sync/failed` 查看被跳过的邮件。

**归档（.eml 备份）**
- 归档过程可**暂停 / 恢复**，并对外报告进度（总数、已完成、失败、封/分、预计剩余），
  不再「点了立即备份只能干等」。
- 归档时提取正文写入 `message_archive.body_text`，新增 `message_archive_fts`，
  备份搜索从「只能搜标题」升级为**可检索 .eml 正文**。
- 前端备份页显示进度条与暂停/继续按钮。

**部署与兼容**
- 新增 `HTTP_PORT`：可直接以 HTTP 方式运行（Docker/裸机），不必依赖飞牛网关。
- 新增 `Dockerfile` / `docker-compose.yml` / [`SELFHOST.md`](SELFHOST.md)。
- 修复 `FastAPI(tags_metadata=...)`（新版 FastAPI 启动即 TypeError）、
  Docker 下 UDS+HTTP 双实例导致的 `init_db` 并发竞态。
- 全量同步的分页大小/页数上限、批次间隔、失败重试次数都支持环境变量调整。

**邮箱支持**
- 内置 **139 / 189 / 搜狐 / 阿里云** 预设：添加账号时只填邮箱 + 授权码，服务器参数自动补全；
  `GET /api/accounts/presets` 可查询支持列表。

### 核心功能

- **多邮箱聚合**：混排展示、按时间统一排序、按邮箱筛选与身份标识
- **邮件收发**：纯文本 / HTML 富文本、附件、草稿、定时发送
- **实时同步**：IMAP IDLE 秒级推送，Poll 轮询兜底
- **本地归档**：`.eml` 落到指定目录，附件完整，服务器删了本地还在
- **全文搜索**：跨账号/文件夹，含正文与高亮片段
- **通知**：WebSocket + Bark / Telegram / Webhook 等第三方通道
- **联系人 / 签名 / 多用户隔离**（飞牛环境下按 NAS 用户隔离）
- **移动端适配**：响应式布局

### 支持的邮箱平台

| 平台 | 认证方式 | 实时同步 |
|---|---|---|
| Gmail | OAuth 2.0 / 应用专用密码 | IDLE |
| Outlook / Microsoft 365 | OAuth 2.0 | IDLE |
| QQ 邮箱 | 授权码 | IDLE |
| 网易（163 / 126 / yeah.net） | 授权码 | Poll |
| iCloud | 应用专用密码 | Poll |
| 新浪邮箱 | 授权码 | Poll |
| **139 / 189 / 搜狐 / 阿里云** | 授权码（内置预设） | Poll |
| 自定义 IMAP/SMTP | 账号密码 / 授权码 | Poll |

### 技术栈

| 层级 | 技术 |
|---|---|
| 前端 | Vue 3 + TypeScript + Pinia + Vite |
| 后端 | Python 3.11 + FastAPI + aiosqlite |
| 数据库 | SQLite（WAL）+ FTS5 全文索引 |
| 邮件协议 | IMAP（IDLE/Poll）+ SMTP |
| 实时通信 | WebSocket |
| 部署 | Docker / 飞牛应用中心（上游打包方式：Nuitka + fnpack） |

### 部署

**方式一：飞牛应用中心（商店版 2.0.2，非本仓库代码）**
适合只想开箱即用的用户；本仓库的改动不会出现在商店版里。

**方式二：Docker 自建（推荐，跑的是本仓库代码）**

```bash
git clone https://github.com/neilzhao-piee/FlyMail.git
cd FlyMail
docker compose up -d --build      # 或 docker build -t flymail:selfhost . && docker run ...
```

默认 `8080`（界面/API）、`51010`（OAuth 回调），数据卷 `./data`。
细节（环境变量、反代、鉴权）见 [`SELFHOST.md`](SELFHOST.md)。

> ⚠️ 自建模式没有飞牛网关注入 `X-Trim-Userid`，所有请求归到 `default` 用户，**不要直接暴露公网**。

**方式三：本地开发**

```bash
# 后端
cd backend && pip install -r requirements.txt
FLYMAIL_DATA_DIR=./data HTTP_PORT=8080 python main.py
# 前端
cd frontend && npm install && npm run dev
```

### 配置（环境变量）

| 变量 | 默认 | 说明 |
|---|---|---|
| `FLYMAIL_DATA_DIR` | `.` | 数据目录（SQLite、日志、索引） |
| `HTTP_PORT` / `HTTP_HOST` | `0` / `0.0.0.0` | 自建模式额外监听的 HTTP 端口（0=关闭） |
| `OAUTH_PORT` | `51010` | OAuth 回调端口 |
| `SOCKET_PATH` | `flymail.sock` | Unix Socket（飞牛网关使用） |
| `FLYMAIL_FULL_SYNC_PAGE_SIZE` | `500` | 全量同步每页 UID 数 |
| `FLYMAIL_FULL_SYNC_MAX_PAGES` | `40` | 全量同步页数上限（默认约 2 万封/文件夹，大邮箱可放大） |
| `FLYMAIL_MAX_FETCH_ATTEMPTS` | `3` | 单封失败重试上限，超过后跳过并记录 |
| `FLYMAIL_FETCH_BATCH_PAUSE_MS` | `0` | 每批之间主动让出毫秒数（限速用） |

### API 摘要

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/search` | 跨账号/文件夹搜索（`q`、`account_id`、`folder`、`date_from`、`date_to`、`sort`） |
| GET | `/api/search/status` | 全文索引是否可用 |
| GET | `/api/sync/failed` | 被跳过的坏邮件（UID + 错误） |
| GET | `/api/backup/progress` | 归档进度（done/total、速率、ETA） |
| POST | `/api/backup/pause` / `/api/backup/resume` | 暂停 / 恢复归档 |
| GET | `/api/backup/messages` | 归档检索（`q` 走归档 FTS，可搜正文） |
| GET | `/api/accounts/presets` | 内置邮箱服务商预设 |

### 测试

```bash
cd backend
pip install pytest pytest-asyncio
pytest -q          # 24 passed
```

前端：`npm run build`（含 `vue-tsc` 类型检查）。

### 已知限制

- **团队共享**尚未实现（1.0.7 数据模型没有团队概念，需要单独设计）。
- OAuth（Gmail/Outlook 网页登录）默认走原作者的 broker；用应用专用密码/授权码则不受影响。
- 自建模式是单用户（`default`），多用户隔离依赖飞牛网关。
- 尚未提供 fpk 打包；需要装进飞牛应用中心的话要另外打包。

### 路线图

- [ ] 团队共享（账号/联系人/归档的多人共享与权限）
- [ ] 自带 OAuth Client（不依赖第三方 broker）
- [ ] fpk 打包与一键升级
- [ ] 归档增量校验（.eml 与 DB 一致性巡检）

### 许可与致谢

- 许可证：**GPL-3.0**，沿用上游；派生作品需同样以 GPL-3.0 开源并保留原始版权声明。
- 原项目与版权：**DinDing1**（1.0.7）。
- 商店版「牛邮 2.0.2」由 `cliii_one` 发布，与本仓库无代码关系。
- `FlyMail™` / `飞邮™` 是 DinDing1 的未注册商标，详见下方「商标声明」。

### 商标声明

**FlyMail™ 和飞邮™ 是 DinDing1 的未注册商标。**

未经授权，不得在派生项目或相关宣传中使用 "FlyMail"、"飞邮" 名称或其变体来暗示与本项目的关联或背书。
本商标声明不限制 GPL-3.0 协议赋予你的代码使用、修改和分发权利，仅用于保护项目名称的识别性，防止混淆。

---

## English

### What is this

FlyMail is a self-hosted mail client that aggregates Gmail, Outlook, QQ/163, iCloud, Sina and other
mailboxes into one UI, storing all mail on your own NAS. **This repository is a community fork of the
1.0.7 release (Python 3.11 + FastAPI + Vue 3)**, adding search, sync resilience, archive controls and
self-hosted deployment on top of upstream.

### Relationship to the fnOS store build ("牛邮 2.0.2")

The "牛邮" app in the fnOS app store is a **separate closed-source Go implementation (2.0.2)** published
by `cliii_one`. It shares no code with this repository. This fork continues the open Python 1.0.7 line so
that everything stays auditable, buildable and deployable anywhere via Docker. Both can coexist on one NAS
(different ports and data directories).

Trademark note: `FlyMail` / `飞邮` are unregistered trademarks of the original author (DinDing1), GPL-3.0.
This fork does not imply endorsement by, or affiliation with, the original author or the store build.

### Changes over upstream 1.0.7

- **Search**: SQLite **FTS5 with trigram** tokenizer (CJK works from 3 characters; short terms fall back to
  LIKE), new cross-account/cross-folder `GET /api/search` with date filters, `date|relevance` sorting and
  `<mark>` snippets; global search UI (**Ctrl/⌘ + K**) that jumps straight to the message.
- **Sync resilience**: a malformed message (e.g. `BODYSTRUCTURE` parse failure) no longer aborts the whole
  folder — the batch degrades to per-message fetching, failures are recorded by UID and skipped, and are
  retried up to `FLYMAIL_MAX_FETCH_ATTEMPTS` times. Failed page fetches fall back to UID batches.
  `GET /api/sync/failed` lists skipped messages.
- **Archive controls**: pause/resume with live progress (done/total, rate, ETA); archive body text is
  indexed (`message_archive_fts`), so backup search can hit the `.eml` body, not just headers.
- **Self-hosted**: `HTTP_PORT` so the app serves plain HTTP (Docker/bare metal), `Dockerfile`,
  `docker-compose.yml` and [`SELFHOST.md`](SELFHOST.md). Fixed `FastAPI(tags_metadata=...)` (crashes on
  current FastAPI) and a double-lifespan `init_db` race under Docker.
- **Providers**: built-in presets for 139 / 189 / Sohu / Aliyun — enter email + auth code only.

### Deployment

- **fnOS app store**: the 2.0.2 Go build, *not* this repository's code.
- **Docker (recommended)**: `docker compose up -d --build`, ports `8080` / `51010`, data in `./data`.
  See [`SELFHOST.md`](SELFHOST.md). No fnOS gateway means a single `default` user — keep it behind a
  reverse proxy / private network.
- **Local dev**: `cd backend && pip install -r requirements.txt && FLYMAIL_DATA_DIR=./data HTTP_PORT=8080 python main.py`;
  `cd frontend && npm install && npm run dev`.

### Tests

`cd backend && pytest -q` → 24 passed. Frontend: `npm run build` (includes `vue-tsc` type-check).

### Limitations

- Team sharing is not implemented yet (1.0.7 has no team model).
- OAuth for Gmail/Outlook goes through the original author's broker by default; app passwords / auth codes
  are unaffected.
- Self-hosted mode is single-user (`default`); per-NAS-user isolation requires the fnOS gateway.
- No fpk packaging yet.

### Roadmap

- [ ] Team sharing (accounts / contacts / archives, with permissions)
- [ ] Bring-your-own OAuth client
- [ ] fpk packaging & one-click upgrade
- [ ] Archive consistency checks (.eml vs. DB)

### License

GPL-3.0, inherited from upstream. Original project and copyright: **DinDing1** (1.0.7). The fnOS store
build "牛邮 2.0.2" is published by `cliii_one` and is unrelated to this repository.
