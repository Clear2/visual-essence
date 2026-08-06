"use client";

import React, { useEffect, useState } from "react";

import { VideoLearningWorkspace } from "@/components/video-learning-workspace";
import { VideoProcessingWorkspace } from "@/components/video-processing-workspace";
import {
  extractConversationContentStream,
  getVideoConversation,
  type ProcessingTraceStep,
  type VideoContent,
  VideoExtractionApiError,
} from "@/core/api/videos";

type ResultState =
  | { status: "loading"; sourceUrl: string; steps: ProcessingTraceStep[] }
  | { status: "ready"; video: VideoContent }
  | {
      status: "error";
      sourceUrl: string;
      steps: ProcessingTraceStep[];
      message: string;
    };

type VideoResultPageProps = {
  conversationId: string;
};

const conversationIdPattern =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

export function VideoResultPage({ conversationId }: VideoResultPageProps) {
  const validConversationId = conversationIdPattern.test(conversationId);
  const [state, setState] = useState<ResultState>(() =>
    validConversationId
      ? { status: "loading", sourceUrl: "", steps: [] }
      : {
          status: "error",
          sourceUrl: "",
          steps: [],
          message: "对话 ID 无效，请重新提交视频链接。",
        },
  );

  useEffect(() => {
    if (!validConversationId) {
      return;
    }

    const controller = new AbortController();
    getVideoConversation(conversationId, { signal: controller.signal })
      .then((conversation) => {
        if (conversation.video) {
          return conversation.video;
        }
        return extractConversationContentStream(conversationId, {
          signal: controller.signal,
          onConversation: (sourceUrl) =>
            setState((current) =>
              current.status === "loading"
                ? { ...current, sourceUrl }
                : current,
            ),
          onProgress: (step) =>
            setState((current) => {
              if (current.status !== "loading") {
                return current;
              }
              const steps = current.steps.some((item) => item.key === step.key)
                ? current.steps.map((item) =>
                    item.key === step.key ? step : item,
                  )
                : [...current.steps, step];
              return { ...current, steps };
            }),
        });
      })
      .then((video) => setState({ status: "ready", video }))
      .catch((cause: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        setState((current) => ({
          status: "error",
          sourceUrl: current.status === "ready" ? "" : current.sourceUrl,
          steps: current.status === "ready" ? [] : current.steps,
          message:
            cause instanceof VideoExtractionApiError
              ? cause.message
              : "视频内容提取失败，请稍后重试。",
        }));
      });

    return () => controller.abort();
  }, [conversationId, validConversationId]);

  if (state.status === "ready") {
    return (
      <VideoLearningWorkspace
        conversationId={conversationId}
        video={state.video}
      />
    );
  }

  return (
    <VideoProcessingWorkspace
      conversationId={conversationId}
      sourceUrl={state.sourceUrl}
      steps={state.steps}
      error={state.status === "error" ? state.message : undefined}
    />
  );
}
