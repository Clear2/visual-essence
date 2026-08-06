import { describe, expect, it } from "@rstest/core";

import {
  parseConversationDetailsResponse,
  parseConversationMessageResponse,
  parseConversationResponse,
  parseExtractionStreamLine,
  parseVideoContentResponse,
  VideoExtractionApiError,
} from "../../../src/core/api/videos";

describe("parseVideoContentResponse", () => {
  it("accepts the backend video contract", () => {
    const result = parseVideoContentResponse({
      platform: "douyin",
      status: "analyzed",
      source_url: "https://v.douyin.com/example/",
      canonical_url: "https://www.douyin.com/video/7420000000000000000",
      video_id: "7420000000000000000",
      title: "测试视频",
      description: null,
      author: { name: "创作者", avatar_url: null },
      cover_url: null,
      playback_url: "/api/videos/7420000000000000000/playback",
      duration_seconds: 12.5,
      transcript: "视频逐一讲述北魏十一位皇帝，并介绍孝文帝改革。",
      coach_interpretation: {
        summary: "视频梳理北魏皇位传承，并把孝文帝改革作为关键转折。",
        key_points: ["迁都洛阳推动了改革。", "汉化政策改变了政治文化。"],
        questions: ["改革为何引发旧贵族反弹？"],
      },
      warnings: [],
      processing_trace: [
        {
          key: "input_inspected",
          title: "看懂了输入",
          detail: "这是一个直接视频链接。",
          kind: "observation",
          status: "complete",
          elapsed_ms: 2,
          data: { video_id: "7420000000000000000" },
        },
      ],
    });

    expect(result.title).toBe("测试视频");
    expect(result.author.name).toBe("创作者");
    expect(result.coach_interpretation?.key_points[0]).toBe(
      "迁都洛阳推动了改革。",
    );
    expect(result.playback_url).toBe(
      "/api/videos/7420000000000000000/playback",
    );
    expect(result.processing_trace[0]?.title).toBe("看懂了输入");
  });

  it("rejects a drifting backend response", () => {
    expect(() => parseVideoContentResponse({ platform: "douyin" })).toThrow(
      VideoExtractionApiError,
    );
  });
});

describe("parseExtractionStreamLine", () => {
  it("accepts a verified progress event", () => {
    const event = parseExtractionStreamLine(
      JSON.stringify({
        type: "progress",
        step: {
          key: "audio_transcription",
          title: "转写视频语音",
          detail: "正在从视频音轨中识别真实口播文本。",
          kind: "tool",
          status: "running",
          elapsed_ms: 1842,
          data: { video_id: "7420000000000000000", media_byte_size: 2201045 },
        },
      }),
    );

    expect(event.type).toBe("progress");
    if (event.type === "progress") {
      expect(event.step.key).toBe("audio_transcription");
      expect(event.step.status).toBe("running");
      expect(event.step.elapsed_ms).toBe(1842);
      expect(event.step.data.media_byte_size).toBe(2201045);
    }
  });
});

describe("parseConversationResponse", () => {
  it("accepts a server-created conversation id", () => {
    expect(
      parseConversationResponse({
        id: "0198c7a0-6f66-7c75-a318-acde48001122",
      }),
    ).toEqual({ id: "0198c7a0-6f66-7c75-a318-acde48001122" });
  });

  it("does not accept a source URL in place of an id", () => {
    expect(() =>
      parseConversationResponse({ id: "https://www.douyin.com/video/1" }),
    ).toThrow(VideoExtractionApiError);
  });
});

describe("parseConversationDetailsResponse", () => {
  it("restores the persisted analyzed video with the conversation", () => {
    const result = parseConversationDetailsResponse({
      id: "0198c7a0-6f66-7c75-a318-acde48001122",
      video: {
        platform: "douyin",
        status: "analyzed",
        source_url: "https://v.douyin.com/example/",
        canonical_url: "https://www.douyin.com/video/7420000000000000000",
        video_id: "7420000000000000000",
        title: "测试视频",
        description: null,
        author: { name: "创作者", avatar_url: null },
        cover_url: null,
        playback_url: "/api/videos/7420000000000000000/playback",
        duration_seconds: 12.5,
        transcript: "已经完成的视频转写。",
        coach_interpretation: null,
        warnings: [],
        processing_trace: [],
      },
      messages: [],
    });

    expect(result.video?.status).toBe("analyzed");
    expect(result.video?.transcript).toBe("已经完成的视频转写。");
  });
});

describe("parseConversationMessageResponse", () => {
  it("accepts a persisted assistant reply", () => {
    const result = parseConversationMessageResponse({
      message: {
        id: "0198c7a0-6f66-7c75-a318-acde48001123",
        role: "assistant",
        content: "ask after 表示问候或打听某人的近况。",
        created_at: "2026-08-06T08:30:00+00:00",
      },
    });

    expect(result.message.role).toBe("assistant");
    expect(result.message.content).toContain("问候");
  });
});
