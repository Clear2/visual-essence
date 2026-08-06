# Visual Essence

[English](README.md) | [简体中文](README_zh.md)

[开源许可](LICENSE) · [更新记录](CHANGELOG.md) · [参与贡献](CONTRIBUTING.md) · [安全策略](SECURITY.md)

输入一个公开的抖音分享链接，获取结构化的视频内容。Visual Essence 会读取公开元数据、转写视频语音，并让 LLM 基于转写文本生成私教解读。

## 第一版能力

- 参考 Sitor 安静、聚焦的交互方式，并建立独立的 Visual Essence 视觉风格
- 支持直接粘贴抖音 URL，也支持粘贴整段分享文案
- 支持通过 `modal_id` 指定视频的抖音精选链接，例如
  `https://www.douyin.com/jingxuan?modal_id=...`
- FastAPI 提取接口会安全解析跳转，并归一化公开页面元数据
- 当公开分享页缺少完整视频状态时，使用固定版本的
  `jiji262/douyin-downloader` 详情适配器作为兜底
- 采用与上游一致的最高画质/无水印媒体选择策略，签名源地址仍只保留在后端播放代理内部
- 提交链接时先创建持久化对话，结果地址只包含不透明的对话 ID（`/result?id=...`），不会暴露抖音链接
- 跳转后立即进入三栏对话工作台，不经过中间加载页；助手消息和右侧路线会实时更新，分析完成后才出现可点击的“查看私教解读”
- 分析完成后可在底部继续提问；回答只使用已保存的视频转写和最近对话作为上下文；刷新或重新打开已完成会话时会直接恢复视频结果和消息，不会重新开始提取
- 提供固定底部输入框、桌面侧栏折叠，以及移动端会话与路线抽屉
- 后端实时推送公开推理记录：根据本次请求实际展示观察、工具调用、策略调整、警告与结果；当前说明会随执行逐字出现，并携带耗时、媒体字节数、转写长度和 LLM 结果数量等安全证据，不预设固定步骤总数，也不展示模型隐藏推理
- 视频结果卡片提供“查看私教解读”入口，点击后在当前页面右侧直接播放视频，并展示以语音转写为依据的 LLM 总结、关键点和思考问题
- 音轨提取后可选择 OpenAI 兼容的语音转写接口或本地 `whisper-cli`，再通过 LangChain 单次调用模型；模型使用文档约定的 `models[]` 配置结构
- 语音转写或 LLM 失败时明确降级为仅返回元数据，不会拿视频标题冒充真实内容总结
- 后端播放代理支持浏览器 Range 请求，不向前端暴露抖音 CDN 的签名地址；首个媒体地址必须属于白名单中的抖音 CDN，后续 HTTPS CDN 跳转也会逐跳执行公网地址与 SSRF 校验；遇到不安全或不可达的 PCDN 分配时，会从可信初始地址最多切换五条媒体线路
- Bilibili 和 YouTube 作为后续平台展示

## 技术栈

- 前端：Next.js 16、React 19、TypeScript、Tailwind CSS 4
- UI：Tailwind CSS、Lucide 图标和无障碍原生控件
- AI：LangChain、OpenAI 兼容聊天模型与转写模型
- 后端：Python 3.12+、FastAPI、HTTPX、Pydantic、
  `jiji262/douyin-downloader`

## 当前状态

抖音提取与内容分析流程已经打通前后端，支持视频直链、短链接、整段分享文案和精选页 `modal_id` 链接。公开分享页解析仍是主路径；固定版本的 `douyin-downloader` 详情客户端只作为隔离的兜底能力。配置视频分析后，后端会提取音轨、转写语音，并只根据转写文本生成 LLM 解读。上游项目的浏览器 Cookie 抓取、批量下载和数据库功能均未启用。

## 项目架构

```text
visual-essence/
├── frontend/                  # Next.js App Router 应用（端口 3000）
│   ├── src/app/               # 页面与布局
│   │   └── result/            # 独立的视频提取结果路由
│   ├── src/components/        # 交互组件
│   └── src/core/              # URL 规则与类型安全的后端客户端
└── backend/                   # FastAPI 应用（端口 8000）
    ├── app/gateway/           # 应用工厂、依赖与 HTTP 路由
    ├── app/videos/            # 内容提取、播放代理、语音转写与 LLM 分析
    └── tests/                 # Gateway 与提取模块测试
```

## 环境要求

- Node.js 22+
- pnpm 10.26.2+
- Python 3.12+
- uv

## 本地开发

在仓库根目录安装前后端依赖：

```bash
make install
```

使用 `make dev` 可同时启动前后端，也可以分别启动：

前端：

```bash
cd frontend
pnpm install
pnpm dev
```

后端：

```bash
cd backend
uv sync
make dev
```

视频分析默认关闭，需要显式配置。复制仓库根目录的模板，通过环境变量提供密钥，然后重启后端：

```bash
cp config.example.yaml config.yaml
export OPENAI_API_KEY="your-api-key"
cd backend
make dev
```

配置文件使用 `config.example.yaml` 记录的 `models[]` 模型注册结构。如果要复用已有的兼容配置而不复制凭据，可设置 `VISUAL_ESSENCE_CONFIG_PATH=/配置文件的绝对路径`；配置中存在多个模型时，可通过 `VISUAL_ESSENCE_LLM_MODEL_NAME` 选择模型。

若使用本地转写，请安装 `ffmpeg` 与 `whisper-cli`、下载 whisper.cpp 模型，并在已被 Git 忽略的 `config.yaml` 中设置：

```yaml
video_analysis:
  enabled: true
  transcription_provider: local_whisper
  whisper_cli_path: whisper-cli
  whisper_model_path: $WHISPER_MODEL_PATH
  whisper_language: zh
```

默认的 `openai` 转写方式使用 `transcription_api_url`、`transcription_api_key` 和 `transcription_model`。不要提交真实的 `config.yaml` 或 API Key。

如果后端不在默认地址运行，可复制前端环境变量模板：

```bash
cp frontend/.env.example frontend/.env.local
```

前端默认使用 `3000` 端口，后端默认使用 `8000` 端口。OpenAPI 文档位于 `http://localhost:8000/docs`。

创建 Pull Request 前，请运行与 CI 相同的完整检查：

```bash
make check
```

## API

```http
POST /api/videos/extract
Content-Type: application/json

{
  "url": "https://www.douyin.com/jingxuan?modal_id=7667128493197192313"
}
```

接口既接受直接的抖音链接，也接受包含链接的整段分享文案，并识别 `modal_id`。后端只读取公开元数据，并在每次跳转前重新校验目标地址。公开页面状态不完整时，后端可使用固定版本的上游详情客户端和空的、未登录 Cookie 集合进行读取，不会自动抓取浏览器 Cookie。`POST /api/conversations` 会先创建本地持久化对话，`POST /api/conversations/{id}/extract/stream` 再以 NDJSON 实时推送本次实际发生的动态活动。每条活动包含 `kind`、`status`、`elapsed_ms` 和安全的结构化 `data`；运行中的活动会在完成或转为警告时原位更新。完整分析成功后，响应状态为 `status: "analyzed"`，并返回 `transcript` 和 `coach_interpretation`（包含 `summary`、`key_points`、`questions`）。分析失败时仍会返回元数据和明确警告，不会伪造内容解读。

`POST /api/conversations/{id}/messages` 用于继续提问，`GET /api/conversations/{id}` 用于同时恢复已经持久化的视频结果以及用户与助手消息。

## 后续计划

- 平台提供字幕时，支持直接提取字幕轨道
- 支持 Bilibili
- 支持 YouTube

## 参与贡献与开源许可

欢迎参与贡献。创建 Pull Request 前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)，安全问题请按照 [SECURITY.md](SECURITY.md) 私下报告。Visual Essence 使用 [MIT License](LICENSE) 开源。
