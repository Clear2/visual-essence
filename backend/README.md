# Visual Essence Backend

FastAPI gateway for extracting structured content from public video links.
The first release supports Douyin direct, short, copied-share, and
`jingxuan?modal_id=...` links. Public page parsing is backed by an isolated,
pinned `jiji262/douyin-downloader` detail fallback.

When enabled, the analysis pipeline extracts the media audio, transcribes it
with an OpenAI-compatible endpoint or local `whisper-cli`, and invokes a
configured LangChain chat model. The resulting `coach_interpretation` is
validated structured data grounded in the transcript; analysis failures remain
metadata-only instead of falling back to the title.

## Commands

```bash
uv sync
make dev
make test
make lint
make format
```

The API runs on `http://localhost:8000`. OpenAPI documentation is available at
`http://localhost:8000/docs`.

Copy `../config.example.yaml` to `../config.yaml` to configure video analysis.
Keep API keys in environment variables. The backend also accepts an existing
compatible configuration through `VISUAL_ESSENCE_CONFIG_PATH`.

## Main endpoints

- `GET /health`
- `POST /api/videos/extract`
- `POST /api/videos/extract/stream` (NDJSON progress + final result)
- `POST /api/conversations` (persist source and return an opaque ID)
- `POST /api/conversations/{id}/extract/stream`
- `GET /api/conversations/{id}` (restore persisted turns)
- `POST /api/conversations/{id}/messages` (transcript-grounded follow-up)
- `GET /api/videos/{video_id}/playback`

Example request:

```json
{
  "url": "https://www.douyin.com/jingxuan?modal_id=7667128493197192313"
}
```
