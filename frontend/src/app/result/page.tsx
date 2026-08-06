import type { Metadata } from "next";

import { VideoResultPage } from "@/components/video-result-page";

export const metadata: Metadata = {
  title: "视频提取结果 — Visual Essence",
  description: "查看视频提取结果与可验证的处理过程。",
};

type ResultPageProps = {
  searchParams: Promise<{ id?: string | string[] }>;
};

export default async function ResultPage({ searchParams }: ResultPageProps) {
  const params = await searchParams;
  const conversationId = typeof params.id === "string" ? params.id : "";

  return (
    <VideoResultPage key={conversationId} conversationId={conversationId} />
  );
}
