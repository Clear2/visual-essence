import { describe, expect, it } from "@rstest/core";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { VideoResult } from "../../../src/components/video-result";

describe("VideoResult", () => {
  it("renders extracted content with its coach interpretation and process disclosure", () => {
    const html = renderToStaticMarkup(
      <VideoResult
        onOpenInterpretation={() => undefined}
        video={{
          platform: "douyin",
          status: "metadata",
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
              key: "result_ready",
              title: "公开视频信息已经整理好",
              detail: "标题、作者、封面和时长已经归一化。",
              kind: "result",
              status: "complete",
              elapsed_ms: 780,
              data: {},
            },
          ],
        }}
      />,
    );

    expect(html).toContain('aria-label="视频提取结果"');
    expect(html).toContain("把一条视频变成可以阅读的内容");
    expect(html).toContain("Visual Creator");
    expect(html).toContain("查看思考过程");
    expect(html).toContain(
      '<button type="button" class="video-result__interpretation-trigger">查看私教解读',
    );
    expect(html).not.toContain('target="_blank"');
  });
});
