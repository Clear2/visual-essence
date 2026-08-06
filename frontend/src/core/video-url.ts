export type VideoUrlValidation =
  { ok: true; url: string } | { ok: false; error: string };

const DOUYIN_HOSTS = new Set(["douyin.com", "iesdouyin.com"]);
const URL_PATTERN = /https?:\/\/[^\s<>"']+/i;
const TRAILING_PUNCTUATION = /[，。！？、；：,.!?;:)}\]]+$/;

function extractUrl(value: string) {
  const match = value.trim().match(URL_PATTERN);
  return match?.[0].replace(TRAILING_PUNCTUATION, "") ?? "";
}

function isDouyinHost(hostname: string) {
  const normalizedHost = hostname.toLowerCase().replace(/^www\./, "");
  return [...DOUYIN_HOSTS].some(
    (host) => normalizedHost === host || normalizedHost.endsWith(`.${host}`),
  );
}

export function validateDouyinUrl(value: string): VideoUrlValidation {
  if (!value.trim()) {
    return { ok: false, error: "先粘贴一条抖音分享链接。" };
  }

  const extractedUrl = extractUrl(value);
  if (!extractedUrl) {
    return { ok: false, error: "没有找到有效链接，请检查后重新粘贴。" };
  }

  try {
    const url = new URL(extractedUrl);
    if (!isDouyinHost(url.hostname)) {
      return {
        ok: false,
        error: "第一期仅支持抖音链接，Bilibili 和 YouTube 即将开放。",
      };
    }

    return { ok: true, url: url.toString() };
  } catch {
    return { ok: false, error: "链接格式不正确，请粘贴完整的抖音分享链接。" };
  }
}

export function buildConversationResultHref(conversationId: string) {
  return `/result?${new URLSearchParams({ id: conversationId }).toString()}`;
}
