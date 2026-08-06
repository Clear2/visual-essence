"use client";

import React, { useEffect, useState } from "react";

export function StreamingReasoningText({ text }: { text: string }) {
  const [visibleText, setVisibleText] = useState(text);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return;
    }

    let visibleCharacters = 0;
    let timer: number | undefined;
    const charactersPerTick = Math.max(1, Math.ceil(text.length / 60));
    const frame = window.requestAnimationFrame(() => {
      setVisibleText("");
      timer = window.setInterval(() => {
        visibleCharacters = Math.min(
          text.length,
          visibleCharacters + charactersPerTick,
        );
        setVisibleText(text.slice(0, visibleCharacters));
        if (visibleCharacters >= text.length && timer !== undefined) {
          window.clearInterval(timer);
        }
      }, 18);
    });

    return () => {
      window.cancelAnimationFrame(frame);
      if (timer !== undefined) {
        window.clearInterval(timer);
      }
    };
  }, [text]);

  return (
    <span
      className="streaming-reasoning-text"
      aria-label={text}
      aria-live="polite"
    >
      {visibleText}
      <span className="streaming-reasoning-text__cursor" aria-hidden="true" />
    </span>
  );
}
