import { LoaderCircle } from "lucide-react";
import React from "react";

import { ActivityTimeline } from "@/components/processing-trace";
import { StreamingReasoningText } from "@/components/streaming-reasoning-text";
import type { ProcessingTraceStep } from "@/core/api/videos";

export function ExtractionProgress({
  steps,
}: {
  steps: ProcessingTraceStep[];
}) {
  const activeDetail =
    steps.at(-1)?.detail ?? "正在连接内容提取服务，等待第一条真实活动记录。";

  return (
    <div className="result-status result-progress" role="status">
      <div className="result-progress__heading">
        <LoaderCircle className="spin" size={22} strokeWidth={1.6} />
        <span>
          <strong>公开推理正在生成</strong>
          <small>
            <StreamingReasoningText key={activeDetail} text={activeDetail} />
          </small>
        </span>
      </div>
      <p>
        以下逐条内容来自实际工具结果与公开决策摘要；不同链接、失败和重试会产生不同记录。
      </p>
      {steps.length > 0 && <ActivityTimeline steps={steps} />}
    </div>
  );
}
