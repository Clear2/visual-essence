import { ArrowRight } from "lucide-react";
import React from "react";

import { ProcessingTrace } from "@/components/processing-trace";
import type { VideoContent } from "@/core/api/videos";

type VideoResultProps = {
  video: VideoContent;
  onOpenInterpretation: () => void;
  showProcessingTrace?: boolean;
};

export function VideoResult({
  video,
  onOpenInterpretation,
  showProcessingTrace = true,
}: VideoResultProps) {
  return (
    <article className="video-result" aria-label="视频提取结果">
      <div
        className={
          video.cover_url
            ? "video-result__cover"
            : "video-result__cover video-result__cover--empty"
        }
        style={
          video.cover_url
            ? { backgroundImage: `url("${video.cover_url}")` }
            : undefined
        }
        role="img"
        aria-label={
          video.cover_url ? `${video.title} 的视频封面` : "视频封面暂不可用"
        }
      >
        <span>DOUYIN</span>
      </div>
      <div className="video-result__body">
        <div className="video-result__meta">
          <span>提取完成</span>
          {video.duration_seconds && (
            <span>{Math.round(video.duration_seconds)} 秒</span>
          )}
        </div>
        <h2>{video.title}</h2>
        <p>{video.description || "该视频没有提供额外描述。"}</p>
        <div className="video-result__footer">
          <span>{video.author.name || "未知作者"}</span>
          <button
            type="button"
            className="video-result__interpretation-trigger"
            onClick={onOpenInterpretation}
          >
            查看私教解读
            <ArrowRight size={14} strokeWidth={1.7} />
          </button>
        </div>
      </div>
      {showProcessingTrace && (
        <ProcessingTrace steps={video.processing_trace} />
      )}
    </article>
  );
}
