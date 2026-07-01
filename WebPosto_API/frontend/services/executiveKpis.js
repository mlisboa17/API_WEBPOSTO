import { formatCurrency, formatPeriodBr } from "./formatters.js";

export function formatKpiTrend(pct) {
  if (pct == null || pct === "" || Number.isNaN(Number(pct))) {
    return { arrow: "●", cls: "neutral", text: "estável" };
  }
  const n = Number(pct);
  if (n > 0.05) return { arrow: "▲", cls: "up", text: `${Math.abs(n).toFixed(1)}%` };
  if (n < -0.05) return { arrow: "▼", cls: "down", text: `${Math.abs(n).toFixed(1)}%` };
  return { arrow: "●", cls: "neutral", text: "0%" };
}

export function moneyKpi(value) {
  if (value === "INTEGRATION_PROTECTED") return "Integração protegida";
  if (value == null || value === "" || value === "—") return "Dados indisponíveis";
  return formatCurrency(value);
}

export function countKpi(value, suffix = "") {
  if (value === "INTEGRATION_PROTECTED") return "Indisponível";
  if (value == null || value === "" || value === "—") return "Dados indisponíveis";
  return `${value}${suffix}`;
}

export function buildChartBars(items, { labelKey = "label", valueKey = "value", max = 7 } = {}) {
  const rows = (items || [])
    .filter(Boolean)
    .slice(0, max)
    .map((row) => ({
      label: String(row[labelKey] ?? row.nome ?? row.departamento ?? "—").slice(0, 18),
      value: Number(row[valueKey] ?? row.valor ?? row.receita ?? 0) || 0,
    }));
  const peak = Math.max(...rows.map((r) => r.value), 1);
  return rows.map((row, index) => ({
    ...row,
    pct: Math.round((row.value / peak) * 100),
    tone: index === 0 ? "ok" : index < 3 ? "warn" : "neutral",
  }));
}

export function periodSubtitle(filters) {
  return formatPeriodBr(filters?.dataInicial, filters?.dataFinal);
}

export function standardAlertsFromItems(items, { max = 3, mapFn } = {}) {
  return (items || [])
    .slice(0, max)
    .map((item, index) => {
      if (mapFn) return mapFn(item, index);
      return {
        severity: item.severity || item.prioridade || (index === 0 ? "CRÍTICO" : "ALTO"),
        title: item.title || item.titulo || item.tipo || "Alerta",
        detail: item.detail || item.descricao || "",
        view: item.view || "",
      };
    });
}
