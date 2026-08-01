/**
 * Status de integração da Loja de Conveniência por filial.
 * Casa Caiada e Real Doze operam loja em ERP legado até a migração webPosto.
 */

export type ConvenienciaStatus = "INTEGRADO" | "EM_MIGRACAO";

export interface FilialIntegrationConfig {
  empresaCodigo: number;
  nome: string;
  nomeAbreviado: string;
  convenienciaStatus: ConvenienciaStatus;
}

export const FILIAIS_CONFIG: Record<number, FilialIntegrationConfig> = {
  11495: {
    empresaCodigo: 11495,
    nome: "Posto VIP",
    nomeAbreviado: "VIP",
    convenienciaStatus: "INTEGRADO",
  },
  5555: {
    empresaCodigo: 5555,
    nome: "AP Casa Caiada",
    nomeAbreviado: "Casa Caiada",
    convenienciaStatus: "EM_MIGRACAO",
  },
  74014: {
    empresaCodigo: 74014,
    nome: "Posto Real / Doze",
    nomeAbreviado: "Real Doze",
    convenienciaStatus: "EM_MIGRACAO",
  },
};

export function getFilialConfig(
  empresaCodigo?: number | null
): FilialIntegrationConfig | null {
  if (empresaCodigo == null || empresaCodigo === 0) return null;
  return FILIAIS_CONFIG[empresaCodigo] ?? null;
}

export function getConvenienciaStatus(
  empresaCodigo?: number | null
): ConvenienciaStatus {
  return getFilialConfig(empresaCodigo)?.convenienciaStatus ?? "INTEGRADO";
}

export function isConvenienciaEmMigracao(
  empresaCodigo?: number | null
): boolean {
  return getConvenienciaStatus(empresaCodigo) === "EM_MIGRACAO";
}

/** Cestas Food Service (Café/Salgados) — ocultas enquanto a loja está em migração. */
const FOOD_SERVICE_RE =
  /(caf[eé]|salgado|lanche|food\s*service|p[aã]o|pastel|coxinha|empada|sandu[ií]che)/i;

export function isFoodServiceAffinity(produtos: string[] | undefined | null): boolean {
  return (produtos || []).some((p) => FOOD_SERVICE_RE.test(String(p || "")));
}
