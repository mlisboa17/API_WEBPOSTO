/**
 * HEATMAP-01 — Engine de densidade térmica da pista.
 * I(p) = Σ Peso(t) × FatorVolume — sem hardcode de posto; geometria via layout.
 */

import type { ForecourtLayout } from "@/types/api";
import type { ForecourtFuelEvent } from "@/lib/forecourt-fuel-dots";
import { buildNozzleIndex } from "@/lib/forecourt-fuel-dots";

export type HeatMode = "realtime" | "rush" | "off";

export type HeatSource = {
  key: string;
  kind: "position" | "pump";
  x: number;
  y: number;
  intensity: number; // 0..1+
  radius: number;
  position_code?: string;
  island_code?: string;
  pump_id?: number;
  orientation?: string;
  zone_code?: string;
  count: number;
  windowMinutes: number;
};

export type HeatCellHover = {
  label: string;
  densityLabel: string;
  count: number;
  windowMinutes: number;
  intensity: number;
  island_code?: string;
  position_code?: string;
  orientation?: string;
  zone_code?: string;
};

export function parseEventTime(raw?: string): number | null {
  if (!raw) return null;
  const s = raw.trim();
  // ISO / "YYYY-MM-DD HH:mm:ss"
  const iso = Date.parse(s.includes("T") ? s : s.replace(" ", "T"));
  if (!Number.isNaN(iso)) return iso;
  // "DD/MM/YYYY HH:mm:ss"
  const m = s.match(
    /^(\d{2})\/(\d{2})\/(\d{4})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?/
  );
  if (m) {
    const d = new Date(
      Number(m[3]),
      Number(m[2]) - 1,
      Number(m[1]),
      Number(m[4] || 0),
      Number(m[5] || 0),
      Number(m[6] || 0)
    );
    return d.getTime();
  }
  return null;
}

/** Peso temporal: realtime decai rápido; rush acumula janela mais longa. */
export function timeWeight(ageMs: number, mode: HeatMode): number {
  if (mode === "off") return 0;
  const ageMin = Math.max(0, ageMs / 60_000);
  if (mode === "realtime") {
    // meia-vida ~12 min; quase zero após 45 min
    return Math.exp(-ageMin / 12);
  }
  // rush: janela ~90 min com decaimento suave
  if (ageMin > 120) return 0;
  return Math.exp(-ageMin / 40);
}

export function volumeFactor(litros?: number): number {
  const L = Number(litros);
  if (!Number.isFinite(L) || L <= 0) return 1;
  // normaliza ~40 L = 1.0; satura em ~2.0
  return Math.min(2, 0.35 + L / 40);
}

export function intensityToBand(i: number): "idle" | "flow" | "dense" | "critical" {
  if (i < 0.2) return "idle";
  if (i < 0.5) return "flow";
  if (i < 0.8) return "dense";
  return "critical";
}

export function bandLabel(band: ReturnType<typeof intensityToBand>): string {
  if (band === "idle") return "Low";
  if (band === "flow") return "Normal";
  if (band === "dense") return "High";
  return "Critical 🔥";
}

/** Cor RGBA para o canvas (gradiente da pista). */
export function intensityColor(i: number, alphaScale = 1): string {
  const a = Math.min(0.85, (0.18 + i * 0.55) * alphaScale);
  if (i < 0.2) {
    // azul suave
    return `rgba(56, 189, 248, ${a * 0.7})`;
  }
  if (i < 0.5) {
    // verde menta
    return `rgba(52, 211, 153, ${a})`;
  }
  if (i < 0.8) {
    // amarelo / laranja
    return `rgba(251, 146, 60, ${a})`;
  }
  // vermelho quente → roxo
  const t = Math.min(1, (i - 0.8) / 0.4);
  const r = Math.round(239 + (168 - 239) * t);
  const g = Math.round(68 + (85 - 68) * t);
  const b = Math.round(68 + (247 - 68) * t);
  return `rgba(${r}, ${g}, ${b}, ${Math.min(0.9, a + 0.1)})`;
}

export function computeHeatSources(
  layout: ForecourtLayout,
  events: ForecourtFuelEvent[],
  mode: HeatMode,
  nowMs = Date.now()
): HeatSource[] {
  if (mode === "off" || !events.length) return [];

  const index = buildNozzleIndex(layout);
  const islandByCode = new Map(layout.islands.map((i) => [i.code, i]));
  const posByCode = new Map(layout.positions.map((p) => [p.code, p]));

  type Acc = {
    x: number;
    y: number;
    intensity: number;
    count: number;
    island_code: string;
    pump_id: number;
    orientation: string;
    zone_code: string;
  };

  const byPos = new Map<string, Acc>();
  const windowMinutes = mode === "realtime" ? 30 : 90;

  for (const ev of events) {
    const anchor = index.get(Number(ev.bico));
    if (!anchor) continue;
    const ts = parseEventTime(ev.dataHora);
    // eventos sem timestamp: peso baixo (não inventar horário)
    const ageMs = ts == null ? 45 * 60_000 : Math.max(0, nowMs - ts);
    const w = timeWeight(ageMs, mode);
    if (w < 0.02) continue;
    const contrib = w * volumeFactor(ev.litros);
    const pos = posByCode.get(anchor.position_code);
    const island = pos ? islandByCode.get(pos.island_code) : undefined;
    const key = anchor.position_code;
    const prev = byPos.get(key);
    if (prev) {
      prev.intensity += contrib;
      prev.count += 1;
    } else {
      byPos.set(key, {
        x: anchor.x,
        y: anchor.y,
        intensity: contrib,
        count: 1,
        island_code: pos?.island_code || "",
        pump_id: anchor.pump_id,
        orientation: anchor.orientation || "",
        zone_code: island?.zone_code || "",
      });
    }
  }

  // Normaliza pela carga máxima local (evita saturar tudo)
  let maxI = 0;
  for (const a of byPos.values()) maxI = Math.max(maxI, a.intensity);
  const norm = maxI > 0 ? 1 / maxI : 1;

  const sources: HeatSource[] = [];
  for (const [code, a] of byPos) {
    const i = Math.min(1.4, a.intensity * norm * (mode === "rush" ? 1.15 : 1));
    sources.push({
      key: `pos:${code}`,
      kind: "position",
      x: a.x,
      y: a.y,
      intensity: i,
      radius: 55 + i * 50,
      position_code: code,
      island_code: a.island_code,
      pump_id: a.pump_id,
      orientation: a.orientation,
      zone_code: a.zone_code,
      count: a.count,
      windowMinutes,
    });
  }

  // Fusão por bomba: quando lados/sensores da mesma bomba estão quentes, blob único
  const byPump = new Map<
    number,
    { x: number; y: number; n: number; intensity: number; count: number; island: string; zone: string }
  >();
  for (const s of sources) {
    if (s.pump_id == null) continue;
    const p = byPump.get(s.pump_id) || {
      x: 0,
      y: 0,
      n: 0,
      intensity: 0,
      count: 0,
      island: s.island_code || "",
      zone: s.zone_code || "",
    };
    p.x += s.x;
    p.y += s.y;
    p.n += 1;
    p.intensity += s.intensity;
    p.count += s.count;
    byPump.set(s.pump_id, p);
  }
  for (const [pumpId, p] of byPump) {
    if (p.n < 2) continue;
    const avgI = p.intensity / p.n;
    if (avgI < 0.45) continue; // só funde sob pressão
    sources.push({
      key: `pump:${pumpId}`,
      kind: "pump",
      x: p.x / p.n,
      y: p.y / p.n,
      intensity: Math.min(1.5, avgI * 1.25),
      radius: 90 + avgI * 70,
      pump_id: pumpId,
      island_code: p.island,
      zone_code: p.zone,
      count: p.count,
      windowMinutes,
    });
  }

  return sources;
}

export function pickHoverCell(
  sources: HeatSource[],
  lx: number,
  ly: number
): HeatCellHover | null {
  let best: HeatSource | null = null;
  let bestD = Infinity;
  for (const s of sources) {
    if (s.kind !== "position" && s.kind !== "pump") continue;
    const dx = s.x - lx;
    const dy = s.y - ly;
    const d = Math.hypot(dx, dy);
    const hitR = s.radius * 0.65;
    if (d <= hitR && d < bestD) {
      best = s;
      bestD = d;
    }
  }
  if (!best || best.intensity < 0.05) return null;
  const band = intensityToBand(best.intensity);
  const scope =
    best.kind === "pump"
      ? `bomba ${best.pump_id}`
      : best.position_code || "posição";
  return {
    label: scope,
    densityLabel: bandLabel(band),
    count: best.count,
    windowMinutes: best.windowMinutes,
    intensity: best.intensity,
    island_code: best.island_code,
    position_code: best.position_code,
    orientation: best.orientation,
    zone_code: best.zone_code,
  };
}
