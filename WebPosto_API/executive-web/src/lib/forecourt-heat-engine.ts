/**
 * HEATMAP-01 — Engine de densidade térmica da pista.
 * Intensidade acoplada a T_bico / retenção (pista_intelligence) + volume.
 * I(p) = f(T_bico, Peso(t), FatorVolume) — fusão metaball por lado e ilha.
 *
 * Bandas de temperatura (min):
 *   Azul suave   T < 1.5
 *   Verde menta  1.5 ≤ T < 2.5
 *   Âmbar        2.5 ≤ T < 4.5
 *   Vermelho 🔥  T ≥ 4.5
 */

import type { ForecourtLayout } from "@/types/api";
import type { ForecourtFuelEvent } from "@/lib/forecourt-fuel-dots";
import { buildNozzleIndex } from "@/lib/forecourt-fuel-dots";

export type HeatMode = "realtime" | "rush" | "off";

export type HeatSource = {
  key: string;
  kind: "position" | "side" | "pump" | "island";
  x: number;
  y: number;
  intensity: number; // 0..1+ (escala de cor alinhada a T_bico)
  radius: number;
  position_code?: string;
  island_code?: string;
  pump_id?: number;
  orientation?: string;
  zone_code?: string;
  count: number;
  windowMinutes: number;
  /** Média T_bico / retenção na célula (minutos) */
  tBicoMin?: number;
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
  tBicoMin?: number;
};

const SIDE_PAIRS: Record<string, string> = {
  SENSOR_A: "SENSOR_B",
  SENSOR_B: "SENSOR_A",
  AVENIDA: "CONVENIENCIA",
  CONVENIENCIA: "AVENIDA",
};

/** Limiares oficiais T_bico (min) — alinhados à engine da pista. */
export const T_IDLE = 1.5;
export const T_GREEN = 2.5;
export const T_YELLOW = 4.5;

export function parseEventTime(raw?: string): number | null {
  if (!raw) return null;
  const s = raw.trim();
  const iso = Date.parse(s.includes("T") ? s : s.replace(" ", "T"));
  if (!Number.isNaN(iso)) return iso;
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
    return Math.exp(-ageMin / 12);
  }
  if (ageMin > 120) return 0;
  return Math.exp(-ageMin / 40);
}

export function volumeFactor(litros?: number): number {
  const L = Number(litros);
  if (!Number.isFinite(L) || L <= 0) return 1;
  return Math.min(2, 0.35 + L / 40);
}

/** Resolve T efetivo do evento (retenção pontual > T_bico médio). */
export function eventTBicoMin(ev: ForecourtFuelEvent): number | null {
  const r = Number(ev.retencaoMin);
  if (Number.isFinite(r) && r > 0) return r;
  const t = Number(ev.tBicoMin);
  if (Number.isFinite(t) && t > 0) return t;
  return null;
}

/**
 * Mapeia minutos T_bico → intensidade 0..1.4 para o gradiente.
 * Pontos de quebra: 1.5 / 2.5 / 4.5.
 */
export function tBicoToIntensity(tMin: number): number {
  const t = Math.max(0, tMin);
  if (t < T_IDLE) return 0.08 + (t / T_IDLE) * 0.12; // → ~0.20
  if (t < T_GREEN) return 0.22 + ((t - T_IDLE) / (T_GREEN - T_IDLE)) * 0.28; // → ~0.50
  if (t < T_YELLOW) return 0.52 + ((t - T_GREEN) / (T_YELLOW - T_GREEN)) * 0.28; // → ~0.80
  return Math.min(1.45, 0.85 + (t - T_YELLOW) * 0.12);
}

export function intensityToBand(i: number): "idle" | "flow" | "dense" | "critical" {
  if (i < 0.22) return "idle";
  if (i < 0.52) return "flow";
  if (i < 0.82) return "dense";
  return "critical";
}

export function bandLabel(band: ReturnType<typeof intensityToBand>): string {
  if (band === "idle") return "Azul · ocioso (<1.5 min)";
  if (band === "flow") return "Menta · fluxo (1.5–2.5 min)";
  if (band === "dense") return "Âmbar · pressão (2.5–4.5 min)";
  return "🔥 Vermelho · crítico (≥4.5 min)";
}

export function tBicoBandLabel(tMin: number): string {
  if (tMin < T_IDLE) return "Azul · ocioso (<1.5 min)";
  if (tMin < T_GREEN) return "Menta · fluxo (1.5–2.5 min)";
  if (tMin < T_YELLOW) return "Âmbar · pressão (2.5–4.5 min)";
  return "🔥 Vermelho · crítico (≥4.5 min)";
}

/** Cor RGBA — Azul → Menta → Âmbar → Vermelho quente (por intensidade). */
export function intensityColor(i: number, alphaScale = 1): string {
  const a = Math.min(0.88, (0.2 + i * 0.55) * alphaScale);
  if (i < 0.22) return `rgba(56, 189, 248, ${a * 0.75})`; // azul suave
  if (i < 0.52) return `rgba(52, 211, 153, ${a})`; // verde menta
  if (i < 0.82) return `rgba(251, 191, 36, ${a})`; // âmbar
  const t = Math.min(1, (i - 0.82) / 0.4);
  const r = Math.round(248 + (220 - 248) * t);
  const g = Math.round(113 + (38 - 113) * t);
  const b = Math.round(113 + (38 - 113) * t);
  return `rgba(${r}, ${g}, ${b}, ${Math.min(0.92, a + 0.12)})`;
}

/** Cor direta a partir de T_bico (minutos). */
export function tBicoColor(tMin: number, alphaScale = 1): string {
  return intensityColor(tBicoToIntensity(tMin), alphaScale);
}

function isRoadCode(code: string, layout: ForecourtLayout): boolean {
  const up = code.toUpperCase();
  if (/^BR[-_]?\d+/.test(up)) return true;
  return (layout.markers || []).some((m) => {
    const k = String(m.kind || "ROAD").toUpperCase();
    return (
      (k === "ROAD" || /^BR[-_]?\d+/i.test(m.code || "")) &&
      m.code.toUpperCase() === up
    );
  });
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
    tSum: number;
    tN: number;
    island_code: string;
    pump_id: number;
    orientation: string;
    zone_code: string;
  };

  const byPos = new Map<string, Acc>();
  const windowMinutes = mode === "realtime" ? 15 : 90;

  for (const ev of events) {
    const anchor = index.get(Number(ev.bico));
    if (!anchor) continue;
    const ts = parseEventTime(ev.dataHora);
    const ageMs = ts == null ? 45 * 60_000 : Math.max(0, nowMs - ts);
    const w = timeWeight(ageMs, mode);
    if (w < 0.02) continue;

    const tEv = eventTBicoMin(ev);
    // Intensidade: prioriza T_bico/retenção da engine; fallback volume
    let baseI: number;
    if (tEv != null) {
      baseI = tBicoToIntensity(tEv) * (0.55 + 0.45 * w) * volumeFactor(ev.litros);
    } else {
      baseI = w * volumeFactor(ev.litros) * 0.55;
    }

    const pos = posByCode.get(anchor.position_code);
    const island = pos ? islandByCode.get(pos.island_code) : undefined;
    const key = anchor.position_code;
    const prev = byPos.get(key);
    if (prev) {
      prev.intensity += baseI;
      prev.count += 1;
      if (tEv != null) {
        prev.tSum += tEv;
        prev.tN += 1;
      }
    } else {
      byPos.set(key, {
        x: anchor.x,
        y: anchor.y,
        intensity: baseI,
        count: 1,
        tSum: tEv ?? 0,
        tN: tEv != null ? 1 : 0,
        island_code: pos?.island_code || "",
        pump_id: anchor.pump_id,
        orientation: anchor.orientation || "",
        zone_code: island?.zone_code || "",
      });
    }
  }

  let maxI = 0;
  for (const a of byPos.values()) maxI = Math.max(maxI, a.intensity);
  const norm = maxI > 0 ? 1 / maxI : 1;
  const rushBoost = mode === "rush" ? 1.12 : 1;

  const sources: HeatSource[] = [];
  for (const [code, a] of byPos) {
    if (!a.island_code || isRoadCode(a.island_code, layout)) continue;
    const avgT = a.tN > 0 ? a.tSum / a.tN : undefined;
    // Se há T médio, a cor segue T; senão normaliza volume
    const i =
      avgT != null
        ? Math.min(1.5, tBicoToIntensity(avgT) * rushBoost)
        : Math.min(1.4, a.intensity * norm * rushBoost);
    sources.push({
      key: `pos:${code}`,
      kind: "position",
      x: a.x,
      y: a.y,
      intensity: i,
      radius: 48 + i * 42,
      position_code: code,
      island_code: a.island_code,
      pump_id: a.pump_id,
      orientation: a.orientation,
      zone_code: a.zone_code,
      count: a.count,
      windowMinutes,
      tBicoMin: avgT,
    });
  }

  // Fusão por lado da bomba (SENSOR_A/B ou AVENIDA/CONVENIENCIA)
  const byPumpSide = new Map<
    string,
    {
      pump_id: number;
      orientation: string;
      x: number;
      y: number;
      n: number;
      intensity: number;
      count: number;
      tSum: number;
      tN: number;
      island: string;
      zone: string;
    }
  >();
  for (const s of sources) {
    if (s.kind !== "position" || s.pump_id == null) continue;
    const o = (s.orientation || "").toUpperCase();
    if (!SIDE_PAIRS[o]) continue;
    const key = `${s.pump_id}:${o}`;
    const p = byPumpSide.get(key) || {
      pump_id: s.pump_id,
      orientation: o,
      x: 0,
      y: 0,
      n: 0,
      intensity: 0,
      count: 0,
      tSum: 0,
      tN: 0,
      island: s.island_code || "",
      zone: s.zone_code || "",
    };
    p.x += s.x;
    p.y += s.y;
    p.n += 1;
    p.intensity += s.intensity;
    p.count += s.count;
    if (s.tBicoMin != null) {
      p.tSum += s.tBicoMin;
      p.tN += 1;
    }
    byPumpSide.set(key, p);
  }

  const sideSources: HeatSource[] = [];
  for (const p of byPumpSide.values()) {
    if (p.n < 1) continue;
    const avgI = p.intensity / p.n;
    if (avgI < 0.16) continue;
    const avgT = p.tN > 0 ? p.tSum / p.tN : undefined;
    // Séxtupla Real: 3 bicos no lado → mancha envolve o sensor
    // Quádrupla Casa Caiada: lado Av/Conv isolado
    const sideHot =
      p.n >= 2 || (avgT != null && avgT >= T_GREEN) || avgI >= 0.35;
    if (!sideHot && p.n < 2) continue;
    sideSources.push({
      key: `side:${p.pump_id}:${p.orientation}`,
      kind: "side",
      x: p.x / p.n,
      y: p.y / p.n,
      intensity: Math.min(1.5, avgI * 1.12),
      radius: (p.orientation.startsWith("SENSOR") ? 82 : 70) + avgI * 58,
      pump_id: p.pump_id,
      orientation: p.orientation,
      island_code: p.island,
      zone_code: p.zone,
      count: p.count,
      windowMinutes,
      tBicoMin: avgT,
    });
  }
  sources.push(...sideSources);

  // Ambos os lados ativos → fusão central (ilha ferve / 6 bicos Real)
  const sidesByPump = new Map<number, HeatSource[]>();
  for (const s of sideSources) {
    if (s.pump_id == null) continue;
    const list = sidesByPump.get(s.pump_id) || [];
    list.push(s);
    sidesByPump.set(s.pump_id, list);
  }
  for (const [pumpId, sides] of sidesByPump) {
    if (sides.length < 2) continue;
    const avgI = sides.reduce((a, s) => a + s.intensity, 0) / sides.length;
    if (avgI < 0.32) continue;
    const bothHot = sides.every((s) => s.intensity >= 0.32);
    if (!bothHot) continue;
    const cx = sides.reduce((a, s) => a + s.x, 0) / sides.length;
    const cy = sides.reduce((a, s) => a + s.y, 0) / sides.length;
    const island = sides[0].island_code || "";
    const isl = island ? islandByCode.get(island) : undefined;
    const tVals = sides.map((s) => s.tBicoMin).filter((t): t is number => t != null);
    const avgT =
      tVals.length > 0 ? tVals.reduce((a, b) => a + b, 0) / tVals.length : undefined;
    // Rush com 6 bicos: força vermelho quente se T médio ≥ 4.5 ou intensidade alta
    const boil =
      (avgT != null && avgT >= T_YELLOW) || avgI >= 0.75
        ? Math.min(1.65, Math.max(avgI * 1.4, tBicoToIntensity(avgT ?? T_YELLOW)))
        : Math.min(1.55, avgI * 1.3);
    sources.push({
      key: `pump:${pumpId}`,
      kind: "pump",
      x: cx,
      y: cy,
      intensity: boil,
      radius: Math.max(
        115,
        (isl ? Math.min(isl.width, isl.height) * 0.5 : 125) + avgI * 55
      ),
      pump_id: pumpId,
      island_code: island,
      zone_code: sides[0].zone_code,
      count: sides.reduce((a, s) => a + s.count, 0),
      windowMinutes,
      tBicoMin: avgT,
    });
  }

  // Metaball por ilha sob rush bilateral / 4 bicos Casa Caiada fundindo no centro
  const byIsland = new Map<
    string,
    {
      x: number;
      y: number;
      n: number;
      intensity: number;
      count: number;
      tSum: number;
      tN: number;
      zone: string;
    }
  >();
  for (const s of sources) {
    if ((s.kind !== "position" && s.kind !== "side") || !s.island_code) continue;
    const p = byIsland.get(s.island_code) || {
      x: 0,
      y: 0,
      n: 0,
      intensity: 0,
      count: 0,
      tSum: 0,
      tN: 0,
      zone: s.zone_code || "",
    };
    p.x += s.x;
    p.y += s.y;
    p.n += 1;
    p.intensity += s.intensity;
    p.count += s.count;
    if (s.tBicoMin != null) {
      p.tSum += s.tBicoMin;
      p.tN += 1;
    }
    byIsland.set(s.island_code, p);
  }
  for (const [islandCode, p] of byIsland) {
    if (p.n < 2) continue;
    const avgI = p.intensity / p.n;
    if (avgI < 0.4) continue;
    const isl = islandByCode.get(islandCode);
    const cx = isl ? isl.x + isl.width / 2 : p.x / p.n;
    const cy = isl ? isl.y + isl.height / 2 : p.y / p.n;
    const avgT = p.tN > 0 ? p.tSum / p.tN : undefined;
    sources.push({
      key: `island:${islandCode}`,
      kind: "island",
      x: cx,
      y: cy,
      intensity: Math.min(1.65, avgI * 1.28),
      radius: Math.max(
        125,
        (isl ? Math.max(isl.width, isl.height) * 0.44 : 135) + avgI * 48
      ),
      island_code: islandCode,
      zone_code: p.zone,
      count: p.count,
      windowMinutes,
      tBicoMin: avgT,
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
    best.kind === "island"
      ? `ilha ${best.island_code}`
      : best.kind === "pump"
        ? `bomba ${best.pump_id} (fusão)`
        : best.kind === "side"
          ? `lado ${best.orientation} · bomba ${best.pump_id}`
          : best.position_code || "posição";
  return {
    label: scope,
    densityLabel:
      best.tBicoMin != null ? tBicoBandLabel(best.tBicoMin) : bandLabel(band),
    count: best.count,
    windowMinutes: best.windowMinutes,
    intensity: best.intensity,
    island_code: best.island_code,
    position_code: best.position_code,
    orientation: best.orientation,
    zone_code: best.zone_code,
    tBicoMin: best.tBicoMin,
  };
}
