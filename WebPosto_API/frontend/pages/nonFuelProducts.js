import { downloadCsv } from "../services/export.js";
import { bindExecutiveNav, renderExecutiveEmptyState } from "../components/executiveFirstFold.js";
import { buildExecutivePageHtml } from "../components/executiveInsightDetail.js";
import { buildChartBars, moneyKpi } from "../services/executiveKpis.js";
import {
  buildFourQuestionBrief,
  enrichAlert,
  mapCriticalBranches,
  mapOpportunities,
  mapPriorityActions,
  mapRisks,
} from "../services/executiveBrief.js";

function panelText(value, fallback = "Não informado") {
  if (value == null || value === "" || value === "—") return fallback;
  return value;
}

function panelMetric(value) {
  if (value == null || value === "" || value === "—") return "Dados indisponíveis";
  return value;
}

function cellText(value) {
  if (value == null || value === "" || value === "—") return "Não informado";
  return value;
}

function cellMetric(value) {
  if (value == null || value === "" || value === "—") return "Vazio";
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
          const display = c.metric ? cellMetric(val) : cellText(val);
          return `<td>${display}</td>`;
        })
        .join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");
  return `<section class="panel"><h3>${title}</h3><table class="data-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></section>`;
}

function kpiMoney(value, hasContext) {
  if (value == null || value === "" || value === "—") return "Dados indisponíveis";
  if (!hasContext && Number(value) === 0) return "Dados indisponíveis";
  return moneyKpi(value);
}

function branchLabel(row) {
  return row?.empresaNome || row?.nomeFilial || (row?.empresaCodigo ? `Filial ${row.empresaCodigo}` : "Rede");
}

export function renderNonFuelProducts(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = renderExecutiveEmptyState({
      title: options.pageTitle || "Mix & Vendas",
      message: "Não foi possível montar esta visão no período selecionado.",
      chartTitle: "Top produtos por receita (Pareto)",
    });
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const pareto = payload.productRevenueIntelligence?.pareto || cockpit.pareto8020 || [];
  const actionCenter = payload.commercialActionCenter || {};
  const acSummary = actionCenter.summary || {};
  const acoes = actionCenter.actions || cockpit.acoesComerciais || cockpit.acoesAltaPrioridade || [];
  const acoesAlta = cockpit.acoesAltaPrioridade || acoes.filter((a) => a.prioridade === "ALTA").slice(0, 8);
  const branch = payload.branchProductMix?.filiais || cockpit.mixPorFilial || [];
  const depts =
    payload.departmentRefinement?.porDepartamento
      ? Object.entries(payload.departmentRefinement.porDepartamento).map(([departamento, qtd]) => ({
          departamento,
          itens: qtd,
        }))
      : payload.departmentIntelligence?.receitaPorDepartamento || cockpit.topDepartamentos || [];
  const alertasMargem = payload.opportunityEngine?.highVolumeLowMargin?.produtos || cockpit.alertasBaixaMargem || [];

  const receitaVal = exec["1_receitaProdutosVendidos"] ?? cockpit.receitaTotal;
  const margemVal = exec["9_margemRealizada"] ?? cockpit.margemRealizada ?? cockpit.margemBruta;
  const hasProductData = Boolean(pareto.length || branch.length || depts.length);
  const receitaKpi = kpiMoney(receitaVal, hasProductData);
  const margemKpi = kpiMoney(margemVal, hasProductData && margemVal != null);
  const alertasCount = acoesAlta.length || alertasMargem.length;

  const kpis = [
    { label: "Receita", value: receitaKpi, trendPct: null, status: "ok" },
    { label: "Despesa", value: "Dados indisponíveis", trendPct: null, status: "ok" },
    { label: "Margem", value: margemKpi, trendPct: null, status: "ok" },
    {
      label: "Alertas",
      value: String(alertasCount || 0),
      trendPct: null,
      status: alertasCount > 0 ? "crit" : "ok",
    },
  ];

  const topProduct = pareto[0];
  const topBranch = [...branch].sort(
    (a, b) => Number(b.mixProdutosVendidosPct || 0) - Number(a.mixProdutosVendidosPct || 0)
  )[0];
  const lowMargin = alertasMargem[0];

  const brief = buildFourQuestionBrief({
    what:
      receitaKpi !== "Dados indisponíveis"
        ? `Produtos vendidos geraram ${receitaKpi} com margem ${margemKpi}.`
        : "Dados de produtos vendidos indisponíveis para este período.",
    why: topProduct
      ? `${topProduct.nome || "Top produto"} lidera receita — ${lowMargin ? "com alerta de margem baixa" : "mix saudável"}.`
      : "Receita concentrada em poucos SKUs.",
    where: topBranch ? `${branchLabel(topBranch)} destaca no mix.` : "Distribuição entre filiais a validar.",
    actionNow: acoesAlta[0]
      ? `Executar: ${acoesAlta[0].titulo || acoesAlta[0].tipo || "ação comercial prioritária"}.`
      : "Revisar produtos de alto volume e baixa margem.",
  });

  const chartBars = buildChartBars(pareto, { labelKey: "nome", valueKey: "valor", max: 7 });
  const alertSource = acoesAlta.length ? acoesAlta : alertasMargem;
  const alerts = alertSource.slice(0, 3).map((a) => {
    const isMarginAlert = !a.titulo && !a.tipo && (a.nome || a.produto);
    return enrichAlert(
      {
        severity: a.prioridade || "ALTO",
        title: isMarginAlert
          ? `Margem baixa — ${a.nome || a.produto}`
          : a.titulo || a.descricao || a.tipo || "Ação comercial",
        detail: isMarginAlert ? a.motivo || "Alto volume, margem comprimida" : a.empresaCodigo ? `Filial ${a.empresaCodigo}` : "",
        view: "commercialExecution",
        origin: "Comercial",
      },
      {
        why: isMarginAlert
          ? a.motivo || "Alto volume com margem comprimida"
          : a.tipo || "Oportunidade de receita incremental",
        where: a.empresaCodigo ? `Filial ${a.empresaCodigo}` : branchLabel(a) || "Rede",
        actionNow: isMarginAlert ? "Revisar precificação e mix do produto" : "Abrir plano de ação comercial",
      }
    );
  });

  const detail = `
    ${renderTable("Plano de ação comercial", acoes.slice(0, 12), [
      { key: "tipo", label: "Tipo" },
      { key: "titulo", label: "Ação" },
      { key: "prioridade", label: "Prioridade" },
      { key: "status", label: "Status" },
      { key: "responsavel", label: "Responsável", render: (r) => cellText(r.responsavel?.ownerName) },
    ])}
    ${renderTable("Mix por filial", branch, [
      { key: "empresaCodigo", label: "Filial", render: (r) => cellText(r.empresaCodigo) },
      { key: "empresaNome", label: "Nome", render: (r) => cellText(r.empresaNome ?? r.nomeFilial) },
      { key: "mixProdutosVendidosPct", label: "Mix PV %", metric: true, render: (r) => (r.mixProdutosVendidosPct != null ? `${r.mixProdutosVendidosPct}%` : null) },
    ])}
    ${renderTable("Departamentos", depts.slice(0, 8), [
      { key: "departamento", label: "Departamento", render: (r) => cellText(r.departamento ?? r.nome) },
      {
        key: "receita",
        label: "Receita R$",
        metric: true,
        render: (r) => ((r.receita ?? r.valor) != null ? Number(r.receita ?? r.valor).toFixed(2) : null),
      },
    ])}
  `;

  node.innerHTML = buildExecutivePageHtml({
    title: options.pageTitle || "Mix & Vendas",
    actionsHtml: "",
    kpis,
    brief,
    chartBars,
    chartTitle: "Top produtos por receita (Pareto)",
    criticalBranches: mapCriticalBranches(
      branch
        .slice()
        .sort((a, b) => Number(a.mixProdutosVendidosPct || 0) - Number(b.mixProdutosVendidosPct || 0))
        .slice(0, 3)
        .map((b) => ({
          name: panelText(b.empresaNome || (b.empresaCodigo ? `Filial ${b.empresaCodigo}` : null)),
          metric: b.mixProdutosVendidosPct != null ? `${b.mixProdutosVendidosPct}% mix` : "Dados indisponíveis",
          tag: "Mix baixo",
          view: "nonFuelProducts",
        }))
    ),
    priorityActions: mapPriorityActions(acoesAlta, { defaultView: "commercialExecution" }),
    risks: mapRisks(
      alertasMargem.slice(0, 3).map((p) => ({
        title: p.nome || p.produto || "Margem baixa",
        detail: p.motivo || "Alto volume, margem comprimida",
        severity: "ALTO",
      }))
    ),
    opportunities: mapOpportunities(
      acoes.slice(0, 3).map((a) => ({
        title: panelText(a.titulo || a.tipo, "Oportunidade comercial"),
        impact: a.empresaCodigo ? `Filial ${a.empresaCodigo}` : "Não informado",
        view: "commercialExecution",
      }))
    ),
    alerts,
    detailHtml: detail,
    detailSummary: "Detalhamento comercial",
  });

  node.querySelector("#nonFuelRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#nonFuelExport")?.addEventListener("click", () => {
    downloadCsv("produtos-vendidos-acoes-comerciais.csv", acoes.length ? acoes : acoesAlta);
  });
  bindExecutiveNav(node, options.onNavigate);
}
