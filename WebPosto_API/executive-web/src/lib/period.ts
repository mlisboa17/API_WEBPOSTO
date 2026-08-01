/** Helpers de período para comparação de tendências (N dias anteriores). */

export function inclusiveDays(start: string, end: string): number {
  const a = new Date(`${start}T12:00:00`);
  const b = new Date(`${end}T12:00:00`);
  const ms = Math.abs(b.getTime() - a.getTime());
  return Math.max(1, Math.floor(ms / 86_400_000) + 1);
}

function shiftISO(iso: string, deltaDays: number): string {
  const d = new Date(`${iso}T12:00:00`);
  d.setDate(d.getDate() + deltaDays);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** Período imediatamente anterior com a mesma duração (N dias). */
export function previousPeriod(start: string, end: string): { start: string; end: string } {
  const n = inclusiveDays(start, end);
  const prevEnd = shiftISO(start, -1);
  const prevStart = shiftISO(prevEnd, -(n - 1));
  return { start: prevStart, end: prevEnd };
}

export function percentChange(current: number, previous: number): number | null {
  if (!Number.isFinite(current) || !Number.isFinite(previous)) return null;
  if (previous === 0) {
    if (current === 0) return 0;
    return null;
  }
  return ((current - previous) / Math.abs(previous)) * 100;
}
