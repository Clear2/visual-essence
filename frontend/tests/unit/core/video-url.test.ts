import { describe, expect, it } from "@rstest/core";

import {
  buildConversationResultHref,
  validateDouyinUrl,
} from "../../../src/core/video-url";

describe("validateDouyinUrl", () => {
  it("accepts a Douyin short link", () => {
    expect(validateDouyinUrl("https://v.douyin.com/abc123/")).toEqual({
      ok: true,
      url: "https://v.douyin.com/abc123/",
    });
  });

  it("extracts a link from copied share text", () => {
    expect(
      validateDouyinUrl(
        "复制打开抖音，看看这个视频 https://v.douyin.com/abc123/ 01/20",
      ),
    ).toEqual({
      ok: true,
      url: "https://v.douyin.com/abc123/",
    });
  });

  it("rejects another platform", () => {
    expect(validateDouyinUrl("https://www.bilibili.com/video/BV1xx")).toEqual({
      ok: false,
      error: "第一期仅支持抖音链接，Bilibili 和 YouTube 即将开放。",
    });
  });

  it("rejects input without a URL", () => {
    expect(validateDouyinUrl("这不是一条链接")).toEqual({
      ok: false,
      error: "没有找到有效链接，请检查后重新粘贴。",
    });
  });
});

describe("buildConversationResultHref", () => {
  it("builds a result route containing only the conversation id", () => {
    expect(
      buildConversationResultHref("0198c7a0-6f66-7c75-a318-acde48001122"),
    ).toBe("/result?id=0198c7a0-6f66-7c75-a318-acde48001122");
  });
});
