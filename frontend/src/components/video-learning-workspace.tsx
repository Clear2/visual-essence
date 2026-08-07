"use client";

import {
  ArrowUp,
  BookOpen,
  ChevronLeft,
  FileText,
  Flame,
  HelpCircle,
  House,
  LoaderCircle,
  Menu,
  MessageSquare,
  MoreHorizontal,
  PanelLeftClose,
  Paperclip,
  Phone,
  Plus,
  Route,
  Settings,
  SlidersHorizontal,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  Wrench,
  X,
} from "lucide-react";
import Link from "next/link";
import React from "react";
import { useEffect, useState } from "react";

import { ProcessingTrace } from "@/components/processing-trace";
import { VideoCoachInterpretation } from "@/components/video-coach-interpretation";
import { VideoResult } from "@/components/video-result";
import {
  type ConversationMessage,
  getVideoConversation,
  sendConversationMessage,
  type VideoContent,
  VideoExtractionApiError,
} from "@/core/api/videos";
import { buildConversationResultHref } from "@/core/video-url";

type VideoLearningWorkspaceProps = {
  conversationId: string;
  video: VideoContent;
};

type DetailTab = "context" | "notes";

function formatDuration(duration: number | null) {
  if (!duration) {
    return "时长未知";
  }

  return `${Math.round(duration)} 秒`;
}

export function VideoLearningWorkspace({
  conversationId,
  video,
}: VideoLearningWorkspaceProps) {
  const hasCoachInterpretation = Boolean(
    video.transcript && video.coach_interpretation,
  );
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailTab, setDetailTab] = useState<DetailTab>("context");
  const [coachOpen, setCoachOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [sending, setSending] = useState(false);
  const [chatError, setChatError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    getVideoConversation(conversationId, { signal: controller.signal })
      .then((conversation) => setMessages(conversation.messages))
      .catch(() => undefined);
    return () => controller.abort();
  }, [conversationId]);

  function openRoadmap() {
    setCoachOpen(false);
    setDetailOpen(true);
  }

  function openCoachInterpretation() {
    if (!hasCoachInterpretation) {
      return;
    }
    setCoachOpen(true);
    setDetailOpen(true);
  }

  function closeDetailPanel() {
    setCoachOpen(false);
    setDetailOpen(false);
  }

  async function copyResult() {
    const text = [
      video.title,
      video.description,
      `作者：${video.author.name || "未知作者"}`,
      video.canonical_url,
    ]
      .filter(Boolean)
      .join("\n");

    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  async function submitQuestion(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = question.trim();
    if (!content || sending || !video.transcript) {
      return;
    }

    const optimisticUserMessage: ConversationMessage = {
      id: `pending-${Date.now()}`,
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };
    setMessages((current) => [...current, optimisticUserMessage]);
    setQuestion("");
    setChatError("");
    setSending(true);
    try {
      const assistantMessage = await sendConversationMessage(
        conversationId,
        content,
      );
      setMessages((current) => [...current, assistantMessage]);
    } catch (cause) {
      setChatError(
        cause instanceof VideoExtractionApiError
          ? cause.message
          : "LLM 暂时无法回答这个问题。",
      );
    } finally {
      setSending(false);
    }
  }

  return (
    <main
      className={[
        "learning-workspace",
        leftCollapsed ? "learning-workspace--left-collapsed" : "",
        coachOpen ? "learning-workspace--coach-open" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      aria-label="视频处理工作台"
    >
      <button
        type="button"
        className={
          mobileNavOpen
            ? "workspace-scrim workspace-scrim--open"
            : "workspace-scrim"
        }
        aria-label="关闭侧栏"
        onClick={() => setMobileNavOpen(false)}
      />

      <aside
        className="workspace-left"
        aria-label="视频会话侧栏"
        data-mobile-open={mobileNavOpen}
      >
        <div className="workspace-left__brand-row">
          <Link className="workspace-brand" href="/">
            <span className="workspace-brand__mark" aria-hidden="true" />
            <span>Visual Essence</span>
          </Link>
          <button
            type="button"
            aria-label="折叠侧栏"
            onClick={() => setLeftCollapsed(true)}
          >
            <ChevronLeft size={17} strokeWidth={1.7} />
          </button>
        </div>

        <Link className="workspace-new-session" href="/#extractor">
          <Plus size={17} strokeWidth={1.8} />
          <span>新解析</span>
        </Link>

        <div className="workspace-session-scroll">
          <section className="workspace-session-group">
            <div className="workspace-session-group__title">
              <span>{hasCoachInterpretation ? "已完成" : "未完成"}</span>
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
                <strong>{video.title}</strong>
                <small>
                  {hasCoachInterpretation ? "内容已解读" : "仅公开信息"}
                </small>
              </span>
            </Link>
          </section>

          <section className="workspace-session-group">
            <div className="workspace-session-group__title">
              <span>最近内容</span>
              <small>1</small>
            </div>
            <div className="workspace-session workspace-session--muted">
              <span className="workspace-session__icon">
                <MessageSquare size={13} strokeWidth={1.7} />
              </span>
              <span className="workspace-session__copy">
                <strong>{conversationId}</strong>
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
          <button type="button">
            <MoreHorizontal size={16} strokeWidth={1.7} />
            更多
          </button>
        </div>
      </aside>

      {leftCollapsed && (
        <button
          type="button"
          className="workspace-left-restore"
          aria-label="展开侧栏"
          onClick={() => setLeftCollapsed(false)}
        >
          <PanelLeftClose size={17} strokeWidth={1.7} />
        </button>
      )}

      <section className="workspace-center">
        <header className="workspace-topbar">
          <button
            type="button"
            className="workspace-mobile-menu"
            aria-label="打开侧栏"
            onClick={() => setMobileNavOpen(true)}
          >
            <Menu size={19} strokeWidth={1.8} />
          </button>
          <h1>{video.title}</h1>
          <div className="workspace-topbar__actions">
            <span>
              {hasCoachInterpretation ? "视频分析完成" : "视频分析未完成"}
            </span>
            <span className="workspace-public-badge">公开</span>
            <button type="button" aria-label="设置">
              <Settings size={16} strokeWidth={1.7} />
            </button>
            <button type="button" aria-label="语音通话">
              <Phone size={16} strokeWidth={1.7} />
            </button>
            <button type="button" aria-label="更多操作">
              <MoreHorizontal size={17} strokeWidth={1.7} />
            </button>
          </div>
          <button
            type="button"
            className="workspace-mobile-roadmap"
            aria-label="打开内容脉络"
            onClick={openRoadmap}
          >
            <Route size={17} strokeWidth={1.7} />
            <span>内容脉络</span>
          </button>
        </header>

        <div className="workspace-feed" role="log" aria-label="视频内容对话">
          <article className="workspace-user-message">
            <p>{video.source_url}</p>
            <time>刚刚</time>
          </article>

          <article className="workspace-assistant-message">
            <ProcessingTrace
              steps={video.processing_trace}
              label={hasCoachInterpretation ? "查看思考过程" : "查看未完成原因"}
            />

            <p className="workspace-assistant-message__intro">
              {hasCoachInterpretation
                ? "视频分析已完成——已经取得语音转写，并由 LLM 生成结构化私教解读。"
                : "处理已经结束，但视频内容分析未完成；本次只保留已验证的公开信息。"}
            </p>

            <VideoResult
              video={video}
              showProcessingTrace={false}
              onOpenInterpretation={
                hasCoachInterpretation ? openCoachInterpretation : undefined
              }
            />

            <section className="workspace-digest">
              <h2>
                {hasCoachInterpretation ? "视频内容概要" : "公开视频简介"}
              </h2>
              <p>{video.description || "该视频没有提供额外描述。"}</p>
              <dl>
                <div>
                  <dt>作者</dt>
                  <dd>{video.author.name || "未知作者"}</dd>
                </div>
                <div>
                  <dt>时长</dt>
                  <dd>{formatDuration(video.duration_seconds)}</dd>
                </div>
                <div>
                  <dt>平台</dt>
                  <dd>抖音公开页面</dd>
                </div>
              </dl>
            </section>

            <footer className="workspace-message-actions">
              <time>刚刚</time>
              <button type="button" aria-label="复制结果" onClick={copyResult}>
                <FileText size={14} strokeWidth={1.6} />
                {copied ? "已复制" : "复制"}
              </button>
              <button
                type="button"
                aria-label="有帮助"
                aria-pressed={feedback === "up"}
                onClick={() => setFeedback(feedback === "up" ? null : "up")}
              >
                <ThumbsUp size={14} strokeWidth={1.6} />
              </button>
              <button
                type="button"
                aria-label="没有帮助"
                aria-pressed={feedback === "down"}
                onClick={() => setFeedback(feedback === "down" ? null : "down")}
              >
                <ThumbsDown size={14} strokeWidth={1.6} />
              </button>
            </footer>
          </article>

          {messages.map((message) =>
            message.role === "user" ? (
              <article className="workspace-user-message" key={message.id}>
                <p>{message.content}</p>
                <time>刚刚</time>
              </article>
            ) : (
              <article className="workspace-assistant-message" key={message.id}>
                <p className="workspace-assistant-message__intro">
                  {message.content}
                </p>
              </article>
            ),
          )}

          {sending && (
            <article className="workspace-assistant-message" aria-live="polite">
              <p className="workspace-assistant-message__intro">
                <LoaderCircle className="spin" size={16} strokeWidth={1.7} />
                LLM 正在结合视频转写思考这个问题…
              </p>
            </article>
          )}

          {chatError && (
            <article className="workspace-assistant-message" role="alert">
              <p className="workspace-assistant-message__intro">{chatError}</p>
            </article>
          )}
        </div>

        <nav className="workspace-turns" aria-label="对话轮次">
          <button type="button">第 1 轮：提交视频链接</button>
          <button type="button">第 2 轮：整理公开内容</button>
        </nav>

        <form className="workspace-composer" onSubmit={submitQuestion}>
          <div className="workspace-composer__input-row">
            <button type="button" aria-label="上传学习材料">
              <Paperclip size={17} strokeWidth={1.7} />
            </button>
            <input
              type="text"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder={
                video.transcript
                  ? "就这条视频继续提问…"
                  : "取得语音转写后才能继续提问"
              }
              aria-label="继续对话"
              disabled={sending || !video.transcript}
            />
            <button
              type="submit"
              aria-label="发送"
              disabled={sending || !video.transcript || !question.trim()}
            >
              {sending ? (
                <LoaderCircle className="spin" size={17} strokeWidth={1.7} />
              ) : (
                <ArrowUp size={17} strokeWidth={1.8} />
              )}
            </button>
          </div>
          <div className="workspace-composer__tools">
            <button type="button">
              <Flame size={14} strokeWidth={1.7} />
              严格处理
            </button>
            <button type="button" aria-label="工具">
              <Wrench size={14} strokeWidth={1.7} />
            </button>
            <button type="button" aria-label="帮助">
              <HelpCircle size={14} strokeWidth={1.7} />
            </button>
            <span>Enter 发送</span>
          </div>
        </form>
      </section>

      <button
        type="button"
        className={
          detailOpen
            ? "workspace-detail-scrim workspace-detail-scrim--open"
            : "workspace-detail-scrim"
        }
        aria-label={coachOpen ? "关闭私教解读" : "关闭内容脉络"}
        onClick={closeDetailPanel}
      />

      <aside
        className="workspace-right"
        aria-label={coachOpen ? "私教解读" : "内容脉络"}
        data-mobile-open={detailOpen}
        data-view={coachOpen ? "coach" : "learning"}
      >
        {coachOpen ? (
          <>
            <div className="workspace-coach-header">
              <h2>
                <FileText size={16} strokeWidth={1.7} aria-hidden="true" />
                私教解读
              </h2>
              <button
                type="button"
                aria-label="关闭私教解读"
                onClick={closeDetailPanel}
              >
                <X size={17} strokeWidth={1.7} />
              </button>
            </div>
            <VideoCoachInterpretation video={video} />
          </>
        ) : (
          <>
            <div className="workspace-right__title-row">
              <h2>{video.title}</h2>
              <button
                type="button"
                aria-label="关闭内容脉络"
                onClick={closeDetailPanel}
              >
                <ChevronLeft size={16} strokeWidth={1.7} />
              </button>
            </div>

            <div
              className="workspace-right__tabs"
              role="tablist"
              aria-label="详情视图"
            >
              <button
                type="button"
                role="tab"
                aria-selected={detailTab === "context"}
                onClick={() => setDetailTab("context")}
              >
                内容脉络
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={detailTab === "notes"}
                onClick={() => setDetailTab("notes")}
              >
                内容笔记
              </button>
            </div>

            {detailTab === "context" ? (
              <div className="workspace-roadmap">
                <div className="workspace-context-summary">
                  <span>基于当前可验证内容</span>
                  <p>
                    {video.coach_interpretation?.summary ??
                      "本次没有取得可验证的完整转写，因此不从标题或描述推断视频内容。"}
                  </p>
                </div>
              </div>
            ) : (
              <div className="workspace-notes" role="tabpanel">
                <div>
                  <Sparkles size={15} strokeWidth={1.7} />
                  <span>
                    <strong>内容状态</strong>
                    <small>公开元数据已完成整理</small>
                  </span>
                </div>
                <div>
                  <BookOpen size={15} strokeWidth={1.7} />
                  <span>
                    <strong>可用信息</strong>
                    <small>标题、作者、封面、描述与时长</small>
                  </span>
                </div>
                {video.warnings.map((warning) => (
                  <div key={warning}>
                    <SlidersHorizontal size={15} strokeWidth={1.7} />
                    <span>
                      <strong>能力提示</strong>
                      <small>{warning}</small>
                    </span>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </aside>
    </main>
  );
}
