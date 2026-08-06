# Backend Architecture

Visual Essence uses a gateway plus domain-module layout modeled after the
reference backend supplied for this project.

```text
HTTP request
    │
    ▼
app/gateway/routers/videos.py
    │  calls one interface
    ▼
VideoExtractionModule.extract(url)
    ├── validate URL and DNS target
    ├── recognize direct IDs and `modal_id` query values
    ├── follow allowlisted redirects
    ├── fetch public HTML through HTTPX
    ├── parse Douyin page state
    ├── fall back to DouyinDownloaderDetailClient when page state is incomplete
    ├── register an allowlisted media source behind a local playback URL
    ├── optionally fetch media through that guarded playback path
    ├── extract audio and transcribe speech
    ├── invoke an LLM using the transcript as the sole content source
    ├── attach a verified processing trace
    └── return VideoContentResponse

Before the user-facing extraction starts, `POST /api/conversations` stores the
submitted source in `data/conversations/{uuid}.json` and returns only that UUID.
The frontend route uses `/result?id={uuid}`. Its conversation streaming endpoint
loads the stored source URL and delegates to the same `VideoExtractionModule`;
the transport route never needs the Douyin URL in its browser address.
The completed analyzed video contract is persisted on that conversation.
Follow-up message requests compose the stored transcript, up to eight recent
turns, and the new question through `TranscriptConversationCoach`; successful
user/assistant exchanges are then written back to the same record.

Browser playback requests use `GET /api/videos/{video_id}/playback`. The route
passes valid Range headers through `VideoExtractionModule`, forwards only safe
media response headers, and never exposes the signed upstream CDN URL. The
registered initial media source must match the static Douyin CDN allowlist.
Redirect targets are accepted only as part of that trusted response chain; each
must use HTTPS on the default port, omit URL credentials, and resolve entirely
to public IP addresses before it is requested. Unsafe or failed CDN redirect
chains are retried from the original allowlisted source at most five times;
the retry rotates the public play endpoint's `line` parameter so Douyin can
assign another CDN. Rejected targets are never requested.

`DouyinDownloaderDetailClient` is a deliberately small adapter around the pinned
`jiji262/douyin-downloader` `DouyinAPIClient.get_video_detail()` API. It uses an
empty cookie set for public content and does not enable the upstream CLI,
database, browser fallback, automatic cookie capture, or download pipeline. The
adapter is replaceable at the `DouyinDetailClient` boundary for deterministic
tests. Metadata normalization also follows the upstream preference for the
highest available bitrate and converts the public `playwm` endpoint into its
no-watermark `play` form before registering the private playback source.

Video analysis is separately replaceable at the `VideoAnalyzer` boundary. The
production implementation composes an `AudioTranscriber` (OpenAI-compatible API
or local whisper.cpp CLI) with a `OneShotLlm` backed by LangChain. Model
definitions are read from the root configuration using the documented `models[]`
shape. The model receives the transcript as untrusted source material and must
return JSON containing `summary`, `key_points`, and `questions`; Pydantic
validates that response before it reaches the API. A completed analysis adds the
observable `media_retrieved`, `audio_transcribed`, and `content_interpreted`
trace stages. The streaming extraction endpoint forwards these same completed
stages as NDJSON events before the final result, so live UI progress and the
persisted trace cannot drift. Failures preserve metadata, attach a warning, and
never generate a title-based summary.
```

## Dependency direction

- `app.gateway` may import `app.videos`.
- `app.videos` must not import `app.gateway`.
- HTTP models are defined in `app.videos.contracts` so the module interface and
  the transport contract cannot drift.
- Platform-specific parsing stays inside the video module.
- Third-party Douyin behavior stays behind `DouyinDetailClient`; Gateway routers
  must not import the upstream package directly.
- Transcription and LLM behavior stay behind `VideoAnalyzer`, `AudioTranscriber`,
  and `OneShotLlm`; the extractor owns only orchestration and graceful fallback.
- `processing_trace` contains completed, observable stages only. It must never
  expose private model reasoning, hidden prompts, or speculative drafts.

## Adding a platform

Add a parser inside `app/videos/`, extend the platform enum and host policy, and
route to that parser from `VideoExtractionModule`. The Gateway route and frontend
request shape should remain unchanged.
