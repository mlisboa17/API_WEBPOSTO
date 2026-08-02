/**
 * Normalização de filial UI → código real WebPosto (empresaCodigo).
 *
 * Aliases ordinais (1/001, 2/002, 3/003) e nomes comerciais resolvem para:
 *   Casa Caiada → 5555 | VIP → 11495 | Real Doze → 74014
 */

export const EMPRESA_CASA_CAIADA = 5555;
export const EMPRESA_VIP = 11495;
export const EMPRESA_REAL_DOZE = 74014;

/** Ordinal interno (legado UI/cache) → código WebPosto. */
export const ORDINAL_TO_EMPRESA: Record<number, number> = {
  1: EMPRESA_CASA_CAIADA,
  2: EMPRESA_VIP,
  3: EMPRESA_REAL_DOZE,
};

export const EMPRESA_TO_ORDINAL: Record<number, number> = {
  [EMPRESA_CASA_CAIADA]: 1,
  [EMPRESA_VIP]: 2,
  [EMPRESA_REAL_DOZE]: 3,
};

const ALIAS_TO_EMPRESA: Record<string, number> = {
  // Casa Caiada
  "1": EMPRESA_CASA_CAIADA,
  "01": EMPRESA_CASA_CAIADA,
  "001": EMPRESA_CASA_CAIADA,
  "5555": EMPRESA_CASA_CAIADA,
  casa: EMPRESA_CASA_CAIADA,
  casacaiada: EMPRESA_CASA_CAIADA,
  apcasacaiada: EMPRESA_CASA_CAIADA,
  apcasacaiadaolinda: EMPRESA_CASA_CAIADA,
  // VIP
  "2": EMPRESA_VIP,
  "02": EMPRESA_VIP,
  "002": EMPRESA_VIP,
  "11495": EMPRESA_VIP,
  vip: EMPRESA_VIP,
  postovip: EMPRESA_VIP,
  postovipolinda: EMPRESA_VIP,
  // Real Doze
  "3": EMPRESA_REAL_DOZE,
  "03": EMPRESA_REAL_DOZE,
  "003": EMPRESA_REAL_DOZE,
  "74014": EMPRESA_REAL_DOZE,
  doze: EMPRESA_REAL_DOZE,
  real: EMPRESA_REAL_DOZE,
  realdoze: EMPRESA_REAL_DOZE,
  postodoze: EMPRESA_REAL_DOZE,
  postoreal: EMPRESA_REAL_DOZE,
  postorealdoze: EMPRESA_REAL_DOZE,
  postodozefilialii: EMPRESA_REAL_DOZE,
};

function slugify(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");
}

export function isTodasFiliais(raw: unknown): boolean {
  if (raw == null || raw === "") return true;
  if (typeof raw === "number") return raw === 0;
  const s = String(raw).trim().toUpperCase();
  return s === "0" || s === "TODAS" || s === "ALL" || s === "CONSOLIDADO" || s === "TODAS AS FILIAIS";
}

/**
 * Resolve qualquer variação (nome, slug, ordinal 1–3, código WebPosto)
 * para o `empresaCodigo` real. Retorna `null` = TODAS (consolidado).
 */
export function resolveEmpresaCodigo(raw: unknown): number | null {
  if (isTodasFiliais(raw)) return null;

  if (typeof raw === "number" && Number.isFinite(raw)) {
    const n = Math.trunc(raw);
    if (n === EMPRESA_CASA_CAIADA || n === EMPRESA_VIP || n === EMPRESA_REAL_DOZE) return n;
    if (ORDINAL_TO_EMPRESA[n]) return ORDINAL_TO_EMPRESA[n];
    return n > 0 ? n : null;
  }

  const text = String(raw).trim();
  if (!text) return null;

  // numérico puro
  if (/^\d+$/.test(text)) {
    return resolveEmpresaCodigo(Number(text));
  }

  const slug = slugify(text);
  if (ALIAS_TO_EMPRESA[slug] != null) return ALIAS_TO_EMPRESA[slug];

  // match parcial por palavras-chave
  if (slug.includes("caiada") || (slug.includes("casa") && !slug.includes("real"))) {
    return EMPRESA_CASA_CAIADA;
  }
  if (slug.includes("vip")) return EMPRESA_VIP;
  if (slug.includes("doze") || slug.includes("real")) return EMPRESA_REAL_DOZE;

  return null;
}

/** Ordinal legado (1/2/3) a partir do código WebPosto. */
export function toEmpresaOrdinal(empresaCodigo: number | null | undefined): number | null {
  if (empresaCodigo == null || empresaCodigo === 0) return null;
  return EMPRESA_TO_ORDINAL[empresaCodigo] ?? null;
}

export function matchesEmpresa(
  rowEmpresaCodigo: unknown,
  selected: unknown
): boolean {
  const resolvedSelected = resolveEmpresaCodigo(selected);
  if (resolvedSelected == null) return true;
  const resolvedRow = resolveEmpresaCodigo(rowEmpresaCodigo);
  return resolvedRow === resolvedSelected;
}
