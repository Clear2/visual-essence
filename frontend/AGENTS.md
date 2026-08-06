# Frontend guidance

The frontend is a Next.js 16 App Router application for submitting a Douyin URL
and viewing the extracted video content.

## Stack and commands

- Node.js 22+
- pnpm 10.26.2+
- Next.js 16, React 19, and TypeScript
- Tailwind CSS 4
- Shadcn UI, MagicUI, React Bits, and Vercel AI Elements
- LangGraph SDK for agent-backed flows

Run commands from `frontend/`:

```bash
pnpm install
pnpm dev
pnpm check
pnpm test
pnpm build
```

## Structure

Use the App Router under `src/app/`. Put reusable UI in `src/components/`, domain
logic and API clients in `src/core/`, shared hooks in `src/hooks/`, and generic
utilities in `src/lib/`. `src/core/api/videos.ts` owns the typed backend contract;
components must not parse raw API responses. `src/components/processing-trace.tsx`
owns the native disclosure and activity timeline used for the user-facing “View
thinking process” interaction. It renders dynamic observations, tools,
decisions, warnings, results, elapsed time, and safe evidence from the backend.
`src/components/streaming-reasoning-text.tsx` types the current public
explanation as it changes. These are observable public reasoning summaries, not
private hidden model reasoning. The homepage validates input and navigates to `src/app/result/`; the
result route owns loading, error, extracted-content, and processing-trace states.
`src/components/video-result.tsx` owns the user-facing “View personal-coach
interpretation” action on the extracted video card. The action is not an
external link: `src/components/video-learning-workspace.tsx` opens the in-page
detail panel, while `src/components/video-coach-interpretation.tsx` renders its
native inline video player, transcript-grounded LLM summary, key points,
reflection questions, and capability-boundary notice. When
`coach_interpretation` is absent, show the explicit analysis-unavailable state;
never construct an interpretation from title or metadata. Playback URLs come
from the typed backend contract and resolve against
the configured API origin; the preview must not navigate to the platform page.
`src/components/video-learning-workspace.tsx` owns the Sitor-aligned result
workspace: left session navigation, the central conversation feed and composer,
and the right roadmap/notes panel. Keep desktop collapse, mobile drawers, and
message-level process disclosure behavior synchronized when changing this shell.
The homepage creates a server-side conversation, then navigates to
`/result?id={conversationId}`; never encode the source URL in the result route.
The result page immediately renders the conversation workspace and first reads
`GET /api/conversations/{id}`. Restore a persisted video result directly when
one exists; only a new conversation consumes
`POST /api/conversations/{id}/extract/stream`. Show only backend-reported stages
inside the assistant message and roadmap, without a fixed total-step count.
Upsert streaming activities by `key` so a running event is replaced by its
completed or warning state instead of appearing twice.
Never add a separate intermediate loading page, simulate progress with a timer,
or label observable processing as the model's private chain of thought.
After analysis, the workspace composer posts to the current conversation's
`/messages` endpoint, renders an immediate user turn plus a bounded LLM waiting
state, and restores saved turns through `GET /api/conversations/{id}`. Never
encode questions or source URLs back into the result route.
Tests live under `tests/` and mirror the source layout.

## Conventions

- Prefer Server Components; add `"use client"` only for interactive state or
  browser APIs.
- Validate API responses at the boundary and render actionable error states.
- Keep generated registry components under `src/components/ui/` or
  `src/components/ai-elements/`; avoid hand-editing generated files.
- Use the `@/*` path alias for `src/*` imports.
- Use `cn()` for conditional Tailwind class composition.
- Add tests for user-visible flows and non-trivial state transitions.

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
