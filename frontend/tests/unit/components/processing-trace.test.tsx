import { describe, expect, it } from "@rstest/core";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import {
  buildPublicReasoningNarrative,
  ProcessingTrace,
} from "../../../src/components/processing-trace";

describe("ProcessingTrace", () => {
  const steps = [
    {
      key: "input_inspected",
      title: "不应拿事件标题补写叙事",
      detail: "这是一个直接视频链接，视频 ID 是 7420000000000000000。",
      kind: "observation",
      status: "complete",
      elapsed_ms: 12,
      data: { unrelated_internal_marker: "不应展示的数据" },
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
  ] as const;

  it("renders one continuous narrative made only from verified details", () => {
    const narrative = buildPublicReasoningNarrative([...steps]);
    const html = renderToStaticMarkup(<ProcessingTrace steps={[...steps]} />);

    expect(html).toContain("<details");
    expect(html).not.toContain("<details open");
    expect(html).toContain("查看思考过程");
    expect(narrative).toBe(
      "这是一个直接视频链接，视频 ID 是 7420000000000000000。 " +
        "公开分享页没有找到完整作品状态，不能据此继续分析。 " +
        "视频 ID 已确认，可以查询公开详情。 " +
        "正在从视频音轨中识别真实口播文本。",
    );
    expect(html).toContain(narrative);
    expect(html).not.toContain("不应拿事件标题补写叙事");
    expect(html).not.toContain("不应展示的数据");
    expect(html).not.toContain("公开推理记录");
    expect(html).not.toContain("+1.84s");
    expect(html).not.toContain("2,201,045 字节");
  });
});
