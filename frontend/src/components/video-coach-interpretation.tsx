import {
  BookOpen,
  Clock3,
  ExternalLink,
  Sparkles,
  UserRound,
} from "lucide-react";
import React from "react";

import { resolveApiUrl, type VideoContent } from "@/core/api/videos";

type VideoCoachInterpretationProps = {
  video: VideoContent;
};

function formatDuration(duration: number | null) {
  return duration ? `${Math.round(duration)} 秒` : "时长未知";
}

export function VideoCoachInterpretation({
  video,
}: VideoCoachInterpretationProps) {
  const interpretation = video.coach_interpretation;

  return (
    <section
      className="coach-interpretation"
      role="tabpanel"
      aria-label="私教解读内容"
    >
      <a
        className="coach-interpretation__source"
        href={video.canonical_url}
        target="_blank"
        rel="noreferrer"
      >
        <span className="coach-interpretation__source-icon" aria-hidden="true">
          <BookOpen size={15} strokeWidth={1.8} />
        </span>
        <span>
          <small>素材来源</small>
          <strong>{video.title}</strong>
        </span>
        <ExternalLink size={14} strokeWidth={1.7} aria-hidden="true" />
      </a>

      {video.playback_url ? (
        <video
          className="coach-interpretation__video"
          aria-label="视频播放器"
          controls
          playsInline
          preload="metadata"
          poster={video.cover_url || undefined}
          src={resolveApiUrl(video.playback_url)}
        />
      ) : (
        <div className="coach-interpretation__preview-unavailable">
          <strong>暂时无法加载视频播放器</strong>
          <span>请重新解析该视频后再试。</span>
        </div>
      )}

      <div className="coach-interpretation__article">
        <p className="coach-interpretation__kicker">
          <Sparkles size={14} strokeWidth={1.8} aria-hidden="true" />
          私教提炼
        </p>
        <h3>这条视频值得抓住什么？</h3>
        {interpretation ? (
          <>
            <p>{interpretation.summary}</p>

            <div className="coach-interpretation__insights">
              <h4>关键内容</h4>
              <ul>
                {interpretation.key_points.map((point) => (
                  <li key={point}>{point}</li>
                ))}
              </ul>
            </div>

            {interpretation.questions.length > 0 && (
              <div className="coach-interpretation__insights">
                <h4>带着这些问题回看</h4>
                <ul>
                  {interpretation.questions.map((question) => (
                    <li key={question}>{question}</li>
                  ))}
                </ul>
              </div>
            )}
          </>
        ) : (
          <div className="coach-interpretation__preview-unavailable">
            <strong>尚未生成视频内容解读</strong>
            <span>
              需要先取得视频语音转写并完成 LLM
              总结；这里不会用标题代替视频内容。
            </span>
          </div>
        )}

        <div className="coach-interpretation__facts">
          <div>
            <UserRound size={15} strokeWidth={1.7} aria-hidden="true" />
            <span>
              <small>内容作者</small>
              <strong>{video.author.name || "未知作者"}</strong>
            </span>
          </div>
          <div>
            <Clock3 size={15} strokeWidth={1.7} aria-hidden="true" />
            <span>
              <small>素材时长</small>
              <strong>{formatDuration(video.duration_seconds)}</strong>
            </span>
          </div>
        </div>

        <div className="coach-interpretation__boundary">
          <strong>
            {interpretation
              ? "当前解读基于视频语音转写与 LLM 总结"
              : "当前仅取得公开视频页面信息"}
          </strong>
          <p>
            {interpretation
              ? "总结只以已识别的口播文本为依据；仍建议结合画面和原视频语境核对细节。"
              : "未取得转写时不生成推测性总结，请检查后端的视频分析配置。"}
          </p>
          {video.warnings.length > 0 && (
            <ul>
              {video.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
