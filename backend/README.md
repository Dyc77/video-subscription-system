# VideoHub - AI 影音摘要平台 API

基于 FastAPI 构建的 YouTube 影片摘要平台后端服务

## 项目特点

- **全域监测模式**: 频道和影片为全域共用资产，非个人化订阅
- **零成本监测**: 使用 RSS XML 解析，完全不依赖 YouTube API
- **按需生成摘要**: On-Demand 模式，只在用户首次点击时调用 Gemini API
- **智能缓存**: 摘要生成后永久缓存，避免重复调用 API
- **Google 登录**: 支持 Google OAuth 2.0 快速登录，无需注册
- **JWT 认证**: 安全的 Token 认证机制，防止用户伪造

## 技术栈

- **框架**: FastAPI
- **数据库**: MySQL + SQLAlchemy ORM
- **认证**: JWT + Google OAuth 2.0
- **AI**: Google Gemini 1.5 Flash
- **调度**: APScheduler (每15分钟扫描一次频道)
- **字幕**: youtube-transcript-api

## 项目结构

```
backend/
├── app/
│   ├── api/              # API 路由
│   │   ├── video.py      # 影片相关 API
│   │   ├── channel.py    # 频道相关 API
│   │   └── user.py       # 用户相关 API
│   ├── core/             # 核心配置
│   │   └── config.py     # 环境变量配置
│   ├── db/               # 数据库
│   │   ├── database.py   # 数据库连接
│   │   └── init_db.py    # 数据库初始化脚本
│   ├── models/           # 数据模型
│   │   ├── models.py     # SQLAlchemy 模型
│   │   └── schemas.py    # Pydantic 模型
│   ├── services/         # 业务逻辑
│   │   ├── watcher_service.py    # RSS 监测爬虫 (The Watcher)
│   │   ├── summary_service.py    # 摘要生成服务 (The Brain)
│   │   ├── gemini_service.py     # Gemini API 集成
│   │   └── youtube_service.py    # YouTube 字幕获取
│   ├── utils/            # 工具类
│   │   └── scheduler.py  # 定时任务调度器
│   └── main.py           # 主应用入口
├── requirements.txt      # Python 依赖
├── .env.example          # 环境变量示例
└── README.md             # 本文档
```

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置:

```bash
cp .env.example .env
```

编辑 `.env` 文件:

```env
# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=videohub

# Google Gemini API Key
GOOGLE_API_KEY=your_gemini_api_key_here
```

### 3. 初始化数据库

```bash
# 创建数据库表
python -m app.db.init_db

# 如需删除所有表重建 (谨慎!)
python -m app.db.init_db --drop
```

### 4. 启动服务

```bash
# 开发模式 (自动重载)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 或使用 Python 直接运行
python -m app.main
```

服务启动后访问:
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

## API 端点

### 认证相关

#### POST /api/auth/login
用户登录，获取 JWT token

**请求体** (form-data):
```
username: user@example.com
password: password123
```

**响应**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### GET /api/auth/me
获取当前用户信息

**Headers**:
```
Authorization: Bearer {JWT_TOKEN}
```

### 影片相关

#### POST /api/video/summary
生成影片摘要 (需要 Premium 会员权限)

**安全性**: user_id 从 JWT token 中解析，不从前端传入

**Headers**:
```
Authorization: Bearer {JWT_TOKEN}
```

**请求体**:
```json
{
  "video_id": "dQw4w9WgXcQ"
}
```

**响应**:
```json
{
  "video_id": "dQw4w9WgXcQ",
  "summary_status": 2,
  "summary_content": "## 📝 一句話總結\n...",
  "message": "摘要生成完成",
  "estimated_wait_seconds": 0
}
```

#### GET /api/video/list
获取用户订阅频道的影片列表

使用 `vw_uservideolibrary` 视图，性能优化

**Headers**:
```
Authorization: Bearer {JWT_TOKEN}
```

**查询参数**:
- `limit`: 返回数量限制 (默认50)
- `offset`: 分页偏移量 (默认0)

**状态码**:
- `summary_status = 0`: 未生成
- `summary_status = 1`: 处理中
- `summary_status = 2`: 完成

### 频道相关

#### GET /api/channel/list
获取频道列表

**查询参数**:
- `status` (可选): 0=停用, 1=启用

#### GET /api/channel/{channel_id}
获取单个频道信息

### 用户相关

#### GET /api/user/{user_id}
获取用户信息

#### POST /api/user/{user_id}/subscribe
订阅频道

**请求体**:
```json
{
  "channel_id": "UC_x5XG1OV2P6uZZ5FSM9Ttw"
}
```

#### DELETE /api/user/{user_id}/subscribe/{channel_id}
取消订阅频道

#### GET /api/user/{user_id}/subscriptions
获取用户订阅列表

## 核心模块说明

### The Watcher (监测爬虫)

- **功能**: 定时扫描所有启用频道的 RSS feed
- **频率**: 每 15 分钟执行一次
- **工作流程**:
  1. 读取 `tb_YoutubeChannel` 中 `channel_status = 1` 的频道
  2. 解析每个频道的 `rss_url`
  3. 比对 `video_id` 是否已存在
  4. 新影片写入数据库，`summary_status = 0`
- **特点**: 零 API 成本，不抓取字幕

### The Brain (摘要生成)

- **功能**: 按需生成影片摘要
- **触发**: 用户点击"生成摘要"按钮
- **工作流程**:
  1. 权限检查 (Premium 会员才能使用)
  2. 状态检查 (Race Condition 处理)
  3. 获取字幕 → 调用 Gemini → 存储摘要
- **特点**: 支持并发请求锁定，避免重复调用

## 定时任务

系统使用 APScheduler 管理定时任务:

- **任务名称**: scan_channels
- **执行频率**: 每 15 分钟
- **任务内容**: 扫描所有频道的新影片
- **日志**: 记录扫描结果和新发现的影片数量

## 数据库模型

### tb_User
用户表

### tb_YoutubeChannel
频道表 (全域共用)

### tb_YoutubeVideo
影片表 (全域共用)
- `summary_status`: 0=未生成, 1=处理中, 2=完成
- `summary_content`: Markdown 格式摘要

### tb_UserSubscription
用户订阅关系表 (多对多)

## 开发注意事项

### 环境变量

所有敏感信息都应该在 `.env` 文件中配置，不要硬编码在代码中。

### 日志

系统使用 Python logging 模块记录日志:
- INFO: 正常操作日志
- WARNING: 警告信息
- ERROR: 错误信息

### CORS

开发环境允许所有来源，生产环境需要在 `main.py` 中修改 CORS 配置。

## 部署建议

### 生产环境配置

1. 设置 `DEBUG=False`
2. 配置正确的 CORS 允许域名
3. 使用强密码和 SECRET_KEY
4. 启用 HTTPS
5. 使用 Gunicorn + Nginx 部署

### 启动命令 (生产)

```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

## 常见问题

### Q: 如何添加新频道？
A: 需要先在数据库中插入频道信息，包括 `channel_id` 和 `rss_url`。RSS URL 格式:
```
https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}
```

### Q: 为什么摘要生成失败？
A: 可能原因:
1. 影片没有字幕
2. Gemini API Key 无效
3. 网络连接问题
4. 用户非 Premium 会员

### Q: 如何手动触发一次频道扫描？
A: 可以直接调用:
```python
from app.db.database import SessionLocal
from app.services.watcher_service import WatcherService

db = SessionLocal()
watcher = WatcherService(db)
watcher.scan_all_channels()
db.close()
```

## License

MIT License
