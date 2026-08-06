"use client";

import { ArrowRight, Clipboard, LoaderCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import {
  createVideoConversation,
  VideoExtractionApiError,
} from "@/core/api/videos";
import {
  buildConversationResultHref,
  validateDouyinUrl,
} from "@/core/video-url";

type SubmissionState = "idle" | "navigating";

const platforms = [
  { name: "抖音", status: "可用", active: true },
  { name: "Bilibili", status: "即将支持", active: false },
  { name: "YouTube", status: "计划中", active: false },
] as const;

function DouyinGlyph() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
    >
      <path
        d="M14.2 4.2c.3 2.1 1.5 3.5 3.6 4.1v3.1a8 8 0 0 1-3.6-1.1v5.1a5.3 5.3 0 1 1-4.6-5.2v3.2a2.2 2.2 0 1 0 1.4 2V4.2h3.2Z"
        fill="currentColor"
      />
    </svg>
  );
}

export function VideoUrlForm() {
  const router = useRouter();
  const [value, setValue] = useState("");
  const [error, setError] = useState("");
  const [state, setState] = useState<SubmissionState>("idle");
  const inputRef = useRef<HTMLInputElement>(null);

  async function pasteFromClipboard() {
    setError("");
    setState("idle");

    try {
      const clipboardValue = await navigator.clipboard.readText();
      setValue(clipboardValue);
      inputRef.current?.focus();
    } catch {
      setError("浏览器没有开放剪贴板权限，请手动粘贴链接。 ");
    }
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setState("navigating");

    const validation = validateDouyinUrl(value);

    if (!validation.ok) {
      setState("idle");
      setError(validation.error);
      return;
    }

    setValue(validation.url);
    try {
      const conversation = await createVideoConversation(validation.url);
      router.push(buildConversationResultHref(conversation.id));
    } catch (cause) {
      setState("idle");
      setError(
        cause instanceof VideoExtractionApiError
          ? cause.message
          : "无法创建视频对话，请稍后重试。",
      );
    }
  }

  return (
    <div className="extractor-card">
      <div className="platform-tabs" role="group" aria-label="选择视频平台">
        {platforms.map((platform) => (
          <button
            key={platform.name}
            type="button"
            className={
              platform.active
                ? "platform-tab platform-tab--active"
                : "platform-tab"
            }
            disabled={!platform.active}
          >
            {platform.active && <span className="platform-tab__signal" />}
            <span>{platform.name}</span>
            <small>{platform.status}</small>
          </button>
        ))}
      </div>

      <form onSubmit={submit} noValidate>
        <div className={error ? "url-field url-field--error" : "url-field"}>
          <span className="url-field__platform">
            <DouyinGlyph />
          </span>
          <label className="sr-only" htmlFor="video-url">
            抖音分享链接
          </label>
          <input
            ref={inputRef}
            id="video-url"
            name="video-url"
            type="text"
            inputMode="url"
            autoComplete="url"
            value={value}
            placeholder="粘贴抖音链接或整段分享文字"
            aria-describedby="url-helper url-feedback"
            aria-invalid={Boolean(error)}
            onChange={(event) => {
              setValue(event.target.value);
              setError("");
              setState("idle");
            }}
          />
          {!value && (
            <button
              className="paste-button"
              type="button"
              onClick={pasteFromClipboard}
            >
              <Clipboard size={15} strokeWidth={1.8} />
              粘贴
            </button>
          )}
          <button
            className="extract-button"
            type="submit"
            aria-label="提取视频内容"
            disabled={state === "navigating"}
          >
            {state === "navigating" ? (
              <LoaderCircle className="spin" size={20} strokeWidth={1.8} />
            ) : (
              <ArrowRight size={20} strokeWidth={1.8} />
            )}
          </button>
        </div>

        <div className="field-meta">
          <p id="url-helper">支持 v.douyin.com 和 douyin.com 的公开视频链接</p>
          <span>无需下载 App</span>
        </div>

        <p
          id="url-feedback"
          className={
            error
              ? "form-feedback form-feedback--error"
              : "form-feedback form-feedback--success"
          }
          role="status"
          aria-live="polite"
        >
          {error}
        </p>
      </form>
    </div>
  );
}
