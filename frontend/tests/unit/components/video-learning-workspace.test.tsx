import { describe, expect, it } from "@rstest/core";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { VideoLearningWorkspace } from "../../../src/components/video-learning-workspace";
import type { VideoContent } from "../../../src/core/api/videos";

const video: VideoContent = {
  platform: "douyin" as const,
  status: "metadata" as const,
  source_url: "https://v.douyin.com/example/",
  canonical_url: "https://www.douyin.com/video/7420000000000000000",
  video_id: "7420000000000000000",
  title: "把一条视频变成可以阅读的内容",
  description: "公开视频简介",
  author: { name: "Visual Creator", avatar_url: null },
  cover_url: null,
  playback_url: "/api/videos/7420000000000000000/playback",
  duration_seconds: 15.42,
  transcript: null,
  coach_interpretation: null,
  warnings: ["公开视频页面没有可直接使用的字幕轨道。"],
  processing_trace: [
    {
      key: "input_inspected",
      title: "看懂了输入",
      detail: "这是一个直接视频链接。",
      kind: "observation" as const,
      status: "complete" as const,
      elapsed_ms: 2,
      data: { video_id: "7420000000000000000" },
    },
    {
      key: "result_ready",
      title: "公开视频信息已经整理好",
      detail: "标题、作者、封面和时长已经归一化。",
      kind: "result" as const,
      status: "complete" as const,
      elapsed_ms: 780,
      data: {},
    },
  ],
};

describe("VideoLearningWorkspace", () => {
  it("renders the three-column learning workspace around the video conversation", () => {
    const html = renderToStaticMarkup(
      <VideoLearningWorkspace
        conversationId="0198c7a0-6f66-7c75-a318-acde48001122"
        video={video}
      />,
    );

    expect(html).toContain('aria-label="视频处理工作台"');
    expect(html).toContain('aria-label="视频会话侧栏"');
    expect(html).toContain('role="log"');
    expect(html).toContain('aria-label="内容脉络"');
    expect(html).toContain("查看未完成原因");
    expect(html).toContain("视频分析未完成");
    expect(html).not.toContain("提取完成");
    expect(html).not.toContain("内容已整理");
    expect(html).not.toContain("视频内容概要");
    expect(html).toContain("公开视频简介");
    expect(html).not.toContain("查看私教解读");
    expect(html).toContain("暂无私教解读");
    expect(html).toContain("仅公开信息");
    expect(html).not.toContain("已完成 2 个阶段");
    expect(html).not.toContain("2/2");
    expect(html).toContain('placeholder="取得语音转写后才能继续提问"');
    expect(html).toContain('aria-label="继续对话" disabled=""');
    expect(html).not.toContain("result?url=");
    expect(html).toContain("内容脉络");
    expect(html).toContain("内容笔记");
  });

  it("marks the workflow complete only when transcript-grounded analysis exists", () => {
    const html = renderToStaticMarkup(
      <VideoLearningWorkspace
        conversationId="0198c7a0-6f66-7c75-a318-acde48001122"
        video={{
          ...video,
          status: "analyzed",
          transcript: "这是一段来自视频语音的完整转写。",
          coach_interpretation: {
            summary: "视频围绕转写中出现的主题展开。",
            key_points: ["关键点来自真实转写。"],
            questions: [],
          },
        }}
      />,
    );

    expect(html).toContain("视频分析完成");
    expect(html).toContain("查看思考过程");
    expect(html).toContain("查看私教解读");
    expect(html).toContain("视频内容概要");
    expect(html).toContain('placeholder="就这条视频继续提问…"');
    expect(html).not.toContain('aria-label="继续对话" disabled=""');
    expect(html).not.toContain("视频分析未完成");
    expect(html).not.toContain("查看未完成原因");
  });
});
