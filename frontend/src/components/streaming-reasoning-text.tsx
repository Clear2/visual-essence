"use client";

import React, { useEffect, useRef, useState } from "react";

function sharedPrefixLength(previous: string, next: string) {
  const limit = Math.min(previous.length, next.length);
  let index = 0;
  while (index < limit && previous[index] === next[index]) {
    index += 1;
  }
  return index;
}

export function StreamingReasoningText({ text }: { text: string }) {
  const [visibleText, setVisibleText] = useState(text);
  const previousText = useRef(text);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      previousText.current = text;
      const reducedMotionFrame = window.requestAnimationFrame(() => {
        setVisibleText(text);
      });
      return () => window.cancelAnimationFrame(reducedMotionFrame);
    }

    const stableCharacters = sharedPrefixLength(previousText.current, text);
    let visibleCharacters = stableCharacters;
    let timer: number | undefined;
    previousText.current = text;
    const charactersPerTick = Math.max(1, Math.ceil(text.length / 60));
    const frame = window.requestAnimationFrame(() => {
      setVisibleText(text.slice(0, stableCharacters));
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
