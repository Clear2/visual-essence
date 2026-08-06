# AGENTS.md

Visual Essence is a web application that accepts a Douyin share URL and
extracts the video's usable content for the user.

## Repository layout

- `frontend/`: Next.js 16 App Router application. Read `frontend/AGENTS.md`
  before changing frontend code.
- `backend/`: Python FastAPI application organized around `app/gateway/` and
  domain modules such as `app/videos/`. Read `backend/AGENTS.md` before changing
  backend code.

## Product boundary

The core flow is:

1. Accept and validate a Douyin share URL.
2. Resolve redirects and retrieve public video metadata safely.
3. Extract useful content such as title, author, transcript, and media metadata.
4. Return normalized data to the frontend.

Do not add download, scraping, or bypass behavior that violates access controls,
platform terms, or applicable law. Never log cookies, tokens, or signed media
URLs.

## Engineering conventions

- Keep frontend and backend contracts explicit and typed.
- Add tests with every feature or bug fix.
- Keep user-facing setup and behavior synchronized across `README.md` and
  `README_zh.md`.
- Keep module-level architecture and commands documented in the relevant
  `AGENTS.md` file.
- Do not commit generated output, local environments, credentials, IDE state, or
  downloaded media.

## Current status

Visual Essence has an end-to-end public Douyin extraction and optional video
analysis flow, including direct links, short links, copied share text, and
`jingxuan?modal_id=...` links. The backend uses public share-page parsing first
and a pinned `jiji262/douyin-downloader` detail adapter as a fallback. When
configured, it extracts audio, transcribes speech through an OpenAI-compatible
API or local whisper.cpp, and invokes a configured LangChain chat model for a
transcript-grounded interpretation. Analysis failure must degrade to explicit
metadata-only output; never synthesize video content from the title. Keep the
gateway thin and platform rules inside the video module.

The browser result route is conversation-based: create a persisted conversation
first and navigate with `/result?id={uuid}`. Never place the submitted Douyin URL
in the result-page query string. The conversation workspace is also the loading
surface; stream verified stages into it instead of adding an intermediate page.
Once analysis is complete, follow-up questions stay inside that conversation and
must be answered from the persisted transcript plus bounded recent turns. Keep
messages durable across refreshes and decline unsupported questions rather than
inventing video content.
