import { z } from "zod";

const authorSchema = z.object({
  name: z.string().nullable(),
  avatar_url: z.string().nullable(),
});

const processingTraceStepSchema = z.object({
  key: z.string(),
  title: z.string(),
  detail: z.string(),
  kind: z.enum(["observation", "tool", "decision", "result", "warning"]),
  status: z.enum(["running", "complete", "warning"]),
  elapsed_ms: z.number().int().nonnegative(),
  data: z.record(
    z.string(),
    z.union([z.string(), z.number(), z.boolean(), z.null()]),
  ),
});

export type ProcessingTraceStep = z.infer<typeof processingTraceStepSchema>;

const coachInterpretationSchema = z.object({
  summary: z.string(),
  key_points: z.array(z.string()),
  questions: z.array(z.string()),
});

const videoContentSchema = z.object({
  platform: z.literal("douyin"),
  status: z.enum(["metadata", "analyzed"]),
  source_url: z.string(),
  canonical_url: z.string(),
  video_id: z.string().nullable(),
  title: z.string(),
  description: z.string().nullable(),
  author: authorSchema,
  cover_url: z.string().nullable(),
  playback_url: z.string().nullable(),
  duration_seconds: z.number().nullable(),
  transcript: z.string().nullable(),
  coach_interpretation: coachInterpretationSchema.nullable(),
  warnings: z.array(z.string()),
  processing_trace: z.array(processingTraceStepSchema),
});

export type VideoContent = z.infer<typeof videoContentSchema>;

const extractionStreamEventSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("conversation"), source_url: z.string().url() }),
  z.object({ type: z.literal("progress"), step: processingTraceStepSchema }),
  z.object({ type: z.literal("result"), video: videoContentSchema }),
  z.object({ type: z.literal("error"), message: z.string() }),
]);

export type ExtractionStreamEvent = z.infer<typeof extractionStreamEventSchema>;

export class VideoExtractionApiError extends Error {}

const conversationSchema = z.object({
  id: z
    .string()
    .regex(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/),
});

const conversationMessageSchema = z.object({
  id: z.string().regex(/^[0-9a-f-]{36}$/),
  role: z.enum(["user", "assistant"]),
  content: z.string(),
  created_at: z.string(),
});

const conversationDetailsSchema = z.object({
  id: conversationSchema.shape.id,
  video: videoContentSchema.nullable(),
  messages: z.array(conversationMessageSchema),
});

const conversationMessageResponseSchema = z.object({
  message: conversationMessageSchema,
});

export type VideoConversation = z.infer<typeof conversationSchema>;
export type ConversationMessage = z.infer<typeof conversationMessageSchema>;
export type ConversationDetails = z.infer<typeof conversationDetailsSchema>;

export function parseConversationResponse(value: unknown): VideoConversation {
  const result = conversationSchema.safeParse(value);
  if (!result.success) {
    throw new VideoExtractionApiError("后端返回的对话 ID 格式不正确。");
  }
  return result.data;
}

export function parseConversationMessageResponse(value: unknown) {
  const result = conversationMessageResponseSchema.safeParse(value);
  if (!result.success) {
    throw new VideoExtractionApiError("后端返回的对话消息格式不正确。");
  }
  return result.data;
}

export function parseConversationDetailsResponse(
  value: unknown,
): ConversationDetails {
  const result = conversationDetailsSchema.safeParse(value);
  if (!result.success) {
    throw new VideoExtractionApiError("后端返回的对话记录格式不正确。");
  }
  return result.data;
}

export function parseVideoContentResponse(value: unknown): VideoContent {
  const result = videoContentSchema.safeParse(value);
  if (!result.success) {
    throw new VideoExtractionApiError("后端返回的数据格式不正确，请稍后重试。");
  }
  return result.data;
}

export function parseExtractionStreamLine(line: string): ExtractionStreamEvent {
  let value: unknown;
  try {
    value = JSON.parse(line);
  } catch {
    throw new VideoExtractionApiError("后端返回了无法识别的处理进度。");
  }
  const result = extractionStreamEventSchema.safeParse(value);
  if (!result.success) {
    throw new VideoExtractionApiError("后端返回了无法识别的处理进度。");
  }
  return result.data;
}

function apiBaseUrl() {
  return (
    process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
  ).replace(/\/+$/, "");
}

export function resolveApiUrl(value: string) {
  if (/^https?:\/\//i.test(value)) {
    return value;
  }
  return `${apiBaseUrl()}${value.startsWith("/") ? value : `/${value}`}`;
}

export async function extractVideoContent(
  url: string,
  options: { signal?: AbortSignal } = {},
): Promise<VideoContent> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}/api/videos/extract`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
      signal: options.signal,
    });
  } catch {
    throw new VideoExtractionApiError(
      "无法连接内容提取服务，请确认后端已经启动。",
    );
  }

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      payload &&
      typeof payload === "object" &&
      "detail" in payload &&
      typeof payload.detail === "string"
        ? payload.detail
        : "视频内容提取失败，请稍后重试。";
    throw new VideoExtractionApiError(detail);
  }

  return parseVideoContentResponse(payload);
}

export async function createVideoConversation(
  url: string,
  options: { signal?: AbortSignal } = {},
): Promise<VideoConversation> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}/api/conversations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
      signal: options.signal,
    });
  } catch {
    throw new VideoExtractionApiError("无法创建视频对话，请确认后端已经启动。");
  }

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      payload &&
      typeof payload === "object" &&
      "detail" in payload &&
      typeof payload.detail === "string"
        ? payload.detail
        : "无法创建视频对话，请稍后重试。";
    throw new VideoExtractionApiError(detail);
  }
  return parseConversationResponse(payload);
}

export async function getVideoConversation(
  conversationId: string,
  options: { signal?: AbortSignal } = {},
): Promise<ConversationDetails> {
  let response: Response;
  try {
    response = await fetch(
      `${apiBaseUrl()}/api/conversations/${encodeURIComponent(conversationId)}`,
      { signal: options.signal },
    );
  } catch {
    throw new VideoExtractionApiError("无法读取视频对话，请稍后重试。");
  }
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new VideoExtractionApiError("无法读取视频对话，请稍后重试。");
  }
  return parseConversationDetailsResponse(payload);
}

export async function sendConversationMessage(
  conversationId: string,
  content: string,
  options: { signal?: AbortSignal } = {},
): Promise<ConversationMessage> {
  let response: Response;
  try {
    response = await fetch(
      `${apiBaseUrl()}/api/conversations/${encodeURIComponent(conversationId)}/messages`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
        signal: options.signal,
      },
    );
  } catch {
    throw new VideoExtractionApiError("无法发送问题，请稍后重试。");
  }
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      payload &&
      typeof payload === "object" &&
      "detail" in payload &&
      typeof payload.detail === "string"
        ? payload.detail
        : "LLM 暂时无法回答这个问题。";
    throw new VideoExtractionApiError(detail);
  }
  return parseConversationMessageResponse(payload).message;
}

export async function extractVideoContentStream(
  url: string,
  options: {
    signal?: AbortSignal;
    onProgress?: (step: ProcessingTraceStep) => void;
    onConversation?: (sourceUrl: string) => void;
  } = {},
): Promise<VideoContent> {
  return extractStreamFromEndpoint(
    `${apiBaseUrl()}/api/videos/extract/stream`,
    JSON.stringify({ url }),
    options,
  );
}

async function extractStreamFromEndpoint(
  endpoint: string,
  body: string | undefined,
  options: {
    signal?: AbortSignal;
    onProgress?: (step: ProcessingTraceStep) => void;
    onConversation?: (sourceUrl: string) => void;
  },
): Promise<VideoContent> {
  let response: Response;
  try {
    response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      signal: options.signal,
    });
  } catch {
    throw new VideoExtractionApiError(
      "无法连接内容提取服务，请确认后端已经启动。",
    );
  }

  if (!response.ok || !response.body) {
    const payload: unknown = await response.json().catch(() => null);
    const detail =
      payload &&
      typeof payload === "object" &&
      "detail" in payload &&
      typeof payload.detail === "string"
        ? payload.detail
        : "视频内容提取失败，请稍后重试。";
    throw new VideoExtractionApiError(detail);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let video: VideoContent | null = null;

  const consumeLine = (line: string) => {
    if (!line.trim()) {
      return;
    }
    const event = parseExtractionStreamLine(line);
    if (event.type === "progress") {
      options.onProgress?.(event.step);
    } else if (event.type === "result") {
      video = event.video;
    } else if (event.type === "conversation") {
      options.onConversation?.(event.source_url);
    } else {
      throw new VideoExtractionApiError(event.message);
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    lines.forEach(consumeLine);
    if (done) {
      break;
    }
  }
  consumeLine(buffer);

  if (!video) {
    throw new VideoExtractionApiError("视频处理已结束，但没有返回可用结果。");
  }
  return video;
}

export async function extractConversationContentStream(
  conversationId: string,
  options: {
    signal?: AbortSignal;
    onProgress?: (step: ProcessingTraceStep) => void;
    onConversation?: (sourceUrl: string) => void;
  } = {},
): Promise<VideoContent> {
  return extractStreamFromEndpoint(
    `${apiBaseUrl()}/api/conversations/${encodeURIComponent(conversationId)}/extract/stream`,
    undefined,
    options,
  );
}
