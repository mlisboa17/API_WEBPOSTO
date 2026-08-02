/**
 * Mapeia abastecimentos (bico ERP) → coordenadas da planta via layout ACTIVE.
 * Nenhuma posição hardcoded: tudo deriva de ForecourtLayout.positions.
 */

import type { ForecourtLayout } from "@/types/api";

export type ForecourtFuelEvent = {
  id: string | number;
  bico: number;
  bomba?: number;
  produto?: string;
  litros?: number;
  valor?: number;
  frentistaNome?: string;
  dataHora?: string;
  /** pendente | baixado | retencao */
  status?: string;
  fonte?: "live" | "periodo";
};

export type ForecourtFuelDot = ForecourtFuelEvent & {
  x: number;
  y: number;
  position_code: string;
  orientation: string;
  pump_id: number;
};

function jitter(seed: number, axis: 0 | 1): number {
  const n = Math.abs((seed * (axis === 0 ? 9301 : 49297) + 49297) % 233280) / 233280;
  return (n - 0.5) * (axis === 0 ? 40 : 32);
}

export function buildNozzleIndex(layout: ForecourtLayout) {
  const map = new Map<
    number,
    { position_code: string; orientation: string; pump_id: number; x: number; y: number }
  >();
  const posW = Math.max(96, Math.min(140, (layout.coordinate_width || 1000) * 0.12));
  const posH = 52;
  for (const p of layout.positions || []) {
    const cx = Number(p.x) + posW / 2;
    const cy = Number(p.y) + posH / 2;
    for (const n of p.nozzles || []) {
      map.set(Number(n.nozzle_id), {
        position_code: p.code,
        orientation: p.orientation || "",
        pump_id: Number(p.pump_id),
        x: cx,
        y: cy,
      });
    }
  }
  return map;
}

export function mapFuelEventsToDots(
  layout: ForecourtLayout,
  events: ForecourtFuelEvent[]
): ForecourtFuelDot[] {
  const index = buildNozzleIndex(layout);
  const dots: ForecourtFuelDot[] = [];
  for (const ev of events) {
    const anchor = index.get(Number(ev.bico));
    if (!anchor) continue;
    const seed = typeof ev.id === "number" ? ev.id : hashStr(String(ev.id));
    dots.push({
      ...ev,
      x: anchor.x + jitter(seed, 0),
      y: anchor.y + jitter(seed + 7, 1),
      position_code: anchor.position_code,
      orientation: anchor.orientation,
      pump_id: anchor.pump_id,
    });
  }
  return dots;
}

function hashStr(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return Math.abs(h);
}
