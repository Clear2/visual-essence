import { LoaderCircle } from "lucide-react";
import React from "react";

import { ReasoningNarrative } from "@/components/processing-trace";
import type { ProcessingTraceStep } from "@/core/api/videos";

export function ExtractionProgress({
  steps,
}: {
  steps: ProcessingTraceStep[];
}) {
  return (
    <div className="result-status result-progress" role="status">
      <div className="result-progress__heading">
        <LoaderCircle className="spin" size={18} strokeWidth={1.7} />
        <span>
          <strong>正在理解这条视频</strong>
          <small>内容会随着真实处理结果自然续写</small>
        </span>
      </div>
      <ReasoningNarrative steps={steps} streaming />
    </div>
  );
}
