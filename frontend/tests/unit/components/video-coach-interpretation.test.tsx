import { describe, expect, it } from "@rstest/core";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { VideoCoachInterpretation } from "../../../src/components/video-coach-interpretation";

describe("VideoCoachInterpretation", () => {
  it("renders the transcript-grounded LLM interpretation", () => {
    const html = renderToStaticMarkup(
      <VideoCoachInterpretation
        video={{
          platform: "douyin",
          status: "analyzed",
          source_url: "https://v.douyin.com/example/",
          canonical_url: "https://www.douyin.com/video/7420000000000000000",
          video_id: "7420000000000000000",
          title: "把一条视频变成可以阅读的内容",
          description: "公开视频简介",
          author: { name: "Visual Creator", avatar_url: null },
          cover_url: "https://example.com/cover.jpg",
          playback_url: "/api/videos/7420000000000000000/playback",
          duration_seconds: 15.42,
          transcript:
            "视频按时间顺序讲述北魏十一位皇帝，并重点解释孝文帝改革。",
          coach_interpretation: {
            summary: "视频梳理北魏皇位传承，并把孝文帝改革作为关键转折。",
            key_points: [
              "皇位传承受到宗室与权臣斗争影响。",
              "迁都洛阳推动了汉化改革。",
            ],
            questions: ["改革为什么会引发旧贵族反弹？"],
          },
          warnings: [],
          processing_trace: [],
        }}
      />,
    );

    expect(html).toContain('aria-label="私教解读内容"');
    expect(html).toContain("素材来源");
    expect(html).toContain("把一条视频变成可以阅读的内容");
    expect(html).toContain('<video class="coach-interpretation__video"');
    expect(html).toContain('aria-label="视频播放器"');
    expect(html).toContain("controls");
    expect(html).toContain('poster="https://example.com/cover.jpg"');
    expect(html).toContain(
      'src="http://localhost:8000/api/videos/7420000000000000000/playback"',
    );
    expect(html).not.toContain('aria-label="在抖音查看原视频"');
    expect(html).toContain("私教提炼");
    expect(html).toContain(
      "视频梳理北魏皇位传承，并把孝文帝改革作为关键转折。",
    );
    expect(html).toContain("迁都洛阳推动了汉化改革。");
    expect(html).toContain("改革为什么会引发旧贵族反弹？");
    expect(html).toContain("当前解读基于视频语音转写与 LLM 总结");
    expect(html).not.toContain("从公开页面来看");
  });
});
