import { describe, expect, it } from "@rstest/core";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { ProcessingTrace } from "../../../src/components/processing-trace";

describe("ProcessingTrace", () => {
  it("renders an evidence-backed public reasoning timeline", () => {
    const html = renderToStaticMarkup(
      <ProcessingTrace
        steps={[
          {
            key: "input_inspected",
            title: "看懂了输入",
            detail: "这是一个直接视频链接，视频 ID 是 7420000000000000000。",
            kind: "observation",
            status: "complete",
            elapsed_ms: 12,
            data: { video_id: "7420000000000000000" },
          },
          {
            key: "share_page_fetch",
            title: "公开页面信息不足",
            detail: "公开分享页没有找到完整作品状态，不能据此继续分析。",
            kind: "warning",
            status: "warning",
            elapsed_ms: 932,
            data: { reason: "incomplete_public_state" },
          },
          {
            key: "fallback_decision",
            title: "改用公开视频详情接口",
            detail: "视频 ID 已确认，可以查询公开详情。",
            kind: "decision",
            status: "complete",
            elapsed_ms: 936,
            data: { strategy: "public_detail_api" },
          },
          {
            key: "audio_transcription",
            title: "转写视频语音",
            detail: "正在从视频音轨中识别真实口播文本。",
            kind: "tool",
            status: "running",
            elapsed_ms: 1842,
            data: { media_byte_size: 2201045 },
          },
        ]}
      />,
    );

    expect(html).toContain("<details");
    expect(html).not.toContain("<details open");
    expect(html).toContain("查看思考过程");
    expect(html).toContain("公开推理记录 · 4 条活动");
    expect(html).toContain("观察");
    expect(html).toContain("注意");
    expect(html).toContain("调整");
    expect(html).toContain("工具");
    expect(html).toContain("+1.84s");
    expect(html).toContain("2,201,045 字节");
    expect(html).toContain("逐字说明来自实际执行结果");
    expect(html).not.toContain("processing-trace__index");
  });
});
