"use client";

/**
 * HEATMAP-01 — Overlay Canvas de difusão térmica (metaballs + blur).
 * Alinhado ao viewBox lógico da planta; pointer-events none (hover no pai).
 */

import { useEffect, useMemo, useRef, useState } from "react";
import type { ForecourtLayout } from "@/types/api";
import type { ForecourtFuelEvent } from "@/lib/forecourt-fuel-dots";
import {
  computeHeatSources,
  intensityColor,
  pickHoverCell,
  type HeatCellHover,
  type HeatMode,
  type HeatSource,
} from "@/lib/forecourt-heat-engine";
import { cn } from "@/lib/utils";

type Props = {
  layout: ForecourtLayout;
  fuelEvents: ForecourtFuelEvent[];
  mode: HeatMode;
  className?: string;
  /** Expõe fontes atuais para o pai calcular hover sem bloquear o SVG. */
  onSourcesChange?: (sources: HeatSource[]) => void;
};

export function ForecourtHeatRenderer({
  layout,
  fuelEvents,
  mode,
  className,
  onSourcesChange,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [tick, setTick] = useState(0);

  const w = layout.coordinate_width || 1000;
  const h = layout.coordinate_height || 700;

  useEffect(() => {
    if (mode === "off") return;
    const id = window.setInterval(() => setTick((t) => t + 1), 12_000);
    return () => window.clearInterval(id);
  }, [mode]);

  const sources = useMemo(
    () => computeHeatSources(layout, fuelEvents, mode, Date.now()),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [layout, fuelEvents, mode, tick]
  );

  useEffect(() => {
    onSourcesChange?.(sources);
  }, [sources, onSourcesChange]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || mode === "off") return;

    const scale = Math.min(1, 900 / Math.max(w, h));
    const cw = Math.max(1, Math.round(w * scale));
    const ch = Math.max(1, Math.round(h * scale));
    canvas.width = cw;
    canvas.height = ch;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, cw, ch);
    if (!sources.length) return;

    const off = document.createElement("canvas");
    off.width = cw;
    off.height = ch;
    const octx = off.getContext("2d");
    if (!octx) return;

    octx.clearRect(0, 0, cw, ch);
    octx.globalCompositeOperation = "lighter";

    for (const s of sources) {
      const x = s.x * scale;
      const y = s.y * scale;
      const r = s.radius * scale;
      const g = octx.createRadialGradient(x, y, 0, x, y, r);
      const peak = Math.min(1, s.intensity);
      g.addColorStop(0, intensityColor(peak, 1.1));
      g.addColorStop(0.35, intensityColor(peak * 0.85, 0.75));
      g.addColorStop(0.7, intensityColor(peak * 0.45, 0.35));
      g.addColorStop(1, "rgba(0,0,0,0)");
      octx.fillStyle = g;
      octx.beginPath();
      octx.arc(x, y, r, 0, Math.PI * 2);
      octx.fill();
    }

    ctx.save();
    ctx.filter = `blur(${Math.max(8, 14 * scale)}px)`;
    ctx.globalAlpha = mode === "rush" ? 0.92 : 0.85;
    ctx.drawImage(off, 0, 0);
    ctx.restore();

    ctx.save();
    ctx.filter = `blur(${Math.max(4, 8 * scale)}px)`;
    ctx.globalAlpha = 0.45;
    ctx.globalCompositeOperation = "screen";
    ctx.drawImage(off, 0, 0);
    ctx.restore();
  }, [sources, mode, w, h]);

  if (mode === "off") return null;

  return (
    <canvas
      ref={canvasRef}
      className={cn("absolute inset-0 w-full h-full pointer-events-none", className)}
      style={{ mixBlendMode: "screen", opacity: 0.95 }}
      aria-hidden
    />
  );
}

/** Helper exportado para o pai mapear mouse → célula térmica. */
export function heatHoverAt(
  sources: HeatSource[],
  layoutW: number,
  layoutH: number,
  clientX: number,
  clientY: number,
  bounds: DOMRect
): HeatCellHover | null {
  const lx = ((clientX - bounds.left) / bounds.width) * layoutW;
  const ly = ((clientY - bounds.top) / bounds.height) * layoutH;
  return pickHoverCell(sources, lx, ly);
}
