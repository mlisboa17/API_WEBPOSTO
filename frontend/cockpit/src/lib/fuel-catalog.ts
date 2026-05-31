/** Códigos WebPosto · Posto VIP — conferidos com relatório gerencial */
export const FUEL_CATALOG: Record<string, string> = {
  "1257884": "Gasolina",
  "1257885": "Gasolina aditivada",
  "1975728": "Etanol aditivado",
  "1260803": "Diesel S10",
  "1257999": "Diesel S10",
  "1258001": "Diesel comum",
};

export function fuelLabel(codigo: string, nomeApi?: string | null): string {
  const c = String(codigo || "").trim();
  if (c && FUEL_CATALOG[c]) return FUEL_CATALOG[c];
  if (nomeApi?.trim()) return nomeApi.trim();
  return c ? `Produto ${c}` : "—";
}

export function isAfericao(row: Record<string, unknown>): boolean {
  const v = row.afericao;
  if (v === true || v === 1) return true;
  return String(v ?? "").toLowerCase() === "true";
}

export function rowLitros(row: Record<string, unknown>): number {
  return Number(row.quantidade ?? 0);
}

export function rowValor(row: Record<string, unknown>): number {
  const vt = Number(row.valorTotal ?? 0);
  if (vt > 0) return vt;
  const q = Number(row.quantidade ?? 0);
  const vu = Number(row.valorUnitario ?? 0);
  return q > 0 && vu > 0 ? q * vu : 0;
}
