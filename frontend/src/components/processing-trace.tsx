import { Brain, ChevronRight } from "lucide-react";
import React from "react";

import { StreamingReasoningText } from "@/components/streaming-reasoning-text";
import type { ProcessingTraceStep, VideoContent } from "@/core/api/videos";

type ProcessingTraceProps = {
  steps: VideoContent["processing_trace"];
  label?: string;
};

const WAITING_FOR_EVIDENCE = "正在等待第一条可验证的处理记录。";

function finishSentence(value: string) {
  const normalized = value.trim();
  if (!normalized || /[。！？!?]$/.test(normalized)) {
    return normalized;
  }
  return `${normalized}。`;
}

/**
 * Compose only backend-reported public observations. This deliberately does
 * not infer transitions from titles, kinds, timings, or arbitrary data fields.
 */
export function buildPublicReasoningNarrative(steps: ProcessingTraceStep[]) {
  const fragments: string[] = [];

  for (const step of steps) {
    const detail = finishSentence(step.detail);
    if (detail && fragments.at(-1) !== detail) {
      fragments.push(detail);
    }
  }

  return fragments.join(" ");
}

export function ReasoningNarrative({
  steps,
  streaming = false,
}: {
  steps: ProcessingTraceStep[];
  streaming?: boolean;
}) {
  const narrative =
    buildPublicReasoningNarrative(steps) || WAITING_FOR_EVIDENCE;

  return (
    <div className="reasoning-thread" data-streaming={streaming}>
      <span className="reasoning-thread__rail" aria-hidden="true">
        <span />
      </span>
      <p className="reasoning-thread__copy">
        {streaming ? <StreamingReasoningText text={narrative} /> : narrative}
      </p>
    </div>
  );
}

export function ProcessingTrace({
  steps,
  label = "查看思考过程",
}: ProcessingTraceProps) {
  if (steps.length === 0) {
    return null;
  }

  return (
    <details className="processing-trace">
      <summary className="processing-trace__summary">
        <span className="processing-trace__label">
          <Brain aria-hidden="true" size={14} strokeWidth={1.7} />
          {label}
        </span>
        <ChevronRight
          aria-hidden="true"
          className="processing-trace__chevron"
          size={14}
          strokeWidth={1.7}
        />
      </summary>

      <div className="processing-trace__content">
        <ReasoningNarrative steps={steps} />
      </div>
    </details>
  );
}
