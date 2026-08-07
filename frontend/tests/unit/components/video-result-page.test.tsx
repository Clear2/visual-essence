import { describe, expect, it } from "@rstest/core";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { ExtractionProgress } from "../../../src/components/extraction-progress";
import { VideoProcessingWorkspace } from "../../../src/components/video-processing-workspace";

describe("ExtractionProgress", () => {
  it("shows completed backend stages and the active LLM phase", () => {
    const html = renderToStaticMarkup(
      <ExtractionProgress
        steps={[
          {
            key: "share_page_fetch",
            title: "公开页面信息不足",
            detail: "公开分享页没有找到完整作品状态，不能据此继续分析。",
            kind: "warning",
            status: "warning",
            elapsed_ms: 920,
            data: { reason: "incomplete_public_state" },
          },
          {
            key: "detail_api_fetch",
            title: "查询公开视频详情",
            detail: "正在读取视频 7420000000000000000 的公开详情数据。",
            kind: "tool",
            status: "running",
            elapsed_ms: 934,
            data: { video_id: "7420000000000000000" },
          },
        ]}
      />,
    );

    expect(html).toContain("正在理解这条视频");
    expect(html).toContain(
      "公开分享页没有找到完整作品状态，不能据此继续分析。",
    );
    expect(html).toContain("正在读取视频 7420000000000000000 的公开详情数据。");
    expect(html).not.toContain("查询公开视频详情");
    expect(html).not.toContain("2 个阶段");
    expect(html).not.toContain("正在调用 LLM 生成私教解读");
  });
});

describe("VideoProcessingWorkspace", () => {
  it("renders the LLM process directly inside the conversation workspace", () => {
    const html = renderToStaticMarkup(
      <VideoProcessingWorkspace
        conversationId="0198c7a0-6f66-7c75-a318-acde48001122"
        sourceUrl="https://www.douyin.com/video/7670495404269604134"
        steps={[]}
      />,
    );

    expect(html).toContain('aria-label="视频处理工作台"');
    expect(html).toContain("正在理解这条视频");
    expect(html).toContain("/result?id=0198c7a0-6f66-7c75-a318-acde48001122");
    expect(html).not.toContain("EXTRACTION / RESULT");
    expect(html).not.toContain("result?url=");
    expect(html).not.toContain("查看私教解读");
    expect(html).toContain("正在形成内容脉络");
    expect(html).not.toContain("实时处理轨迹");
    expect(html).not.toContain("0/8");
    expect(html).not.toContain("/ 8");
  });
});
