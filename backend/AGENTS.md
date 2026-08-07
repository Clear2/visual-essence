# Backend guidance

The backend is a Python FastAPI service responsible for URL validation, Douyin
page retrieval, metadata normalization, audio transcription, LLM-based content
interpretation, playback proxying, and API responses.

## Stack and commands

- Python 3.12+
- FastAPI and Pydantic
- HTTPX for outbound HTTP requests
- uv for dependency and virtual-environment management
- pytest and pytest-asyncio for tests
- Ruff for linting and formatting

Run commands from `backend/`:

```bash
uv sync
make dev
make test
make lint
make format
```

## Structure

The layout follows the same high-level application organization as the supplied
reference backend without importing unrelated agent-specific modules:

```text
backend/
├── app/
│   ├── gateway/
│   │   ├── app.py             # FastAPI app factory and lifespan
│   │   ├── config.py          # Process configuration
│   │   ├── deps.py            # HTTP dependency seams
│   │   └── routers/           # Thin HTTP routers
│   └── videos/                # Deep video extraction module
├── tests/                     # Gateway and module-interface tests
├── Dockerfile
├── Makefile
└── pyproject.toml
```

`VideoExtractionModule.extract()` is the module interface. Redirect resolution,
outbound-request safety, upstream fetching, page-state parsing, and response
normalization stay behind that interface. Routers must not duplicate those
rules. When an extracted page exposes a verified media source, the public
response contains only a stable local `playback_url`; the signed upstream URL
stays inside `VideoExtractionModule`, and the playback route proxies allowlisted
media bytes with browser Range headers. The initial source must match the static
Douyin CDN allowlist. A redirect returned by that trusted chain may use another
CDN hostname only when it remains HTTPS on the default port, contains no URL
credentials, and passes the public-IP SSRF check before every request.
Unsafe or failed redirect chains may be retried only from the original
allowlisted source, with a fixed five-attempt limit. For the public
`snssdk.com/aweme/v1/play/` endpoint, retries may rotate the `line` parameter;
never request the rejected target.
Successful responses include a
`processing_trace` made only from
verifiable processing activity; never put private model reasoning, prompts, or
unvalidated drafts in it. Activities carry `kind`, `status`, `elapsed_ms`, and
safe structured `data`. Emit a `running` event before real work, then update the
same key to `complete` or `warning`; final traces keep only the latest state for
each key. Conditional fallbacks and media-line retries produce their own events.
The production adapter uses HTTPX; tests use HTTPX's in-memory transport.

`POST /api/videos/extract/stream` returns NDJSON activity updates as work starts,
completes, changes strategy, or warns, followed by one result or error event. Keep the ordinary
`POST /api/videos/extract` endpoint for non-streaming clients. Streaming stages
and the final `processing_trace` must come from the same extractor callbacks so
the loading UI never presents timer-based or fabricated progress.

User-facing result routes are conversation-based. `FileConversationStore`
persists the source URL under `data/conversations/{uuid}.json` (gitignored),
`POST /api/conversations` returns only the opaque UUID, and
`POST /api/conversations/{id}/extract/stream` resolves the stored source before
starting extraction. Never put the source URL back into the browser result URL.
Completed analyzed responses are stored on the conversation so follow-up
questions can use the transcript. `TranscriptConversationCoach` receives only
that transcript, up to eight recent turns, and the new question. Persist the
user/assistant exchange only after a successful model answer; if the transcript
does not support an answer, the coach must say so rather than guessing.
`GET /api/conversations/{id}` returns the persisted video result together with
the saved turns so the frontend can restore a completed conversation without
rerunning extraction.

Optional video analysis lives behind `VideoAnalyzer`. The production
`TranscriptLlmVideoAnalyzer` receives complete media bytes through the same safe
playback path, extracts an audio file, transcribes it through either an
OpenAI-compatible API or local `whisper-cli`, and asks a LangChain chat model for
validated `summary`, `key_points`, and `questions`. Model definitions use the
root `config.yaml -> models[]` shape documented in `config.example.yaml`. Video analysis is
disabled unless explicitly enabled in `video_analysis`. If transcription or the
LLM fails, return the metadata result with an actionable warning and leave
`coach_interpretation` empty; never create a title-based fallback.
When analysis is disabled, emit the same explicit metadata-only boundary rather
than silently ending after metadata extraction.

Douyin links may identify a work through `/video/{id}` or a `modal_id` query
parameter. Public share-page parsing is the primary extraction path. If that
page does not contain usable work state, `DouyinDownloaderDetailClient` may call
the pinned `jiji262/douyin-downloader` detail API behind the
`DouyinDetailClient` interface. Keep the upstream project's CLI, browser-cookie
capture, database, batch-download, and transcription pipeline disabled; Visual
Essence owns its separate analysis pipeline behind `VideoAnalyzer`.

## Requirements

- Use async HTTP calls in request paths and set explicit connect/read timeouts.
- Validate schemes and hosts before outbound requests. Revalidate every redirect
  target to prevent SSRF.
- Do not return raw upstream exceptions, cookies, tokens, or signed URLs.
- Put external-service behavior behind interfaces and use fixtures/mocks in unit
  tests.
- Write tests before or alongside every feature and bug fix.
- Use type hints and Pydantic models at API boundaries.
- Keep `README.md` and `README_zh.md` synchronized for user-facing changes.
