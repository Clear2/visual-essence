import {
  Check,
  ChevronDown,
  CircleDot,
  GitBranch,
  LoaderCircle,
  Sparkles,
  TriangleAlert,
  Wrench,
} from "lucide-react";
import React from "react";

import type { ProcessingTraceStep, VideoContent } from "@/core/api/videos";

type ProcessingTraceProps = {
  steps: VideoContent["processing_trace"];
};

const kindLabels: Record<ProcessingTraceStep["kind"], string> = {
  observation: "观察",
  tool: "工具",
  decision: "调整",
  result: "结果",
  warning: "注意",
};

const evidenceLabels: Record<string, string> = {
  author: "作者",
  byte_size: "媒体大小",
  character_count: "转写字符",
  duration_seconds: "时长",
  failed_line: "失败线路",
  input_type: "输入类型",
  key_point_count: "关键点",
  line: "采用线路",
  media_byte_size: "媒体大小",
  next_line: "下一线路",
  question_count: "问题",
  reason: "原因",
  source: "数据来源",
  strategy: "采用策略",
  summary_excerpt: "总结片段",
  title: "标题",
  transcript_character_count: "转写字符",
  video_id: "视频 ID",
};

const evidenceValueLabels: Record<string, string> = {
  direct_url: "直接链接",
  detail_api: "公开详情接口",
  incomplete_public_state: "公开页状态不完整",
  public_detail_api: "公开视频详情接口",
  public_share_page: "公开分享页",
  share_text: "分享文案",
};

export function formatActivityElapsed(elapsedMs: number) {
  if (elapsedMs < 1000) {
    return `+${elapsedMs}ms`;
  }
  return `+${(elapsedMs / 1000).toFixed(2)}s`;
}

function formatEvidenceValue(
  key: string,
  value: string | number | boolean | null,
) {
  if (value === null) {
    return "未知";
  }
  if (typeof value === "number") {
    if (key === "byte_size" || key === "media_byte_size") {
      return `${value.toLocaleString("en-US")} 字节`;
    }
    if (key === "duration_seconds") {
      return `${value} 秒`;
    }
    if (key.includes("character_count")) {
      return `${value.toLocaleString("en-US")} 字`;
    }
    return value.toLocaleString("en-US");
  }
  if (typeof value === "boolean") {
    return value ? "是" : "否";
  }
  return evidenceValueLabels[value] ?? value;
}

function KindIcon({ kind }: { kind: ProcessingTraceStep["kind"] }) {
  if (kind === "tool") {
    return <Wrench aria-hidden="true" size={12} strokeWidth={1.8} />;
  }
  if (kind === "decision") {
    return <GitBranch aria-hidden="true" size={12} strokeWidth={1.8} />;
  }
  if (kind === "result") {
    return <Sparkles aria-hidden="true" size={12} strokeWidth={1.8} />;
  }
  if (kind === "warning") {
    return <TriangleAlert aria-hidden="true" size={12} strokeWidth={1.8} />;
  }
  return <CircleDot aria-hidden="true" size={12} strokeWidth={1.8} />;
}

function StatusIcon({ status }: { status: ProcessingTraceStep["status"] }) {
  if (status === "running") {
    return (
      <LoaderCircle
        aria-label="正在执行"
        className="spin"
        size={14}
        strokeWidth={1.8}
      />
    );
  }
  if (status === "warning") {
    return <TriangleAlert aria-label="需要注意" size={14} strokeWidth={1.8} />;
  }
  return <Check aria-label="已完成" size={14} strokeWidth={2} />;
}

export function ActivityTimeline({ steps }: { steps: ProcessingTraceStep[] }) {
  return (
    <ol className="processing-trace__activity">
      {steps.map((step) => {
        const evidence = Object.entries(step.data).filter(
          ([, value]) => value !== "" && value !== null,
        );
        return (
          <li key={step.key} data-kind={step.kind} data-status={step.status}>
            <div className="processing-trace__activity-head">
              <span className="processing-trace__kind">
                <KindIcon kind={step.kind} />
                {kindLabels[step.kind]}
              </span>
              <time>{formatActivityElapsed(step.elapsed_ms)}</time>
              <StatusIcon status={step.status} />
            </div>
            <div className="processing-trace__activity-copy">
              <strong>{step.title}</strong>
              <p>{step.detail}</p>
              {evidence.length > 0 && (
                <dl className="processing-trace__evidence">
                  {evidence.map(([key, value]) => (
                    <div key={key}>
                      <dt>{evidenceLabels[key] ?? key}</dt>
                      <dd>{formatEvidenceValue(key, value)}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

export function ProcessingTrace({ steps }: ProcessingTraceProps) {
  if (steps.length === 0) {
    return null;
  }

  return (
    <details className="processing-trace">
      <summary className="processing-trace__summary">
        <span className="processing-trace__label">
          <GitBranch aria-hidden="true" size={15} strokeWidth={1.8} />
          查看思考过程
        </span>
        <span className="processing-trace__count">
          公开推理记录 · {steps.length} 条活动
        </span>
        <ChevronDown
          aria-hidden="true"
          className="processing-trace__chevron"
          size={16}
          strokeWidth={1.8}
        />
      </summary>

      <div className="processing-trace__content">
        <p className="processing-trace__note">
          逐字说明来自实际执行结果与公开决策摘要，不包含模型隐藏提示或不可验证的草稿。
        </p>
        <ActivityTimeline steps={steps} />
      </div>
    </details>
  );
}
