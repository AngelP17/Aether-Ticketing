"use client";

import { useEffect, useRef, useState } from "react";

export function useMountedFlag() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const raf = window.requestAnimationFrame(() => setMounted(true));
    return () => window.cancelAnimationFrame(raf);
  }, []);

  return mounted;
}

export function useElementWidth<T extends HTMLElement = HTMLDivElement>(
  fallbackWidth = 400,
  minWidth = 280
) {
  const ref = useRef<T | null>(null);
  const [width, setWidth] = useState(fallbackWidth);

  useEffect(() => {
    const node = ref.current;
    if (!node) {
      return;
    }

    const update = () => {
      const next = Math.max(minWidth, Math.floor(node.getBoundingClientRect().width));
      setWidth(next);
    };

    update();

    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", update);
      return () => window.removeEventListener("resize", update);
    }

    const observer = new ResizeObserver(() => update());
    observer.observe(node);

    return () => observer.disconnect();
  }, [fallbackWidth, minWidth]);

  return { ref, width };
}
