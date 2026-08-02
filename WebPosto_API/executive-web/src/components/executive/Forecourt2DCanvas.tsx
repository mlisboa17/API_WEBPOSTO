"use client";

/**
 * FORECOURT-LAYOUT-02 — Planta operacional 2D (SVG dinâmico).
 * Geometrias + pontos de abastecimento via layout/API (sem coords hardcoded).
 */

import { useCallback, useId, useMemo, useRef, useState, type ReactNode } from "react";
import type {
  ForecourtIsland,
  ForecourtLayout,
  ForecourtPosition,
} from "@/types/api";
import type { ForecourtFuelDot, ForecourtFuelEvent } from "@/lib/forecourt-fuel-dots";
import { mapFuelEventsToDots } from "@/lib/forecourt-fuel-dots";
import type { HeatCellHover, HeatMode, HeatSource } from "@/lib/forecourt-heat-engine";
import {
  ForecourtHeatRenderer,
  heatHoverAt,
} from "@/components/executive/ForecourtHeatRenderer";
import { cn } from "@/lib/utils";

type Selection =
  | { kind: "island"; code: string }
  | { kind: "position"; code: string }
  | { kind: "fuel"; id: string }
  | null;

type Props = {
  layout: ForecourtLayout;
  fuelEvents?: ForecourtFuelEvent[];
  className?: string;
};

function padBico(n: number) {
  return String(n).padStart(3, "0");
}

function fuelFromLabel(label?: string) {
  if (!label) return "—";
  return label.replace(/^\d+\s*/, "").trim() || label;
}

function islandLabel(code: string, name?: string) {
  const raw = (name || code || "").replace(/_/g, " ");
  return raw.toUpperCase();
}

function orientStyle(orientation: string) {
  const o = (orientation || "").toUpperCase();
  if (o === "AVENIDA") return { stroke: "#38bdf8", fill: "#0c1929", tag: "#7dd3fc" };
  if (o === "CONVENIENCIA") return { stroke: "#a78bfa", fill: "#15122a", tag: "#c4b5fd" };
  if (o === "GNV") return { stroke: "#34d399", fill: "#0a1f1a", tag: "#6ee7b7" };
  // UNCONFIRMED / SENSOR / outros
  return { stroke: "#94a3b8", fill: "#121826", tag: "#cbd5e1" };
}

/** Zonas: geometria do seed quando presente; senão bbox das ilhas; fallback orientação. */
function deriveZones(layout: ForecourtLayout) {
  const w = layout.coordinate_width || 1000;
  const h = layout.coordinate_height || 700;
  const pad = 16;

  if ((layout.zones?.length || 0) > 0) {
    return (layout.zones || []).map((z) => {
      if (
        z.x != null &&
        z.y != null &&
        z.width != null &&
        z.height != null &&
        Number(z.width) > 0 &&
        Number(z.height) > 0
      ) {
        return {
          code: z.code,
          label: (z.name || z.code).toUpperCase(),
          x: Number(z.x),
          y: Number(z.y),
          width: Number(z.width),
          height: Number(z.height),
        };
      }
      const islands = layout.islands.filter((i) => i.zone_code === z.code);
      if (!islands.length) {
        return { code: z.code, label: z.name || z.code, x: pad, y: pad, width: w - pad * 2, height: 80 };
      }
      const minX = Math.min(...islands.map((i) => i.x)) - 24;
      const minY = Math.min(...islands.map((i) => i.y)) - 36;
      const maxX = Math.max(...islands.map((i) => i.x + i.width)) + 24;
      const maxY = Math.max(...islands.map((i) => i.y + i.height)) + 24;
      return {
        code: z.code,
        label: (z.name || z.code).toUpperCase(),
        x: Math.max(pad, minX),
        y: Math.max(pad, minY),
        width: Math.min(w - pad * 2, maxX - Math.max(pad, minX)),
        height: Math.min(h - pad * 2, maxY - Math.max(pad, minY)),
      };
    });
  }

  const byOrient = (orient: string) =>
    layout.positions.filter((p) => (p.orientation || "").toUpperCase() === orient);

  const band = (positions: ForecourtPosition[], fallbackY: number, label: string) => {
    if (!positions.length) {
      return { code: label, label, x: pad, y: fallbackY, width: w - pad * 2, height: Math.max(48, h * 0.12) };
    }
    const ys = positions.map((p) => p.y);
    const y = Math.max(pad, Math.min(...ys) - 28);
    const height = Math.max(56, Math.max(...ys) + 56 - y);
    return { code: label, label, x: pad, y, width: w - pad * 2, height: Math.min(height, h - y - pad) };
  };

  return [
    band(byOrient("CONVENIENCIA"), 16, "LOJA DE CONVENIÊNCIA"),
    band(byOrient("AVENIDA"), h * 0.55, "AVENIDA PRINCIPAL"),
  ].filter((z) => layout.positions.length === 0 || z.height > 0);
}

export function Forecourt2DCanvas({ layout, fuelEvents = [], className }: Props) {
  const uid = useId().replace(/:/g, "");
  const [hover, setHover] = useState<Selection>(null);
  const [selected, setSelected] = useState<Selection>(null);
  const [heatMode, setHeatMode] = useState<HeatMode>("realtime");
  const [heatHover, setHeatHover] = useState<HeatCellHover | null>(null);
  const [heatSources, setHeatSources] = useState<HeatSource[]>([]);
  const plantRef = useRef<HTMLDivElement>(null);
  const onSourcesChange = useCallback((s: HeatSource[]) => setHeatSources(s), []);
  const active = selected || hover;

  const w = layout.coordinate_width || 1000;
  const h = layout.coordinate_height || 700;
  const mapping = (layout.mapping_status || "").toUpperCase();
  const confirmed = mapping === "CONFIRMED";

  const zones = useMemo(() => deriveZones(layout), [layout]);
  const fuelDots = useMemo(
    () => mapFuelEventsToDots(layout, fuelEvents),
    [layout, fuelEvents]
  );

  const activityByPosition = useMemo(() => {
    const m = new Map<string, number>();
    for (const d of fuelDots) {
      m.set(d.position_code, (m.get(d.position_code) || 0) + 1);
    }
    return m;
  }, [fuelDots]);

  const maxActivity = useMemo(
    () => Math.max(1, ...activityByPosition.values(), 1),
    [activityByPosition]
  );

  const selectedIsland: ForecourtIsland | null = useMemo(() => {
    if (active?.kind !== "island") return null;
    return layout.islands.find((i) => i.code === active.code) || null;
  }, [active, layout.islands]);

  const selectedPosition: ForecourtPosition | null = useMemo(() => {
    if (active?.kind !== "position") return null;
    return layout.positions.find((p) => p.code === active.code) || null;
  }, [active, layout.positions]);

  const selectedFuel: ForecourtFuelDot | null = useMemo(() => {
    if (active?.kind !== "fuel") return null;
    return fuelDots.find((d) => String(d.id) === active.id) || null;
  }, [active, fuelDots]);

  const posW = Math.max(108, Math.min(148, w * 0.13));
  const posH = 58;

  const pendingCount = fuelDots.filter(
    (d) =>
      (d.status || "").toUpperCase().includes("PEND") ||
      (d.status || "").toUpperCase() === "RETENCAO"
  ).length;

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <div>
            <p className="text-sm font-semibold text-slate-100 tracking-tight">
              {layout.name}
            </p>
            <p className="text-[11px] text-slate-500 font-mono mt-0.5">
              v{layout.version} · {w}×{h}
            </p>
          </div>
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium",
              confirmed
                ? "border-emerald-400/40 bg-emerald-500/15 text-emerald-200"
                : "border-amber-400/40 bg-amber-500/15 text-amber-100"
            )}
          >
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                confirmed ? "bg-emerald-400" : "bg-amber-300 animate-pulse"
              )}
            />
            {confirmed ? "Mapeamento Confirmado" : "Mapeamento Provisório"}
          </span>
          {fuelDots.length > 0 && (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-orange-500/35 bg-orange-500/10 px-2.5 py-1 text-[11px] text-orange-200">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-orange-400 opacity-60" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-orange-400" />
              </span>
              Pista quente · {fuelDots.length} eventos
              {pendingCount > 0 ? ` · ${pendingCount} pend.` : ""}
            </span>
          )}
        </div>
        <p className="text-[11px] text-slate-500">
          {layout.islands.length} ilhas · {layout.positions.length} posições ·{" "}
          {fuelDots.length} abastecimentos
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-1.5">
        {(
          [
            { id: "realtime" as const, label: "🔥 Calor em Tempo Real" },
            { id: "rush" as const, label: "⏱️ Acumulado de Rush" },
            { id: "off" as const, label: "🧊 Desativar Overlay" },
          ] as const
        ).map((opt) => (
          <button
            key={opt.id}
            type="button"
            onClick={() => setHeatMode(opt.id)}
            className={cn(
              "rounded-full border px-3 py-1 text-[11px] font-medium transition-colors",
              heatMode === opt.id
                ? opt.id === "off"
                  ? "border-slate-500 bg-slate-700/40 text-slate-100"
                  : "border-orange-400/50 bg-orange-500/15 text-orange-100"
                : "border-slate-700 text-slate-400 hover:text-slate-200 hover:border-slate-500"
            )}
          >
            {opt.label}
          </button>
        ))}
        <span className="text-[10px] text-slate-600 ml-1">
          Overlay térmico · dados reais do período / pista ao vivo
        </span>
      </div>

      <div className="grid lg:grid-cols-[minmax(0,1fr)_300px] gap-3 items-stretch">
        <div className="relative rounded-xl border border-slate-700/80 bg-[#070b14] overflow-hidden shadow-[inset_0_0_80px_rgba(15,23,42,0.9)]">
          <div
            ref={plantRef}
            className="relative w-full"
            onMouseMove={(e) => {
              if (heatMode === "off" || !plantRef.current) {
                setHeatHover(null);
                return;
              }
              setHeatHover(
                heatHoverAt(
                  heatSources,
                  w,
                  h,
                  e.clientX,
                  e.clientY,
                  plantRef.current.getBoundingClientRect()
                )
              );
            }}
            onMouseLeave={() => setHeatHover(null)}
          >
          <svg
            viewBox={`0 0 ${w} ${h}`}
            width="100%"
            height="auto"
            className="block w-full h-auto max-h-[min(72vh,760px)]"
            role="img"
            aria-label={`Planta operacional 2D — ${layout.name}`}
          >
            <defs>
              <linearGradient id={`pav-${uid}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#0b1220" />
                <stop offset="55%" stopColor="#0a0f18" />
                <stop offset="100%" stopColor="#080c14" />
              </linearGradient>
              <pattern
                id={`grid-${uid}`}
                width="40"
                height="40"
                patternUnits="userSpaceOnUse"
              >
                <path
                  d="M 40 0 L 0 0 0 40"
                  fill="none"
                  stroke="#1e293b"
                  strokeWidth="0.6"
                  opacity="0.35"
                />
              </pattern>
              <radialGradient id={`heat-${uid}`} cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#fb923c" stopOpacity="0.35" />
                <stop offset="55%" stopColor="#f97316" stopOpacity="0.12" />
                <stop offset="100%" stopColor="#f97316" stopOpacity="0" />
              </radialGradient>
              <filter id={`glow-${uid}`} x="-40%" y="-40%" width="180%" height="180%">
                <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#38bdf8" floodOpacity="0.55" />
              </filter>
              <filter id={`glow-amber-${uid}`} x="-40%" y="-40%" width="180%" height="180%">
                <feDropShadow dx="0" dy="0" stdDeviation="3.5" floodColor="#fbbf24" floodOpacity="0.65" />
              </filter>
              <filter id={`dot-glow-${uid}`} x="-80%" y="-80%" width="260%" height="260%">
                <feGaussianBlur stdDeviation="2.2" result="b" />
                <feMerge>
                  <feMergeNode in="b" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            {/* Pavimento */}
            <rect x={0} y={0} width={w} height={h} fill={`url(#pav-${uid})`} />
            <rect x={0} y={0} width={w} height={h} fill={`url(#grid-${uid})`} />
            {/* faixa central sutil */}
            <line
              x1={w * 0.08}
              y1={h * 0.5}
              x2={w * 0.92}
              y2={h * 0.5}
              stroke="#334155"
              strokeWidth={2}
              strokeDasharray="14 10"
              opacity={0.25}
            />

            {/* Zonas (geometria do layout/seed) */}
            {zones.map((z) => {
              const isGnv = String(z.code || "").includes("GNV");
              return (
                <g key={z.code || z.label} opacity={0.95}>
                  <rect
                    x={z.x}
                    y={z.y}
                    width={z.width}
                    height={z.height}
                    rx={16}
                    fill={isGnv ? "#0a1a16" : "#0f172a"}
                    fillOpacity={0.55}
                    stroke={isGnv ? "#065f46" : "#334155"}
                    strokeWidth={1.5}
                    strokeDasharray="6 5"
                  />
                  <rect
                    x={z.x + 10}
                    y={z.y + 8}
                    width={Math.min(320, z.width - 20)}
                    height={22}
                    rx={6}
                    fill="#020617"
                    fillOpacity={0.72}
                  />
                  <text
                    x={z.x + 20}
                    y={z.y + 23}
                    fill={isGnv ? "#6ee7b7" : "#94a3b8"}
                    fontSize={11}
                    fontWeight={600}
                    letterSpacing="0.1em"
                    fontFamily="ui-sans-serif, system-ui, sans-serif"
                  >
                    {z.label}
                  </text>
                </g>
              );
            })}

            {/* Marcadores orientativos (ex. BR-101) — vindos do layout.markers */}
            {(layout.markers || []).map((m) => (
              <g key={m.code}>
                <rect
                  x={m.x - 42}
                  y={m.y - 14}
                  width={84}
                  height={26}
                  rx={6}
                  fill="#14532d"
                  stroke="#4ade80"
                  strokeWidth={1.5}
                />
                <text
                  x={m.x}
                  y={m.y + 4}
                  textAnchor="middle"
                  fill="#bbf7d0"
                  fontSize={12}
                  fontWeight={700}
                  fontFamily="ui-sans-serif, system-ui, sans-serif"
                  letterSpacing="0.06em"
                >
                  {(m.label || m.code).toUpperCase()}
                </text>
              </g>
            ))}

            {/* Halos estáticos só quando overlay térmico desligado */}
            {heatMode === "off" &&
              layout.positions.map((pos) => {
                const count = activityByPosition.get(pos.code) || 0;
                if (count < 1) return null;
                const intensity = count / maxActivity;
                const cx = pos.x + posW / 2;
                const cy = pos.y + posH / 2;
                return (
                  <circle
                    key={`heat-${pos.code}`}
                    cx={cx}
                    cy={cy}
                    r={28 + intensity * 36}
                    fill={`url(#heat-${uid})`}
                    opacity={0.35 + intensity * 0.45}
                    style={{ pointerEvents: "none" }}
                  />
                );
              })}

            {/* Ilhas */}
            {layout.islands.map((isl) => {
              const isHot = active?.kind === "island" && active.code === isl.code;
              const zoneCode = isl.zone_code || "";
              const isGnv = zoneCode.includes("GNV") || /GNV/i.test(isl.code + (isl.name || ""));
              return (
                <g
                  key={isl.id || isl.code}
                  style={{ cursor: "pointer" }}
                  onMouseEnter={() => setHover({ kind: "island", code: isl.code })}
                  onMouseLeave={() => setHover(null)}
                  onClick={() =>
                    setSelected((cur) =>
                      cur?.kind === "island" && cur.code === isl.code
                        ? null
                        : { kind: "island", code: isl.code }
                    )
                  }
                >
                  <rect
                    x={isl.x + 3}
                    y={isl.y + 4}
                    width={isl.width}
                    height={isl.height}
                    rx={14}
                    fill="#000"
                    opacity={0.35}
                  />
                  <rect
                    x={isl.x}
                    y={isl.y}
                    width={isl.width}
                    height={isl.height}
                    rx={14}
                    fill={isHot ? "#152033" : isGnv ? "#0d1c18" : "#101826"}
                    stroke={isHot ? "#38bdf8" : isGnv ? "#34d399" : "#64748b"}
                    strokeWidth={isHot ? 2.5 : 1.75}
                    filter={isHot ? `url(#glow-${uid})` : undefined}
                  />
                  <rect
                    x={isl.x + 8}
                    y={isl.y + 8}
                    width={isl.width - 16}
                    height={3}
                    rx={1.5}
                    fill={isGnv ? "#34d399" : "#475569"}
                    opacity={0.7}
                  />
                  <text
                    x={isl.x + 16}
                    y={isl.y + 30}
                    fill="#f1f5f9"
                    fontSize={14}
                    fontWeight={700}
                    fontFamily="ui-monospace, monospace"
                  >
                    {islandLabel(isl.code, isl.name)}
                  </text>
                  {zoneCode ? (
                    <text
                      x={isl.x + 16}
                      y={isl.y + 48}
                      fill="#64748b"
                      fontSize={10}
                      fontFamily="ui-sans-serif, system-ui, sans-serif"
                    >
                      {zoneCode.replace("ZONE_", "")}
                    </text>
                  ) : null}
                </g>
              );
            })}

            {/* Posições / bombas */}
            {layout.positions.map((pos) => {
              const style = orientStyle(pos.orientation);
              const isHot = active?.kind === "position" && active.code === pos.code;
              const count = activityByPosition.get(pos.code) || 0;
              return (
                <g
                  key={pos.id || pos.code}
                  style={{ cursor: "pointer" }}
                  onMouseEnter={() => setHover({ kind: "position", code: pos.code })}
                  onMouseLeave={() => setHover(null)}
                  onClick={() =>
                    setSelected((cur) =>
                      cur?.kind === "position" && cur.code === pos.code
                        ? null
                        : { kind: "position", code: pos.code }
                    )
                  }
                >
                  <rect
                    x={pos.x}
                    y={pos.y}
                    width={posW}
                    height={posH}
                    rx={10}
                    fill={isHot ? "#1c2436" : style.fill}
                    stroke={isHot ? "#fbbf24" : style.stroke}
                    strokeWidth={isHot ? 2.5 : 1.75}
                    filter={isHot ? `url(#glow-amber-${uid})` : undefined}
                  />
                  {/* “bico” visual */}
                  <circle
                    cx={pos.x + posW - 14}
                    cy={pos.y + 14}
                    r={5}
                    fill={style.stroke}
                    opacity={0.9}
                  />
                  <text
                    x={pos.x + 10}
                    y={pos.y + 18}
                    fill="#f8fafc"
                    fontSize={10}
                    fontWeight={600}
                    fontFamily="ui-monospace, monospace"
                  >
                    {pos.code.length > 18 ? pos.code.slice(-16) : pos.code}
                  </text>
                  <text
                    x={pos.x + 10}
                    y={pos.y + 34}
                    fill={style.tag}
                    fontSize={9}
                    fontWeight={600}
                    fontFamily="ui-sans-serif, system-ui, sans-serif"
                  >
                    {(pos.pump_name || `BOMBA ${pos.pump_id}`).toUpperCase()}
                    {" · "}
                    {(pos.orientation || "—").toUpperCase()}
                  </text>
                  <text
                    x={pos.x + 10}
                    y={pos.y + 48}
                    fill="#94a3b8"
                    fontSize={9}
                    fontFamily="ui-monospace, monospace"
                  >
                    {pos.nozzles.map((n) => padBico(n.nozzle_id)).join(" · ")}
                    {count > 0 ? `  ·  ${count}×` : ""}
                  </text>
                </g>
              );
            })}

            {/* Pontos de abastecimento (sutis quando heat overlay ativo) */}
            <g aria-label="Abastecimentos" opacity={heatMode === "off" ? 1 : 0.55}>
              {fuelDots.map((dot) => {
                const id = String(dot.id);
                const isHot = active?.kind === "fuel" && active.id === id;
                const pending =
                  (dot.status || "").toUpperCase().includes("PEND") ||
                  (dot.status || "").toUpperCase() === "RETENCAO";
                const r = pending ? 7.5 : 5.5;
                return (
                  <g
                    key={`fuel-${id}`}
                    style={{ cursor: "pointer" }}
                    onMouseEnter={() => setHover({ kind: "fuel", id })}
                    onMouseLeave={() => setHover(null)}
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelected((cur) =>
                        cur?.kind === "fuel" && cur.id === id
                          ? null
                          : { kind: "fuel", id }
                      );
                    }}
                  >
                    {pending && (
                      <circle
                        cx={dot.x}
                        cy={dot.y}
                        r={r + 6}
                        fill="none"
                        stroke="#fbbf24"
                        strokeWidth={1.2}
                        opacity={0.55}
                      >
                        <animate
                          attributeName="r"
                          values={`${r + 4};${r + 10};${r + 4}`}
                          dur="1.6s"
                          repeatCount="indefinite"
                        />
                        <animate
                          attributeName="opacity"
                          values="0.6;0.15;0.6"
                          dur="1.6s"
                          repeatCount="indefinite"
                        />
                      </circle>
                    )}
                    {isHot && (
                      <circle
                        cx={dot.x}
                        cy={dot.y}
                        r={r + 6}
                        fill="none"
                        stroke="#f8fafc"
                        strokeWidth={1.5}
                        opacity={0.9}
                      />
                    )}
                    <circle
                      cx={dot.x}
                      cy={dot.y}
                      r={r}
                      fill={pending ? "#fbbf24" : "#38bdf8"}
                      stroke="#020617"
                      strokeWidth={1.25}
                      filter={`url(#dot-glow-${uid})`}
                      opacity={0.95}
                    />
                  </g>
                );
              })}
            </g>
          </svg>

          {heatMode !== "off" && (
            <ForecourtHeatRenderer
              layout={layout}
              fuelEvents={fuelEvents}
              mode={heatMode}
              onSourcesChange={onSourcesChange}
            />
          )}

          {heatHover && heatMode !== "off" && (
            <div className="absolute top-2 right-2 z-10 max-w-[300px] rounded-lg border border-orange-400/40 bg-slate-950/95 px-3 py-2 text-[12px] text-slate-100 shadow-xl pointer-events-none">
              <p className="font-semibold text-orange-200 leading-snug">
                ⚡ Densidade Térmica: {heatHover.densityLabel} (
                {heatHover.count} abast/{heatHover.windowMinutes}min
                {heatHover.island_code ? ` nesta ilha` : ""})
              </p>
              <p className="text-[11px] text-slate-400 mt-1">
                {[
                  heatHover.island_code,
                  heatHover.position_code,
                  heatHover.orientation,
                  heatHover.zone_code,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            </div>
          )}
          </div>

          <div className="absolute bottom-2 left-2 right-2 flex flex-wrap items-center justify-between gap-2 pointer-events-none z-10">
            <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-700/70 bg-slate-950/90 backdrop-blur px-3 py-1.5 text-[11px] text-slate-300 shadow-lg">
              {heatMode === "off" ? (
                <>
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-sky-400 shadow-[0_0_8px_#38bdf8]" />
                    Abastecimento
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-amber-300 shadow-[0_0_8px_#fbbf24]" />
                    Pendente
                  </span>
                </>
              ) : (
                <>
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-sky-400" /> Azul ocioso
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-emerald-400" /> Fluxo
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-orange-400" /> Alta densidade
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-fuchsia-500" /> 🔥 Sobrecarga
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        <aside className="rounded-xl border border-slate-700/80 bg-gradient-to-b from-slate-900/90 to-slate-950/95 p-4 min-h-[220px] flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <p className="text-[11px] uppercase tracking-[0.14em] text-slate-500 font-semibold">
              Inspeção
            </p>
            {(selected || hover) && (
              <button
                type="button"
                className="text-[10px] text-slate-500 hover:text-slate-300"
                onClick={() => setSelected(null)}
              >
                limpar
              </button>
            )}
          </div>

          {!selectedIsland && !selectedPosition && !selectedFuel && (
            <div className="flex-1 flex flex-col justify-center text-center px-2">
              <p className="text-sm text-slate-400 leading-relaxed">
                Clique em uma <span className="text-slate-200">ilha</span>,{" "}
                <span className="text-slate-200">posição</span> ou{" "}
                <span className="text-sky-300">ponto</span> para inspecionar.
              </p>
              <p className="text-[11px] text-slate-600 mt-3">
                Halos laranja mostram onde a pista está mais quente no período.
              </p>
            </div>
          )}

          {selectedFuel && (
            <div className="space-y-2">
              <p className="text-base font-semibold text-slate-50">Abastecimento</p>
              <BadgeSoft tone="sky">Bico {padBico(selectedFuel.bico)}</BadgeSoft>
              <Row k="Posição" v={selectedFuel.position_code} />
              <Row k="Orientação" v={(selectedFuel.orientation || "—").toUpperCase()} />
              <Row k="Bomba" v={String(selectedFuel.pump_id)} />
              <Row k="Produto" v={selectedFuel.produto || "—"} />
              <Row
                k="Litros"
                v={
                  selectedFuel.litros != null
                    ? `${Number(selectedFuel.litros).toLocaleString("pt-BR", {
                        maximumFractionDigits: 3,
                      })} L`
                    : "—"
                }
              />
              <Row
                k="Valor"
                v={
                  selectedFuel.valor != null
                    ? selectedFuel.valor.toLocaleString("pt-BR", {
                        style: "currency",
                        currency: "BRL",
                      })
                    : "—"
                }
              />
              <Row k="Frentista" v={selectedFuel.frentistaNome || "—"} />
              <Row k="Quando" v={selectedFuel.dataHora || "—"} />
              <Row k="Status" v={selectedFuel.status || "—"} />
            </div>
          )}

          {selectedIsland && !selectedFuel && (
            <div className="space-y-2">
              <p className="text-base font-semibold text-slate-50">
                {islandLabel(selectedIsland.code, selectedIsland.name)}
              </p>
              <Row k="Código" v={selectedIsland.code} />
              <Row k="Zona" v={selectedIsland.zone_code || "—"} />
              <Row k="Coords" v={`x=${selectedIsland.x}, y=${selectedIsland.y}`} />
              <Row
                k="Dimensão"
                v={`${selectedIsland.width} × ${selectedIsland.height}`}
              />
              <Row
                k="Posições"
                v={String(
                  layout.positions.filter((p) => p.island_code === selectedIsland.code)
                    .length
                )}
              />
            </div>
          )}

          {selectedPosition && !selectedFuel && (
            <div className="space-y-2">
              <p className="text-base font-semibold text-slate-50">
                {selectedPosition.code}
              </p>
              <Row k="Nome" v={selectedPosition.name || "—"} />
              <Row
                k="Orientação"
                v={(selectedPosition.orientation || "—").toUpperCase()}
              />
              <Row
                k="Bomba"
                v={
                  selectedPosition.pump_name || `BOMBA ${selectedPosition.pump_id}`
                }
              />
              <Row k="Ilha" v={selectedPosition.island_code} />
              <Row
                k="Atividade"
                v={`${activityByPosition.get(selectedPosition.code) || 0} abast.`}
              />
              <div className="pt-2 border-t border-slate-800 mt-2">
                <p className="text-[11px] uppercase tracking-wide text-slate-500 mb-1.5">
                  Bicos ({selectedPosition.nozzles.length})
                </p>
                <ul className="space-y-1.5 max-h-48 overflow-auto pr-1">
                  {selectedPosition.nozzles.map((n) => (
                    <li
                      key={n.nozzle_id}
                      className="rounded-lg border border-slate-700/80 bg-slate-900/80 px-2.5 py-1.5 text-sm text-slate-200 font-mono"
                    >
                      <span className="text-sky-300">{padBico(n.nozzle_id)}</span>
                      <span className="text-slate-600"> · </span>
                      <span className="text-slate-300 font-sans text-[13px]">
                        {fuelFromLabel(n.label)}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function BadgeSoft({
  children,
  tone,
}: {
  children: ReactNode;
  tone: "sky" | "amber";
}) {
  return (
    <span
      className={cn(
        "inline-flex w-fit rounded-md border px-2 py-0.5 text-xs font-medium",
        tone === "sky" && "border-sky-500/40 bg-sky-500/10 text-sky-200",
        tone === "amber" && "border-amber-500/40 bg-amber-500/10 text-amber-200"
      )}
    >
      {children}
    </span>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-3 text-sm py-0.5">
      <span className="text-slate-500">{k}</span>
      <span className="text-slate-200 text-right font-mono text-xs sm:text-[13px]">
        {v}
      </span>
    </div>
  );
}
