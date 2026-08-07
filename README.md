# Visual Essence

[English](README.md) | [简体中文](README_zh.md)

[License](LICENSE) · [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

Enter a public Douyin share URL to extract structured video content. Visual
Essence reads the public metadata, transcribes the video's speech, and asks an
LLM to produce a transcript-grounded personal-coach interpretation.

## First release

- A responsive landing page with a quiet, focused interaction style and an
  original Visual Essence identity
- Douyin URL validation for both direct URLs and full copied share text
- Support for Douyin Selected links that carry a video in `modal_id`, such as
  `https://www.douyin.com/jingxuan?modal_id=...`
- A FastAPI extraction endpoint that safely resolves redirects and normalizes
  public page metadata
- A pinned `jiji262/douyin-downloader` detail adapter used as a fallback when a
  public share page does not contain complete video state
- Upstream-compatible highest-quality/no-watermark media selection, while the
  signed source remains private behind the playback proxy
- A persisted conversation is created before navigation, so result URLs contain
  only an opaque conversation ID (`/result?id=...`) and never the Douyin URL
- The `/result` route opens the three-column conversation workspace immediately;
  the assistant message and right content context update live until the coach
  interpretation becomes available
- After analysis, the composer supports persistent follow-up questions. Answers
  use the saved transcript and recent turns as context, and explicitly decline
  questions the video does not contain enough information to answer. Reopening
  or refreshing a completed conversation restores the saved video and turns
  directly instead of starting extraction again
- A fixed conversation composer, collapsible desktop navigation, and mobile
  drawers for the session list and content context
- A single public-reasoning narrative streams only backend-reported activity in
  execution order. Running activity is replaced in place when it completes,
  the finished interpretation adds a transcript-grounded content thesis, and
  the UI never invents connective claims from event labels or arbitrary data.
  Raw step counts, timings, pipeline cards, and private hidden reasoning are not
  presented as part of the conversation
- Reaching the end of that narrative is a terminal state, not automatically a
  success state. Only a response with both transcript-grounded analysis fields
  is labeled complete; metadata-only termination is labeled “analysis
  incomplete” and exposes its reason instead of a coach interpretation
- A “View personal-coach interpretation” action that opens an in-page side
  panel with direct video playback, an LLM summary, key points, and reflection
  questions grounded in the speech transcript
- Audio extraction followed by either an OpenAI-compatible transcription API or
  a local `whisper-cli`, then a one-shot LangChain model call using the
  documented `models[]` configuration shape
- Explicit degradation to metadata-only output when transcription or the LLM
  is disabled or fails; the result explains why no interpretation exists, does
  not offer an empty interpretation action, and never substitutes the title for
  actual video content
- A guarded backend playback proxy that supports browser range requests without
  exposing signed Douyin CDN URLs to the frontend; its initial source must be an
  allowlisted Douyin CDN, and every HTTPS CDN redirect is rechecked against
  public-address SSRF rules. Unsafe or unreachable PCDN assignments trigger a
  bounded five-line retry from the trusted initial source using alternate media
  assignments
- Bilibili and YouTube shown as upcoming platforms

## Tech stack

- Frontend: Next.js 16, React 19, TypeScript, and Tailwind CSS 4
- UI: Tailwind CSS, Lucide icons, and accessible native controls
- AI: LangChain and OpenAI-compatible chat and transcription models
- Backend: Python 3.12+, FastAPI, HTTPX, Pydantic, and
  `jiji262/douyin-downloader`

## Current status

The end-to-end Douyin extraction and analysis flow is implemented for direct
video URLs, short links, copied share text, and Selected-page `modal_id` links.
Public share-page parsing remains the primary path; the pinned
`douyin-downloader` detail client is an isolated fallback. When video analysis is
configured, the backend extracts audio, transcribes speech, and returns an LLM
interpretation based only on that transcript. Browser cookie capture, batch
downloading, and database features from the upstream project are not enabled.

## Architecture

```text
visual-essence/
├── frontend/                  # Next.js App Router application (port 3000)
│   ├── src/app/               # Pages and layout
│   │   └── result/            # Dedicated extraction result route
│   ├── src/components/        # Interactive UI
│   └── src/core/              # URL rules and typed backend client
└── backend/                   # FastAPI application (port 8000)
    ├── app/gateway/           # App factory, dependencies, and HTTP routers
    ├── app/videos/            # Extraction, playback, transcription, and LLM analysis
    └── tests/                 # Gateway and extraction tests
```

## Prerequisites

- Node.js 22+
- pnpm 10.26.2+
- Python 3.12+
- uv

## Local development

Install both applications from the repository root:

```bash
make install
```

Run both development servers together with `make dev`, or start them separately:

Frontend:

```bash
cd frontend
pnpm install
pnpm dev
```

Backend:

```bash
cd backend
uv sync
make dev
```

Video analysis is disabled until it is explicitly configured. Copy the root
template, provide secrets through environment variables, and restart the backend:

```bash
cp config.example.yaml config.yaml
export OPENAI_API_KEY="your-api-key"
cd backend
make dev
```

The configuration uses the `models[]` registry documented in
`config.example.yaml`. To reuse an existing compatible configuration without copying credentials, set
`VISUAL_ESSENCE_CONFIG_PATH=/absolute/path/to/config.yaml`. Select a named model
with `VISUAL_ESSENCE_LLM_MODEL_NAME` when the file contains multiple models.

For local transcription, install `ffmpeg` and `whisper-cli`, download a
whisper.cpp model, and set these fields in the ignored `config.yaml`:

```yaml
video_analysis:
  enabled: true
  transcription_provider: local_whisper
  whisper_cli_path: whisper-cli
  whisper_model_path: $WHISPER_MODEL_PATH
  whisper_language: zh
```

The default `openai` transcription provider uses the configured
`transcription_api_url`, `transcription_api_key`, and `transcription_model`.
Never commit the real `config.yaml` or API keys.

Copy the optional frontend environment template when the backend runs at a
different address:

```bash
cp frontend/.env.example frontend/.env.local
```

The frontend uses port `3000` by default, and the backend uses port `8000`.
OpenAPI documentation is available at `http://localhost:8000/docs`.

Before opening a pull request, run the same checks used by CI:

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

The endpoint accepts either a direct Douyin URL or copied share text containing
one. It only retrieves publicly available metadata, recognizes `modal_id`, and
revalidates every redirect target before making an outbound request. If public
page state is incomplete, the backend may call the pinned upstream detail client
with an empty, non-authenticated cookie set. It never captures browser cookies
automatically. Successful responses include a dynamic `processing_trace` made
from the path that actually ran. Each activity has a `kind`, `status`,
`elapsed_ms`, and safe structured `data`; running activities are updated in
place when they complete or become warnings. The streaming endpoint
`POST /api/conversations` creates a durable local conversation record, and
`POST /api/conversations/{id}/extract/stream` sends each activity update as
NDJSON so the conversation can display real progress without an intermediate
loading page. Fully analyzed responses have
`status: "analyzed"` and return `transcript` plus
`coach_interpretation` (`summary`, `key_points`, and `questions`). If analysis
fails, the endpoint still returns metadata with an explicit warning and no
fabricated interpretation.

`POST /api/conversations/{id}/messages` continues the same video conversation;
`GET /api/conversations/{id}` restores its persisted video result together with
the user and assistant turns.

## Roadmap

- Subtitle-track extraction when a platform exposes subtitles
- Bilibili support
- YouTube support

## Contributing and license

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening
a pull request and report vulnerabilities according to [SECURITY.md](SECURITY.md).
Visual Essence is released under the [MIT License](LICENSE).
