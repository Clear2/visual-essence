"use client";

import {
  ArrowUp,
  CircleDashed,
  House,
  MessageSquare,
  MoreHorizontal,
  Paperclip,
  Plus,
  Route,
} from "lucide-react";
import Link from "next/link";
import React from "react";

import { ExtractionProgress } from "@/components/extraction-progress";
import type { ProcessingTraceStep } from "@/core/api/videos";
import { buildConversationResultHref } from "@/core/video-url";

type VideoProcessingWorkspaceProps = {
  conversationId: string;
  sourceUrl: string;
  steps: ProcessingTraceStep[];
  error?: string;
};

export function VideoProcessingWorkspace({
  conversationId,
  sourceUrl,
  steps,
  error,
}: VideoProcessingWorkspaceProps) {
  return (
    <main className="learning-workspace" aria-label="视频处理工作台">
      <aside className="workspace-left" aria-label="视频会话侧栏">
        <div className="workspace-left__brand-row">
          <Link className="workspace-brand" href="/">
            <span className="workspace-brand__mark" aria-hidden="true" />
            <span>Visual Essence</span>
          </Link>
        </div>
        <Link className="workspace-new-session" href="/#extractor">
          <Plus size={17} strokeWidth={1.8} />
          <span>新解析</span>
        </Link>
        <div className="workspace-session-scroll">
          <section className="workspace-session-group">
            <div className="workspace-session-group__title">
              <span>{error ? "处理失败" : "处理中"}</span>
              <small>1</small>
            </div>
            <Link
              className="workspace-session workspace-session--active"
              href={buildConversationResultHref(conversationId)}
              aria-current="page"
            >
              <span className="workspace-session__icon">
                <Route size={13} strokeWidth={1.8} />
              </span>
              <span className="workspace-session__copy">
                <strong>{error ? "视频分析未完成" : "正在理解这条视频"}</strong>
                <small>{steps.length > 0 ? "内容持续更新中" : "准备中"}</small>
              </span>
            </Link>
          </section>
          <section className="workspace-session-group">
            <div className="workspace-session-group__title">
              <span>当前对话</span>
              <small>1</small>
            </div>
            <div className="workspace-session workspace-session--muted">
              <span className="workspace-session__icon">
                <MessageSquare size={13} strokeWidth={1.7} />
              </span>
              <span className="workspace-session__copy">
                <strong>{conversationId || "等待对话 ID"}</strong>
                <small>刚刚</small>
              </span>
            </div>
          </section>
        </div>
        <div className="workspace-left__footer">
          <span>当前视频会话</span>
          <Link href="/">
            <House size={15} strokeWidth={1.7} />
            返回首页
          </Link>
          <button type="button" aria-label="更多">
            <MoreHorizontal size={16} strokeWidth={1.7} />
          </button>
        </div>
      </aside>

      <section className="workspace-center">
        <header className="workspace-topbar">
          <h1>{error ? "视频分析未完成" : "正在理解这条视频"}</h1>
          <div className="workspace-topbar__actions">
            <span>
              {error
                ? "已停止"
                : steps.length > 0
                  ? "正在形成内容理解"
                  : "正在等待处理记录"}
            </span>
            <span className="workspace-public-badge">对话</span>
          </div>
        </header>

        <div className="workspace-feed" role="log" aria-label="视频内容对话">
          <article className="workspace-user-message">
            <p>{sourceUrl || "已提交一条抖音视频，正在读取对话内容…"}</p>
            <time>刚刚</time>
          </article>
          <article className="workspace-assistant-message">
            {error ? (
              <div className="result-status result-status--error" role="alert">
                <span className="result-status__code">ANALYSIS STOPPED</span>
                <strong>{error}</strong>
                <Link href="/#extractor">重新提交视频</Link>
              </div>
            ) : (
              <ExtractionProgress steps={steps} />
            )}
          </article>
        </div>

        <form
          className="workspace-composer"
          onSubmit={(event) => event.preventDefault()}
        >
          <div className="workspace-composer__input-row">
            <button type="button" aria-label="上传学习材料">
              <Paperclip size={17} strokeWidth={1.7} />
            </button>
            <input
              type="text"
              placeholder="分析完成后，可以继续围绕视频提问"
              aria-label="继续对话"
              disabled
            />
            <button type="submit" aria-label="发送" disabled>
              <ArrowUp size={17} strokeWidth={1.8} />
            </button>
          </div>
        </form>
      </section>

      <aside className="workspace-right" aria-label="理解状态">
        <div className="workspace-right__title-row">
          <h2>理解状态</h2>
        </div>
        <div className="workspace-roadmap">
          <div className="workspace-understanding-state">
            <strong>{error ? "内容理解已停止" : "正在形成内容脉络"}</strong>
            <p>
              {error
                ? "已保留停止前取得的真实处理记录。"
                : "中心对话只会续写后端已经确认的处理结果。"}
            </p>
          </div>
          {!error && (
            <p className="workspace-roadmap__live">
              <CircleDashed className="spin" size={12} strokeWidth={1.8} />
              等待下一条可验证内容
            </p>
          )}
        </div>
      </aside>
    </main>
  );
}
