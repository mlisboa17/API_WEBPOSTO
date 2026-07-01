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

export function renderFiscalReconciliation(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = renderExecutiveEmptyState({
      title: options.pageTitle || "Conciliação",
      message: FISCAL_EMPTY_MSG,
      chartTitle: "Cobertura por domínio",
    });
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const risks = payload.fiscalRiskConsolidation?.risks || cockpit.riscoFiscalConsolidado || [];
  const nfce = payload.nfceVendaReconciliation || cockpit.nfceReconciliation || {};
  const lmc = payload.lmcSalesReconciliation || cockpit.lmcReconciliation || {};
  const prod = payload.productSalesReconciliation || cockpit.productReconciliation || {};

  const conciliadas = exec["1_vendasConciliadasNfce"] ?? nfce.nfceMatched ?? 0;
  const semNfce = exec["2_vendasSemNfce"] ?? nfce.vendaSemNfce ?? 0;
  const itensProd = exec["3_itensConciliadosProduto"] ?? prod.itensConciliados ?? 0;
  const alertas = risks.length || Number(semNfce) + Number(lmc.litrosSemLmc || 0);
  const hasData = Number(conciliadas) > 0 || alertas > 0 || risks.length > 0;

  if (!hasData) {
    node.innerHTML = renderExecutiveEmptyState({
      title: options.pageTitle || "Conciliação",
      message: FISCAL_EMPTY_MSG,
      chartTitle: "Cobertura por domínio",
    });
    return;
  }

  const kpis = [
    { label: "Conciliadas", value: countKpi(conciliadas), trendPct: null, status: "ok" },
    { label: "Sem nota", value: countKpi(semNfce), trendPct: null, status: Number(semNfce) > 0 ? "warn" : "ok" },
    { label: "Itens cruzados", value: countKpi(itensProd), trendPct: null, status: "ok" },
    {
      label: "Alertas",
      value: String(alertas),
      trendPct: null,
      status: alertas > 0 ? "crit" : "ok",
    },
  ];

  const topRisk = risks[0];
  const brief = buildFourQuestionBrief({
    what: `${conciliadas} vendas conciliadas; ${semNfce} sem nota; ${itensProd} itens cruzados.`,
    why:
      Number(semNfce) > 0
        ? `${semNfce} venda(s) sem evidência fiscal.`
        : Number(lmc.litrosSemLmc || 0) > 0
          ? `${lmc.litrosSemLmc} litros sem registro operacional.`
          : "Conciliação dentro do esperado.",
    where: topRisk?.empresaCodigo
      ? `Filial ${topRisk.empresaCodigo} · ${panelText(topRisk.dominio, "área fiscal")}`
      : "Rede consolidada",
    actionNow: topRisk
      ? `Corrigir ${panelText(topRisk.dominio, "divergência")} na filial ${topRisk.empresaCodigo || "prioritária"}.`
      : "Validar pendências antes do fechamento.",
  });

  const chartItems = [
    { label: "Com nota", valor: conciliadas },
    { label: "Sem nota", valor: semNfce },
    { label: "Produto", valor: itensProd },
    { label: "Volume OK", valor: lmc.litrosConciliados ?? 0 },
    { label: "Volume pend.", valor: lmc.litrosSemLmc ?? 0 },
  ];
  const chartBars = buildChartBars(chartItems, { labelKey: "label", valueKey: "valor", max: 5 });

  const alerts = risks.slice(0, 3).map((r) =>
    enrichAlert(
      {
        severity: r.risco || "ALTO",
        title: `${panelText(r.dominio, "Área fiscal")} — ${panelText(r.empresaCodigo ? `Filial ${r.empresaCodigo}` : "rede")}`,
        detail: r.produtoCodigo ? `Produto ${r.produtoCodigo}` : "",
        view: "fiscalIntelligence",
        origin: "Fiscal",
      },
      {
        why: panelText(r.risco, "Divergência consolidada"),
        where: r.empresaCodigo ? `Filial ${r.empresaCodigo}` : "Rede",
        actionNow: "Revisar classificação e evidências",
      }
    )
  );

  const detail = `
    <div class="exec-detail-toolbar">
      <button type="button" id="fiscalReconRefresh" class="btn-secondary">Atualizar</button>
      <button type="button" id="fiscalReconExport" class="btn-secondary">Exportar CSV</button>
    </div>
    ${renderTable("Vínculo venda-nota", cockpit.lineageFiscal || [], [
      { key: "vendaCodigo", label: "Venda" },
      { key: "vendaItemCodigo", label: "Item" },
      { key: "produtoCodigo", label: "Produto" },
      { key: "nfceCodigo", label: "Nota" },
      { key: "lmcCodigo", label: "Registro" },
    ])}
    ${renderTable("Divergências de nota", nfce.items || cockpit.divergenciasNfce || [], [
      { key: "tipo", label: "Tipo" },
      { key: "quantidade", label: "Qtd" },
    ])}
    ${renderTable("Divergências de volume", cockpit.divergenciasLmc || [], [
      { key: "tipo", label: "Tipo" },
      { key: "quantidade", label: "Qtd" },
    ])}
    ${renderTable("Riscos consolidados", risks.slice(0, 8), [
      { key: "dominio", label: "Área" },
      { key: "risco", label: "Risco" },
      { key: "empresaCodigo", label: "Filial" },
      { key: "produtoCodigo", label: "Produto" },
    ])}
  `;

  node.innerHTML = buildExecutivePageHtml({
    title: options.pageTitle || "Conciliação",
    actionsHtml: "",
    kpis,
    brief,
    chartBars,
    chartTitle: "Cobertura por domínio",
    criticalBranches: mapCriticalBranches(
      risks.slice(0, 3).map((r) => ({
        name: panelText(r.empresaCodigo ? `Filial ${r.empresaCodigo}` : r.dominio),
        metric: panelText(r.risco, "Dados indisponíveis"),
        tag: panelText(r.dominio, "Fiscal"),
        view: "fiscalIntelligence",
      }))
    ),
    priorityActions: mapPriorityActions(alerts, { defaultView: "fiscalIntelligence" }),
    risks: mapRisks(risks),
    opportunities: [],
    alerts,
    detailHtml: detail,
    detailSummary: "Detalhamento de conciliação",
  });

  node.querySelector("#fiscalReconRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#fiscalReconExport")?.addEventListener("click", () => {
    downloadCsv("conciliacao-fiscal-riscos.csv", risks);
  });
  bindExecutiveNav(node, options.onNavigate);
}
