"use client";

import { useEffect, useRef } from "react";

// Same spacing as the old static .grid-texture pattern it replaces.
const SPACING = 28;
// How far from the pointer a dot starts feeling the pull.
const RADIUS = 140;
// Max distance a dot can be dragged, at the pointer's exact position.
const MAX_PULL = 7;

export function MagneticDots() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const dotColor = getComputedStyle(document.documentElement)
      .getPropertyValue("--foreground")
      .trim();

    const pointer = { x: -9999, y: -9999, active: false };
    let width = 0;
    let height = 0;

    function resize() {
      const parent = canvas!.parentElement;
      if (!parent) return;
      width = parent.clientWidth;
      height = parent.clientHeight;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas!.width = width * dpr;
      canvas!.height = height * dpr;
      canvas!.style.width = `${width}px`;
      canvas!.style.height = `${height}px`;
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    window.addEventListener("resize", resize);

    function handleMove(e: PointerEvent) {
      const rect = canvas!.getBoundingClientRect();
      pointer.x = e.clientX - rect.left;
      pointer.y = e.clientY - rect.top;
      pointer.active = true;
    }
    function handleLeave() {
      pointer.active = false;
    }
    window.addEventListener("pointermove", handleMove);
    window.addEventListener("pointerleave", handleLeave);

    function draw() {
      ctx!.clearRect(0, 0, width, height);
      for (let x = SPACING / 2; x < width; x += SPACING) {
        for (let y = SPACING / 2; y < height; y += SPACING) {
          let dx = 0;
          let dy = 0;
          let boost = 0;
          if (pointer.active) {
            const distX = pointer.x - x;
            const distY = pointer.y - y;
            const dist = Math.hypot(distX, distY);
            if (dist < RADIUS) {
              const pull = (1 - dist / RADIUS) * MAX_PULL;
              const angle = Math.atan2(distY, distX);
              dx = Math.cos(angle) * pull;
              dy = Math.sin(angle) * pull;
              boost = (1 - dist / RADIUS) * 0.3;
            }
          }
          ctx!.beginPath();
          ctx!.arc(x + dx, y + dy, 1, 0, Math.PI * 2);
          ctx!.fillStyle = `color-mix(in oklab, ${dotColor} ${Math.round((0.14 + boost) * 100)}%, transparent)`;
          ctx!.fill();
        }
      }
    }

    if (reduceMotion) {
      draw();
      return () => {
        window.removeEventListener("resize", resize);
        window.removeEventListener("pointermove", handleMove);
        window.removeEventListener("pointerleave", handleLeave);
      };
    }

    let raf = 0;
    function loop() {
      draw();
      raf = requestAnimationFrame(loop);
    }
    loop();

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerleave", handleLeave);
    };
  }, []);

  return (
    <canvas ref={canvasRef} className="pointer-events-none absolute inset-0" aria-hidden="true" />
  );
}
