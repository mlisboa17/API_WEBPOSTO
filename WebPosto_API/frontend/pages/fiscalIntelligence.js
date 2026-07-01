import { downloadCsv } from "../services/export.js";
import { bindExecutiveNav, renderExecutiveEmptyState } from "../components/executiveFirstFold.js";
import { buildExecutivePageHtml } from "../components/executiveInsightDetail.js";
import { buildChartBars, countKpi } from "../services/executiveKpis.js";
import {
  buildFourQuestionBrief,
  enrichAlert,
  mapCriticalBranches,
  mapPriorityActions,
  mapRisks,
} from "../services/executiveBrief.js";

const FISCAL_EMPTY_MSG = "Não foi possível montar esta visão no período selecionado.";

function panelText(value, fallback = "Não informado") {
  if (value == null || value === "" || value === "—") return fallback;
  return value;
}

function cellText(value) {
  if (value == null || value === "" || value === "—") return "Não informado";
  return value;
}

function renderTable(title, items, columns) {
  if (!items?.length) return "";
  const head = columns.map((c) => `<th>${c.label}</th>`).join("");
  const body = items
    .filter(Boolean)
    .map((item) => {
      const cells = columns
        .map((c) => {
          const val = c.render ? c.render(item) : item[c.key];
          return `<td>${cellText(val)}</td>`;
        })
        .join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");
  return `<section class="panel"><h3>${title}</h3><table class="data-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></section>`;
}

export function renderFiscalIntelligence(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = renderExecutiveEmptyState({
      title: options.pageTitle || "Tributação",
      message: FISCAL_EMPTY_MSG,
      chartTitle: "Principais riscos",
    });
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const tax = payload.taxClassificationEngine || cockpit.taxClassification || {};
  const risks = payload.fiscalRiskEngine?.risks || cockpit.topRiscos || [];

  const comNcm = exec["2_comNcm"] ?? cockpit.ncmComEvidencia ?? 0;
  const semNcm = exec["3_semNcm"] ?? cockpit.ncmSemEvidencia ?? 0;
  const cobertura = exec["4_coberturaFiscalAtual"] ?? cockpit.coberturaFiscal ?? null;
  const riscosCount = exec["6_riscosFiscais"] ?? risks.length ?? 0;
  const hasData = Number(comNcm) > 0 || risks.length > 0;

  if (!hasData) {
    node.innerHTML = renderExecutiveEmptyState({
      title: options.pageTitle || "Tributação",
      message: FISCAL_EMPTY_MSG,
      chartTitle: "Principais riscos",
    });
    return;
  }

  const kpis = [
    { label: "Com NCM", value: countKpi(comNcm), trendPct: null, status: "ok" },
    { label: "Sem NCM", value: countKpi(semNcm), trendPct: null, status: Number(semNcm) > 0 ? "warn" : "ok" },
    {
      label: "Cobertura",
      value: cobertura != null ? `${cobertura}%` : "Dados indisponíveis",
      trendPct: null,
      status: Number(cobertura) >= 80 ? "ok" : "warn",
    },
    {
      label: "Alertas",
      value: String(riscosCount),
      trendPct: null,
      status: Number(riscosCount) > 0 ? "crit" : "ok",
    },
  ];

  const topRisk = risks[0];
  const brief = buildFourQuestionBrief({
    what: `${comNcm} produtos com NCM evidenciado; cobertura ${cobertura != null ? `${cobertura}%` : "indisponível"}.`,
    why:
      Number(semNcm) > 0
        ? `${semNcm} produto(s) sem NCM com evidência.`
        : topRisk
          ? `Risco ${panelText(topRisk.risco)} em ${panelText(topRisk.nome || topRisk.produtoCodigo)}.`
          : "Cadastro tributário consistente.",
    where: topRisk?.produtoCodigo
      ? `Produto ${topRisk.produtoCodigo}${topRisk.segmento ? ` · ${topRisk.segmento}` : ""}`
      : "Catálogo consolidado",
    actionNow: topRisk
      ? `Regularizar tributação de ${panelText(topRisk.nome || topRisk.produtoCodigo)} hoje.`
      : "Revisar novos produtos antes da venda.",
  });

  const chartBars = buildChartBars(
    risks.slice(0, 7).map((r) => ({ nome: r.nome || r.produtoCodigo, valor: Number(r.risco) || 1 })),
    { labelKey: "nome", valueKey: "valor", max: 7 }
  );

  const alerts = risks.slice(0, 3).map((r) =>
    enrichAlert(
      {
        severity: r.risco || "ALTO",
        title: panelText(r.nome || r.produtoCodigo, "Risco fiscal"),
        detail: [r.segmento, r.tipo].filter(Boolean).join(" · "),
        view: "",
        origin: "Fiscal",
      },
      {
        why: panelText(r.tipo, "Classificação tributária incompleta"),
        where: r.produtoCodigo ? `Produto ${r.produtoCodigo}` : "Catálogo",
        actionNow: "Completar NCM e evidência fiscal",
      }
    )
  );

  const detail = `
    <div class="exec-detail-toolbar">
      <button type="button" id="fiscalIntelRefresh" class="btn-secondary">Atualizar</button>
      <button type="button" id="fiscalIntelExport" class="btn-secondary">Exportar CSV</button>
    </div>
    ${renderTable("Classificação tributária", tax.items || [], [
      { key: "tributo", label: "Tributo" },
      { key: "classificacao", label: "Status" },
      { key: "evidencia", label: "Evidência" },
    ])}
    ${renderTable("Principais riscos", risks.slice(0, 8), [
      { key: "produtoCodigo", label: "Produto" },
      { key: "nome", label: "Nome" },
      { key: "segmento", label: "Segmento" },
      { key: "risco", label: "Risco" },
      { key: "tipo", label: "Tipo" },
    ])}
  `;

  node.innerHTML = buildExecutivePageHtml({
    title: options.pageTitle || "Tributação",
    actionsHtml: "",
    kpis,
    brief,
    chartBars,
    chartTitle: "Principais riscos fiscais",
    criticalBranches: mapCriticalBranches(
      risks.slice(0, 3).map((r) => ({
        name: panelText(r.nome || r.produtoCodigo),
        metric: panelText(r.risco, "Dados indisponíveis"),
        tag: panelText(r.segmento, "Produto"),
        view: "",
      }))
    ),
    priorityActions: mapPriorityActions(
      alerts.map((a) => ({ title: a.title, detail: a.actionNow, view: a.view }))
    ),
    risks: mapRisks(risks),
    opportunities:
      Number(comNcm) > Number(semNcm)
        ? [{ title: "Ampliar produtos com NCM evidenciado", impact: `${comNcm} OK · ${semNcm} pendentes`, view: "" }]
        : [],
    alerts,
    detailHtml: detail,
    detailSummary: "Detalhamento tributário",
  });

  node.querySelector("#fiscalIntelRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#fiscalIntelExport")?.addEventListener("click", () => {
    downloadCsv("tributacao-riscos.csv", risks);
  });
  bindExecutiveNav(node, options.onNavigate);
}
