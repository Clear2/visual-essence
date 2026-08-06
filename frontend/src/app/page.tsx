import {
  ArrowDown,
  ArrowUpRight,
  Captions,
  FileText,
  ScanText,
} from "lucide-react";

import { VideoUrlForm } from "@/components/video-url-form";

function FrameMark({ compact = false }: { compact?: boolean }) {
  return (
    <span
      className={compact ? "frame-mark frame-mark--compact" : "frame-mark"}
      aria-hidden="true"
    >
      <span className="frame-mark__cyan" />
      <span className="frame-mark__rose" />
      <span className="frame-mark__ink">
        <span />
      </span>
    </span>
  );
}

export default function HomePage() {
  return (
    <main>
      <header className="site-header">
        <a className="brand" href="#top" aria-label="Visual Essence 首页">
          <FrameMark compact />
          <span>Visual Essence</span>
        </a>

        <nav className="nav-links" aria-label="主导航">
          <a href="#how-it-works">工作原理</a>
          <a href="#platforms">支持平台</a>
          <a href="#about">关于</a>
        </nav>

        <a className="header-cta" href="#extractor">
          开始提取
          <ArrowUpRight size={16} strokeWidth={1.8} />
        </a>
      </header>

      <section className="hero" id="top">
        <div className="hero-copy">
          <FrameMark />
          <p className="eyebrow">VIDEO IN · ESSENCE OUT</p>
          <h1>
            别再收藏视频了。
            <br />
            <em>把内容留下来。</em>
          </h1>
          <p className="hero-description">
            粘贴一条公开视频链接，Visual Essence
            帮你提取标题、作者与结构化视频信息。
            <br className="desktop-break" />
            第一期，从抖音开始。
          </p>
        </div>

        <div id="extractor" className="extractor-anchor">
          <VideoUrlForm />
        </div>

        <a className="journey-link" href="#how-it-works">
          看看一条视频会变成什么
          <ArrowDown size={15} strokeWidth={1.7} />
        </a>
      </section>

      <section className="process-section" id="how-it-works">
        <div className="section-heading">
          <p className="section-kicker">从链接到内容</p>
          <h2>三步，留下真正有用的部分。</h2>
          <p>不需要下载视频，也不用在进度条上反复拖动。</p>
        </div>

        <div className="content-rail" aria-label="视频内容提取流程">
          <article className="rail-step">
            <span className="rail-time">00:00</span>
            <div className="rail-dot" />
            <div className="rail-card">
              <ScanText size={21} strokeWidth={1.6} />
              <span className="rail-index">01</span>
              <h3>识别链接</h3>
              <p>解析分享地址，确认平台与公开视频信息。</p>
            </div>
          </article>

          <article className="rail-step">
            <span className="rail-time">00:08</span>
            <div className="rail-dot rail-dot--accent" />
            <div className="rail-card">
              <Captions size={21} strokeWidth={1.6} />
              <span className="rail-index">02</span>
              <h3>读懂视频</h3>
              <p>提取视频音轨并完成语音转写，保留原始表达语境。</p>
            </div>
          </article>

          <article className="rail-step">
            <span className="rail-time">00:15</span>
            <div className="rail-dot" />
            <div className="rail-card">
              <FileText size={21} strokeWidth={1.6} />
              <span className="rail-index">03</span>
              <h3>生成精华</h3>
              <p>得到可阅读、可搜索、可继续整理的内容。</p>
            </div>
          </article>
        </div>
      </section>

      <section className="platform-section" id="platforms">
        <div>
          <p className="section-kicker">支持平台</p>
          <h2>先做好一个，再走向更多。</h2>
        </div>
        <div className="platform-list">
          <div className="platform-row platform-row--active">
            <span className="platform-number">01</span>
            <strong>抖音</strong>
            <span>第一期支持</span>
          </div>
          <div className="platform-row">
            <span className="platform-number">02</span>
            <strong>Bilibili</strong>
            <span>即将支持</span>
          </div>
          <div className="platform-row">
            <span className="platform-number">03</span>
            <strong>YouTube</strong>
            <span>计划中</span>
          </div>
        </div>
      </section>

      <footer id="about">
        <a className="brand" href="#top">
          <FrameMark compact />
          <span>Visual Essence</span>
        </a>
        <p>把动态的信息，变成可以沉淀的内容。</p>
        <span>© 2026 Visual Essence</span>
      </footer>
    </main>
  );
}
