import type { Metadata } from "next";

import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "Visual Essence — 提取视频里的真正内容",
  description:
    "粘贴公开视频链接，提取标题、作者和结构化视频信息。首期支持抖音。",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
