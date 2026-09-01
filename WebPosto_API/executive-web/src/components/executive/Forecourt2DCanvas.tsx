"use client";

/**
 * FORECOURT-LAYOUT-02 + HEATMAP-01
 * Planta operacional 2D (SVG) + overlay térmico contínuo.
 * Geometria 100% do layout ACTIVE; BR-101 = marcador viário (nunca ilha/calor).
 */

import { useCallback, useId, useMemo, useRef, useState, type ReactNode } from "react";
import type {
  ForecourtIsland,
  ForecourtLayout,
  ForecourtMarker,
  ForecourtPosition,
  ForecourtZone,
} from "@/types/api";
import type { ForecourtFuelEvent } from "@/lib/forecourt-fuel-dots";
import type { HeatCellHover, HeatMode, HeatSource } from "@/lib/forecourt-heat-engine";
import {
  ForecourtHeatOverlay,
  heatHoverAt,
} from "@/components/executive/ForecourtHeatOverlay";
import { cn } from "@/lib/utils";

type Selection =
  | { kind: "island"; code: string }
  | { kind: "position"; code: string }
  | null;

type Props = {
  layout: ForecourtLayout;
  fuelEvents?: ForecourtFuelEvent[];
  className?: string;
  /** Sync leaderboard → planta: realça bico ERP (nozzle_id). */
  highlightBico?: number | null;
  /** Sync leaderboard → planta: realça ilha pelo número (1, 2, …). */
  highlightIlha?: number | null;
  /** Esconde chrome pesado (útil no cockpit compacto). */
  compact?: boolean;
};

function islandNumber(code: string, name?: string): number | null {
  const m = `${code} ${name || ""}`.match(/(\d+)/);
  return m ? Number(m[1]) : null;
}

type DerivedZone = {
  code: string;
  label: string;
  x: number;
  y: number;
  width: number;
  height: number;
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

function isRoadMarker(m: ForecourtMarker) {
  const kind = String(m.kind || "").toUpperCase();
  if (kind === "ROAD") return true;
  return /^BR[-_]?\d+/i.test(m.code || m.label || "");
}

/** Ilhas operacionais — exclui qualquer código viário (defesa em profundidade). */
function operationalIslands(layout: ForecourtLayout): ForecourtIsland[] {
  const roadCodes = new Set(
    (layout.markers || []).filter(isRoadMarker).map((m) => m.code.toUpperCase())
  );
  return (layout.islands || []).filter((i) => {
    const c = (i.code || "").toUpperCase();
    if (roadCodes.has(c)) return false;
    if (/^BR[-_]?\d+/.test(c)) return false;
    return true;
  });
}

function orientStyle(orientation: string) {
  const o = (orientation || "").toUpperCase();
  if (o === "AVENIDA") return { stroke: "#38bdf8", fill: "#0c1929", tag: "#7dd3fc" };
  if (o === "CONVENIENCIA") return { stroke: "#a78bfa", fill: "#15122a", tag: "#c4b5fd" };
  if (o === "SENSOR_A") return { stroke: "#f59e0b", fill: "#1a1408", tag: "#fbbf24" };
  if (o === "SENSOR_B") return { stroke: "#fb7185", fill: "#1a0c10", tag: "#fda4af" };
  if (o === "GNV") return { stroke: "#34d399", fill: "#0a1f1a", tag: "#6ee7b7" };
  return { stroke: "#94a3b8", fill: "#121826", tag: "#cbd5e1" };
}

function orientShort(orientation: string) {
  const o = (orientation || "").toUpperCase();
  if (o === "SENSOR_A") return "SENSOR A · 3 bicos";
  if (o === "SENSOR_B") return "SENSOR B · 3 bicos";
  if (o === "AVENIDA") return "AVENIDA · 2 bicos";
  if (o === "CONVENIENCIA") return "CONVENIÊNCIA · 2 bicos";
  return o || "—";
}

function zoneFromLayout(z: ForecourtZone, layout: ForecourtLayout, pad: number): DerivedZone {
  const w = layout.coordinate_width || 1000;
  const h = layout.coordinate_height || 700;
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
  const islands = operationalIslands(layout).filter((i) => i.zone_code === z.code);
  if (!islands.length) {
    return {
      code: z.code,
      label: (z.name || z.code).toUpperCase(),
      x: pad,
      y: pad,
      width: w - pad * 2,
      height: 80,
    };
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
}

function deriveZones(layout: ForecourtLayout): DerivedZone[] {
  const w = layout.coordinate_width || 1000;
  const h = layout.coordinate_height || 700;
  const pad = 16;

  if ((layout.zones?.length || 0) > 0) {
    return (layout.zones || []).map((z) => zoneFromLayout(z, layout, pad));
  }

  const byOrient = (orient: string) =>
    layout.positions.filter((p) => (p.orientation || "").toUpperCase() === orient);

  const band = (
    positions: ForecourtPosition[],
    code: string,
    label: string
  ): DerivedZone | null => {
    if (!positions.length) return null;
    const ys = positions.map((p) => p.y);
    const y = Math.max(pad, Math.min(...ys) - 28);
    const height = Math.max(56, Math.max(...ys) + 56 - y);
    return {
      code,
      label,
      x: pad,
      y,
      width: w - pad * 2,
      height: Math.min(height, h - y - pad),
    };
  };

  return [
    band(byOrient("CONVENIENCIA"), "ZONE_CONVENIENCIA", "CONVENIÊNCIA"),
    band(byOrient("AVENIDA"), "ZONE_AVENIDA", "AVENIDA"),
  ].filter((z): z is DerivedZone => z != null);
}

function markerLabel(m: ForecourtMarker) {
  return (m.label || m.code || "").toUpperCase();
}

export function Forecourt2DCanvas({
  layout,
  fuelEvents = [],
  className,
  highlightBico = null,
  highlightIlha = null,
  compact = false,
}: Props) {
  const uid = useId().replace(/:/g, "");
  const [hover, setHover] = useState<Selection>(null);
  const [selected, setSelected] = useState<Selection>(null);
  const [heatMode, setHeatMode] = useState<HeatMode>("realtime");
  const [heatHover, setHeatHover] = useState<HeatCellHover | null>(null);
  /** Ref (não state): evita loop setState ↔ re-render do overlay térmico. */
  const heatSourcesRef = useRef<HeatSource[]>([]);
  const plantRef = useRef<HTMLDivElement>(null);
  const onSourcesChange = useCallback((s: HeatSource[]) => {
    heatSourcesRef.current = s;
  }, []);
  const active = selected || hover;
  const hlBico = highlightBico != null && highlightBico > 0 ? highlightBico : null;
  const hlIlha = highlightIlha != null && highlightIlha > 0 ? highlightIlha : null;

  const w = layout.coordinate_width || 1000;
  const h = layout.coordinate_height || 700;
  const mapping = (layout.mapping_status || "").toUpperCase();
  const confirmed = mapping === "CONFIRMED";
  const provisional = mapping === "PROVISIONAL" || (!confirmed && !!mapping);

  const zones = useMemo(() => deriveZones(layout), [layout]);
  const islands = useMemo(() => operationalIslands(layout), [layout]);
  const roadMarkers = useMemo(
    () => (layout.markers || []).filter(isRoadMarker),
    [layout.markers]
  );
  const otherMarkers = useMemo(
    () => (layout.markers || []).filter((m) => !isRoadMarker(m)),
    [layout.markers]
  );

  const selectedIsland: ForecourtIsland | null = useMemo(() => {
    if (active?.kind !== "island") return null;
    return islands.find((i) => i.code === active.code) || null;
  }, [active, islands]);

  const selectedPosition: ForecourtPosition | null = useMemo(() => {
    if (active?.kind !== "position") return null;
    return layout.positions.find((p) => p.code === active.code) || null;
  }, [active, layout.positions]);

  const posW = Math.max(108, Math.min(148, w * 0.13));
  const posH = Math.max(52, Math.min(64, h * 0.085));

  const islandPositions = (islandCode: string) =>
    layout.positions.filter((p) => p.island_code === islandCode);

  return (
    <div className={cn("space-y-3", className)}>
      {!compact ? (
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <div>
            <p className="text-sm font-semibold text-slate-100 tracking-tight">
              {layout.name}
            </p>
            <p className="text-[11px] text-slate-500 font-mono mt-0.5">
              v{layout.version} · {w}×{h} · station {layout.station_id}
            </p>
          </div>
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium",
              confirmed
                ? "border-emerald-400/40 bg-emerald-500/15 text-emerald-200"
                : "border-amber-400/40 bg-amber-500/15 text-amber-100"
            )}
            title={layout.mapping_note || undefined}
          >
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                confirmed ? "bg-emerald-400" : "bg-amber-300"
              )}
            />
            {confirmed
              ? "CONFIRMED"
              : provisional
                ? "PROVISIONAL"
                : mapping || "SEM STATUS"}
          </span>
          {(provisional || layout.mapping_note) && (
            <span className="max-w-md text-[11px] text-amber-200/80 leading-snug">
              {layout.mapping_note ||
                "Validação humana pendente — mapeamento provisório da pista."}
            </span>
          )}
        </div>
        <p className="text-[11px] text-slate-500">
          {islands.length} ilhas · {layout.positions.length} posições ·{" "}
          {zones.length} zonas · {roadMarkers.length} rótulos viários
        </p>
      </div>
      ) : null}

      <div className="flex flex-wrap items-center gap-1.5">
        {(
          [
            { id: "realtime" as const, label: "🔥 Calor em Tempo Real" },
            { id: "rush" as const, label: "⏱️ Acumulado de Rush" },
            { id: "off" as const, label: "🧊 Apenas Planta" },
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
        {!compact ? (
          <span className="text-[10px] text-slate-600 ml-1">
            T_bico · azul &lt;1.5 · menta 1.5–2.5 · âmbar 2.5–4.5 · 🔥 ≥4.5 · BR-101 sem calor
          </span>
        ) : (
          <span className="text-[10px] text-slate-600 ml-1">T_bico · engine da pista</span>
        )}
      </div>

      <div
        className={cn(
          "grid gap-3 items-stretch",
          compact ? "grid-cols-1" : "lg:grid-cols-[minmax(0,1fr)_300px]"
        )}
      >
        <div className="relative rounded-xl border border-slate-700/80 bg-[#070b14] overflow-hidden">
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
                  heatSourcesRef.current,
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
              preserveAspectRatio="xMidYMid meet"
              className="relative z-[2] block w-full h-auto max-h-[min(72vh,760px)]"
              role="img"
              aria-label={`Planta operacional 2D — ${layout.name}`}
            >
              <defs>
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
                <filter id={`glow-${uid}`} x="-40%" y="-40%" width="180%" height="180%">
                  <feDropShadow
                    dx="0"
                    dy="0"
                    stdDeviation="4"
                    floodColor="#38bdf8"
                    floodOpacity="0.55"
                  />
                </filter>
                <filter
                  id={`glow-amber-${uid}`}
                  x="-40%"
                  y="-40%"
                  width="180%"
                  height="180%"
                >
                  <feDropShadow
                    dx="0"
                    dy="0"
                    stdDeviation="3.5"
                    floodColor="#fbbf24"
                    floodOpacity="0.65"
                  />
                </filter>
                <filter
                  id={`glow-sync-${uid}`}
                  x="-60%"
                  y="-60%"
                  width="220%"
                  height="220%"
                >
                  <feDropShadow
                    dx="0"
                    dy="0"
                    stdDeviation="6"
                    floodColor="#22d3ee"
                    floodOpacity="0.85"
                  />
                </filter>
              </defs>

              <rect x={0} y={0} width={w} height={h} fill="#0a0f18" />
              <rect x={0} y={0} width={w} height={h} fill={`url(#grid-${uid})`} />

              {/* Camada 1 — Zonas */}
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
                      width={Math.min(320, Math.max(80, z.width - 20))}
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

              {/* Camada 1 — ROAD markers (BR-101): faixa viária + rótulo, não clicável */}
              {roadMarkers.map((m) => {
                const label = markerLabel(m);
                const stripY = Math.max(8, Math.min(m.y, 48));
                return (
                  <g key={m.code} pointerEvents="none" aria-label={`Rodovia ${label}`}>
                    {/* Faixa da rodovia na borda frontal */}
                    <rect
                      x={24}
                      y={Math.max(4, stripY - 18)}
                      width={w - 48}
                      height={22}
                      rx={4}
                      fill="#14532d"
                      fillOpacity={0.55}
                      stroke="#22c55e"
                      strokeWidth={1.25}
                      strokeDasharray="10 6"
                    />
                    <text
                      x={40}
                      y={Math.max(4, stripY - 18) + 15}
                      fill="#86efac"
                      fontSize={10}
                      fontWeight={600}
                      letterSpacing="0.12em"
                      fontFamily="ui-sans-serif, system-ui, sans-serif"
                    >
                      RODOVIA
                    </text>
                    {/* Badge central do código da via */}
                    <rect
                      x={m.x - 48}
                      y={stripY - 12}
                      width={96}
                      height={28}
                      rx={6}
                      fill="#052e16"
                      stroke="#4ade80"
                      strokeWidth={1.75}
                    />
                    <text
                      x={m.x}
                      y={stripY + 6}
                      textAnchor="middle"
                      fill="#bbf7d0"
                      fontSize={13}
                      fontWeight={800}
                      fontFamily="ui-sans-serif, system-ui, sans-serif"
                      letterSpacing="0.08em"
                    >
                      {label}
                    </text>
                  </g>
                );
              })}

              {/* Outros landmarks (se houver) */}
              {otherMarkers.map((m) => {
                const label = markerLabel(m);
                const bw = Math.max(72, Math.min(160, 18 + label.length * 9));
                return (
                  <g key={m.code} pointerEvents="none">
                    <rect
                      x={m.x - bw / 2}
                      y={m.y - 14}
                      width={bw}
                      height={26}
                      rx={6}
                      fill="#1e293b"
                      stroke="#64748b"
                      strokeWidth={1.5}
                    />
                    <text
                      x={m.x}
                      y={m.y + 4}
                      textAnchor="middle"
                      fill="#e2e8f0"
                      fontSize={12}
                      fontWeight={700}
                      fontFamily="ui-sans-serif, system-ui, sans-serif"
                    >
                      {label}
                    </text>
                  </g>
                );
              })}

              {/* Camada 2 — Ilhas físicas (sem BR-101) */}
              {islands.map((isl) => {
                const isHot = active?.kind === "island" && active.code === isl.code;
                const nIlha = islandNumber(isl.code, isl.name);
                const isSync =
                  (hlIlha != null && nIlha === hlIlha) ||
                  (hlBico != null &&
                    islandPositions(isl.code).some((p) =>
                      p.nozzles.some((n) => n.nozzle_id === hlBico)
                    ));
                const zoneCode = isl.zone_code || "";
                const isGnv =
                  zoneCode.includes("GNV") ||
                  /GNV/i.test(isl.code + (isl.name || ""));
                return (
                  <g
                    key={isl.id || isl.code}
                    style={{ cursor: "pointer" }}
                    onMouseEnter={() =>
                      setHover({ kind: "island", code: isl.code })
                    }
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
                      fill={
                        isSync
                          ? "#082f3a"
                          : isHot
                            ? "#152033"
                            : isGnv
                              ? "#0d1c18"
                              : "#101826"
                      }
                      stroke={
                        isSync
                          ? "#22d3ee"
                          : isHot
                            ? "#38bdf8"
                            : isGnv
                              ? "#34d399"
                              : "#64748b"
                      }
                      strokeWidth={isSync || isHot ? 2.75 : 1.75}
                      filter={
                        isSync
                          ? `url(#glow-sync-${uid})`
                          : isHot
                            ? `url(#glow-${uid})`
                            : undefined
                      }
                      className={isSync ? "animate-pulse" : undefined}
                    />
                    <rect
                      x={isl.x + 8}
                      y={isl.y + 8}
                      width={Math.max(0, isl.width - 16)}
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
                        {zoneCode.replace(/^ZONE_/, "")}
                      </text>
                    ) : null}
                  </g>
                );
              })}

              {/* Camada 2.5 — Chassi físico da bomba (liga os lados A/B ou Av/Conv) */}
              {Array.from(
                layout.positions.reduce((acc, p) => {
                  const list = acc.get(p.pump_id) || [];
                  list.push(p);
                  acc.set(p.pump_id, list);
                  return acc;
                }, new Map<number, ForecourtPosition[]>())
              ).map(([pumpId, sides]) => {
                if (sides.length < 2) return null;
                const xs = sides.map((s) => s.x);
                const ys = sides.map((s) => s.y);
                const minX = Math.min(...xs) - 8;
                const minY = Math.min(...ys) - 8;
                const maxX = Math.max(...sides.map((s) => s.x + posW));
                const maxY = Math.max(...sides.map((s) => s.y + posH));
                const nNoz = sides.reduce(
                  (a, s) => a + s.nozzles.filter((n) => n.active !== false).length,
                  0
                );
                const label =
                  nNoz >= 6 ? `SÉXTUPLA · BOMBA ${pumpId}` : `QUÁDRUPLA · BOMBA ${pumpId}`;
                return (
                  <g key={`chassis-${pumpId}`} pointerEvents="none">
                    <rect
                      x={minX}
                      y={minY}
                      width={maxX - minX + 8}
                      height={maxY - minY + 8}
                      rx={12}
                      fill="#0b1220"
                      fillOpacity={0.55}
                      stroke="#475569"
                      strokeWidth={1.25}
                      strokeDasharray="4 3"
                    />
                    <text
                      x={minX + 10}
                      y={minY + 14}
                      fill="#64748b"
                      fontSize={9}
                      fontWeight={700}
                      letterSpacing="0.08em"
                      fontFamily="ui-sans-serif, system-ui, sans-serif"
                    >
                      {label}
                    </text>
                  </g>
                );
              })}

              {/* Camada 3 — Posições / lados da bomba */}
              {layout.positions.map((pos) => {
                const style = orientStyle(pos.orientation);
                const isHot =
                  active?.kind === "position" && active.code === pos.code;
                const activeNozzles = pos.nozzles.filter((n) => n.active !== false);
                const isSyncPos =
                  hlBico != null &&
                  activeNozzles.some((n) => n.nozzle_id === hlBico);
                const o = (pos.orientation || "").toUpperCase();
                const isSextupleSide = o === "SENSOR_A" || o === "SENSOR_B";
                return (
                  <g
                    key={pos.id || pos.code}
                    style={{ cursor: "pointer" }}
                    onMouseEnter={() =>
                      setHover({ kind: "position", code: pos.code })
                    }
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
                      height={isSextupleSide ? posH + 12 : posH}
                      rx={10}
                      fill={isSyncPos ? "#083344" : isHot ? "#1c2436" : style.fill}
                      stroke={
                        isSyncPos ? "#22d3ee" : isHot ? "#fbbf24" : style.stroke
                      }
                      strokeWidth={isSyncPos || isHot ? 2.75 : 1.75}
                      filter={
                        isSyncPos
                          ? `url(#glow-sync-${uid})`
                          : isHot
                            ? `url(#glow-amber-${uid})`
                            : undefined
                      }
                      className={isSyncPos ? "animate-pulse" : undefined}
                    />
                    {/* Indicadores de bico (3+3 ou 2+2) */}
                    {activeNozzles.map((n, idx) => {
                      const t =
                        activeNozzles.length > 1
                          ? idx / (activeNozzles.length - 1)
                          : 0.5;
                      const cx = isSextupleSide
                        ? pos.x + posW / 2
                        : pos.x + 18 + t * (posW - 36);
                      const cy = isSextupleSide
                        ? pos.y + 22 + t * (posH - 8)
                        : pos.y + posH - 10;
                      const isNoz = hlBico != null && n.nozzle_id === hlBico;
                      return (
                        <circle
                          key={n.nozzle_id}
                          cx={cx}
                          cy={cy}
                          r={isNoz ? 7 : 4.5}
                          fill={isNoz ? "#22d3ee" : style.stroke}
                          opacity={0.95}
                          filter={isNoz ? `url(#glow-sync-${uid})` : undefined}
                          className={isNoz ? "animate-pulse" : undefined}
                        />
                      );
                    })}
                    <text
                      x={pos.x + 10}
                      y={pos.y + 16}
                      fill="#f8fafc"
                      fontSize={10}
                      fontWeight={600}
                      fontFamily="ui-monospace, monospace"
                    >
                      {pos.code.length > 18 ? pos.code.slice(-16) : pos.code}
                    </text>
                    <text
                      x={pos.x + 10}
                      y={pos.y + 30}
                      fill={style.tag}
                      fontSize={9}
                      fontWeight={600}
                      fontFamily="ui-sans-serif, system-ui, sans-serif"
                    >
                      {orientShort(pos.orientation)}
                    </text>
                    <text
                      x={pos.x + 10}
                      y={pos.y + (isSextupleSide ? posH + 2 : 48)}
                      fill="#94a3b8"
                      fontSize={9}
                      fontFamily="ui-monospace, monospace"
                    >
                      {activeNozzles.map((n) => padBico(n.nozzle_id)).join(" · ") ||
                        "sem bicos"}
                    </text>
                  </g>
                );
              })}
            </svg>

            {heatMode !== "off" && (
              <ForecourtHeatOverlay
                layout={layout}
                fuelEvents={fuelEvents}
                mode={heatMode}
                onSourcesChange={onSourcesChange}
              />
            )}

            {heatHover && heatMode !== "off" && (
              <div className="absolute top-2 right-2 z-10 max-w-[320px] rounded-lg border border-orange-400/40 bg-slate-950/95 px-3 py-2 text-[12px] text-slate-100 pointer-events-none">
                <p className="font-semibold text-orange-200 leading-snug">
                  {heatHover.densityLabel}
                  {heatHover.tBicoMin != null
                    ? ` · T_bico ${heatHover.tBicoMin.toFixed(1)} min`
                    : ""}
                </p>
                <p className="text-[11px] text-slate-400 mt-1">
                  {heatHover.count} abast / {heatHover.windowMinutes} min ·{" "}
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

          <div className="absolute bottom-2 left-2 pointer-events-none z-10">
            <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-700/70 bg-slate-950/90 px-3 py-1.5 text-[11px] text-slate-300">
              {heatMode === "off" ? (
                <>
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-sm border border-slate-500 bg-slate-800" />
                    Ilha
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-emerald-500" />
                    Rodovia (rótulo)
                  </span>
                </>
              ) : (
                <>
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-sky-400" /> &lt;1.5m
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-emerald-400" /> 1.5–2.5m
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-amber-400" /> 2.5–4.5m
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-rose-500" /> 🔥 ≥4.5m
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        {!compact ? (
          <aside className="rounded-xl border border-slate-700/80 bg-slate-950/95 p-4 min-h-[220px] flex flex-col">
            <div className="flex items-center justify-between mb-3">
              <p className="text-[11px] uppercase tracking-[0.14em] text-slate-500 font-semibold">
                Inspector da Pista
              </p>
              {selected && (
                <button
                  type="button"
                  className="text-[10px] text-slate-500 hover:text-slate-300"
                  onClick={() => setSelected(null)}
                >
                  limpar
                </button>
              )}
            </div>

            {!selectedIsland && !selectedPosition && (
              <div className="flex-1 flex flex-col justify-center text-center px-2">
                <p className="text-sm text-slate-400 leading-relaxed">
                  Clique em uma <span className="text-slate-200">ilha</span> ou{" "}
                  <span className="text-slate-200">posição</span> para inspecionar.
                </p>
                <p className="text-[11px] text-slate-600 mt-3">
                  BR-101 é rótulo da rodovia — não é ilha, bomba nem fonte térmica.
                </p>
              </div>
            )}

            {selectedIsland && !selectedPosition && (
              <IslandInspector
                island={selectedIsland}
                positions={islandPositions(selectedIsland.code)}
              />
            )}

            {selectedPosition && (
              <PositionInspector
                position={selectedPosition}
                island={
                  islands.find((i) => i.code === selectedPosition.island_code) ||
                  null
                }
              />
            )}
          </aside>
        ) : null}
      </div>
    </div>
  );
}

function IslandInspector({
  island,
  positions,
}: {
  island: ForecourtIsland;
  positions: ForecourtPosition[];
}) {
  const nozzles = positions.flatMap((p) =>
    p.nozzles.filter((n) => n.active !== false)
  );
  const fuels = Array.from(
    new Set(nozzles.map((n) => fuelFromLabel(n.label)).filter((f) => f !== "—"))
  );

  return (
    <div className="space-y-2">
      <p className="text-base font-semibold text-slate-50">
        {islandLabel(island.code, island.name)}
      </p>
      <BadgeSoft tone="sky">Ilha</BadgeSoft>
      <Row k="Código" v={island.code} />
      <Row k="Zona" v={island.zone_code || "—"} />
      <Row k="Coords" v={`x=${island.x}, y=${island.y}`} />
      <Row k="Dimensão" v={`${island.width} × ${island.height}`} />
      <Row k="Posições" v={String(positions.length)} />
      <Row k="Bicos ativos" v={String(nozzles.length)} />
      {fuels.length > 0 && (
        <div className="pt-2 border-t border-slate-800 mt-2">
          <p className="text-[11px] uppercase tracking-wide text-slate-500 mb-1.5">
            Combustíveis na ilha
          </p>
          <ul className="space-y-1">
            {fuels.map((f) => (
              <li
                key={f}
                className="text-sm text-slate-300 rounded-md border border-slate-800 bg-slate-900/60 px-2 py-1"
              >
                {f}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function PositionInspector({
  position,
  island,
}: {
  position: ForecourtPosition;
  island: ForecourtIsland | null;
}) {
  const activeNozzles = position.nozzles.filter((n) => n.active !== false);
  const inactive = position.nozzles.filter((n) => n.active === false);

  return (
    <div className="space-y-2">
      <p className="text-base font-semibold text-slate-50 leading-snug">
        {position.name || position.code}
      </p>
      <BadgeSoft tone="amber">Posição</BadgeSoft>
      <Row k="Código" v={position.code} />
      <Row k="Bomba" v={position.pump_name || `BOMBA ${position.pump_id}`} />
      <Row
        k="Orientação / sensor"
        v={(position.orientation || "—").toUpperCase()}
      />
      <Row
        k="Ilha"
        v={island ? islandLabel(island.code, island.name) : position.island_code}
      />
      <Row k="Coords" v={`x=${position.x}, y=${position.y}`} />

      <div className="pt-2 border-t border-slate-800 mt-2">
        <p className="text-[11px] uppercase tracking-wide text-slate-500 mb-1.5">
          Bicos ativos ({activeNozzles.length})
        </p>
        {activeNozzles.length === 0 ? (
          <p className="text-sm text-slate-500">Nenhum bico ativo nesta posição.</p>
        ) : (
          <ul className="space-y-1.5 max-h-48 overflow-auto pr-1">
            {activeNozzles.map((n) => (
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
        )}
      </div>

      {inactive.length > 0 && (
        <p className="text-[11px] text-slate-600 pt-1">
          Inativos: {inactive.map((n) => padBico(n.nozzle_id)).join(", ")}
        </p>
      )}

      <div className="pt-2 border-t border-slate-800 mt-2">
        <p className="text-[11px] uppercase tracking-wide text-slate-500 mb-1.5">
          Combustíveis compatíveis
        </p>
        <ul className="space-y-1">
          {Array.from(
            new Set(
              activeNozzles.map((n) => fuelFromLabel(n.label)).filter((f) => f !== "—")
            )
          ).map((f) => (
            <li
              key={f}
              className="text-sm text-slate-300 rounded-md border border-slate-800 bg-slate-900/60 px-2 py-1"
            >
              {f}
            </li>
          ))}
        </ul>
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
