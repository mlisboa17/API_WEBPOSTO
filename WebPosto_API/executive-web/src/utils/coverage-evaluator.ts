import { DateCoverageResponse } from "../services/http-copilot-adapter";

export type DerivedCoverageStatus =
  | "COVERED"
  | "OUTSIDE_AVAILABLE_RANGE"
  | "INTERSECTS_GAP"
  | "NO_COVERAGE"
  | "COVERAGE_UNAUTHORIZED"
  | "COVERAGE_ERROR";

export interface CoverageEvalResult {
  status: DerivedCoverageStatus;
  isCovered: boolean;
  canPlanDataRequest: boolean;
  reason?: string;
}

export const UNIT_PUBLIC_NAMES: Record<number, string> = {
  5555: "AP Casa Caiada",
  11495: "Posto VIP",
  74014: "Posto Real/Doze",
  118508: "Conveniência 24 Horas",
};

export function getUnitPublicName(code?: number | null, fallback?: string): string {
  if (!code) return fallback || "Unidade Não Informada";
  if (code === 6666) return UNIT_PUBLIC_NAMES[11495]; // alias legacy banido
  return UNIT_PUBLIC_NAMES[code] || fallback || `Unidade ${code}`;
}

export function getUnitPublicNames(codes?: number[] | null): string {
  if (!codes || codes.length === 0) return "Não informada";
  return codes.map((c) => getUnitPublicName(c)).join(", ");
}

/**
 * Função pura que avalia se o período selecionado pelo usuário está 100% coberto
 * pelos dados locais disponíveis ou se exige solicitação DATA-ON-DEMAND.
 */
export function evaluatePeriodCoverage(
  coverage: DateCoverageResponse | null,
  selectedStart: string,
  selectedEnd: string,
  fetchErrorStatus?: number | null
): CoverageEvalResult {
  // Tratar erros HTTP de consulta da cobertura
  if (fetchErrorStatus === 401) {
    return {
      status: "COVERAGE_UNAUTHORIZED",
      isCovered: false,
      canPlanDataRequest: false,
      reason: "Sua sessão expirou. Entre novamente para consultar a cobertura.",
    };
  }

  if (fetchErrorStatus && fetchErrorStatus !== 200) {
    return {
      status: "COVERAGE_ERROR",
      isCovered: false,
      canPlanDataRequest: false,
      reason: fetchErrorStatus === 403
        ? "Você não possui acesso à cobertura desta unidade."
        : "Não foi possível consultar a cobertura agora.",
    };
  }

  if (!coverage || coverage.empty) {
    return {
      status: "NO_COVERAGE",
      isCovered: false,
      canPlanDataRequest: true,
      reason: "Sem período consolidado disponível para este escopo.",
    };
  }

  const startDate = coverage.firstCompleteDate || coverage.suggestedStartDate;
  const endDate = coverage.lastCompleteDate || coverage.suggestedEndDate;

  if (!startDate || !endDate) {
    return {
      status: "NO_COVERAGE",
      isCovered: false,
      canPlanDataRequest: true,
      reason: "Sem período consolidado disponível para este escopo.",
    };
  }

  // Validação básica de datas
  if (selectedStart > selectedEnd) {
    return {
      status: "NO_COVERAGE",
      isCovered: false,
      canPlanDataRequest: false,
      reason: "Data inicial é posterior à data final.",
    };
  }

  // Verificar se o período selecionado ultrapassa a faixa disponível [startDate, endDate]
  if (selectedStart < startDate || selectedEnd > endDate) {
    return {
      status: "OUTSIDE_AVAILABLE_RANGE",
      isCovered: false,
      canPlanDataRequest: true,
      reason: `O período selecionado está fora da faixa disponível (${startDate} a ${endDate}).`,
    };
  }

  // Verificar se o período intersecta algum gap da lista coverage.gaps
  if (Array.isArray(coverage.gaps) && coverage.gaps.length > 0) {
    const hasGapIntersection = coverage.gaps.some((gap: any) => {
      if (!gap) return false;
      const gapDay = typeof gap === "string" ? gap : gap.day || gap.date || gap.inicio || gap.start;
      const gapEnd = typeof gap === "object" ? gap.fim || gap.end || gapDay : gapDay;

      if (gapDay) {
        return !(selectedEnd < gapDay || selectedStart > gapEnd);
      }
      return false;
    });

    if (hasGapIntersection) {
      return {
        status: "INTERSECTS_GAP",
        isCovered: false,
        canPlanDataRequest: true,
        reason: "O período selecionado intersecta dias com lacunas de consolidação local.",
      };
    }
  }

  return {
    status: "COVERED",
    isCovered: true,
    canPlanDataRequest: false,
    reason: "Período totalmente coberto pelos dados locais.",
  };
}

/**
 * Função pura para identificar se a pergunta do usuário exige comparação entre unidades.
 */
export function isComparisonQuery(queryText: string): boolean {
  if (!queryText) return false;
  const lower = queryText.toLowerCase();
  return (
    lower.includes("compare") ||
    lower.includes("comparar") ||
    lower.includes("comparativo") ||
    lower.includes("diferença entre") ||
    lower.includes("diferenca entre") ||
    lower.includes("cada unidade") ||
    lower.includes("entre as unidades")
  );
}
