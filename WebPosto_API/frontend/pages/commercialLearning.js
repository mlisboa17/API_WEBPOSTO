import { downloadCsv } from "../services/export.js";
import { bindExecutiveNav } from "../components/executiveFirstFold.js";
import { buildExecutivePageHtml } from "../components/executiveInsightDetail.js";
import { buildChartBars, countKpi, moneyKpi } from "../services/executiveKpis.js";
import {
  buildFourQuestionBrief,
  enrichAlert,
  mapCriticalBranches,
  mapOpportunities,
  mapPriorityActions,
  mapRisks,
} from "../services/executiveBrief.js";

function fmtCount(v) {
  if (v == null || v === "") return "Dados indisponíveis";
  return String(v);
}

function fmtPct(v) {
  if (v == null || v === "") return "Dados indisponíveis";
  return `${v}%`;
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
          return `<td>${val ?? "Dados indisponíveis"}</td>`;
        })
        .join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");
  return `<section class="panel"><h3>${title}</h3><table class="data-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></section>`;
}

export function renderCommercialLearning(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = `<p class="muted">Dados indisponíveis para este período.</p>`;
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const effectiveness = payload.recommendationEffectivenessEngine || {};
  const responsible = payload.responsiblePerformanceEngine || {};
  const branch = payload.branchLearningEngine || {};
  const calibration = payload.recommendationCalibrationEngine || {};
  const outcome = payload.outcomeLearningEngine || {};
  const execReport = payload.executiveLearningReport || {};

  const tipos = effectiveness.porTipo || cockpit.melhoresAcoes || [];
  const owners = responsible.porResponsavel || cockpit.melhoresResponsaveis || [];
  const filiais = branch.porFilial || cockpit.melhoresFiliais || [];
  const calibrations = calibration.calibrations || cockpit.calibrations || [];
  const parecer = payload.parecerFinal || "";

  const totalValidadas = tipos.reduce((sum, row) => sum + Number(row.validadas || 0), 0);
  const taxaAcertoMedia =
    tipos.length > 0
      ? Math.round(
          tipos.reduce((sum, row) => sum + Number(row.taxaAcertoPct || 0), 0) / tipos.length
        )
      : null;
  const roiRealTotal = tipos.reduce((sum, row) => sum + Number(row.roiReal || 0), 0);
  const desvios = calibrations.filter((c) => Number(c.erroPct || 0) > 20);

  const kpis = [
    { label: "Ações validadas", value: countKpi(totalValidadas || null), trendPct: null, status: "ok" },
    { label: "Taxa de acerto", value: taxaAcertoMedia != null ? fmtPct(taxaAcertoMedia) : "Dados indisponíveis", trendPct: null, status: "ok" },
    {
      label: "ROI realizado",
      value: roiRealTotal > 0 ? moneyKpi(roiRealTotal) : countKpi(exec["10_roiRealCitavel"]),
      trendPct: null,
      status: "ok",
    },
    {
      label: "Alertas",
      value: fmtCount(desvios.length || tipos.length || 0),
      trendPct: null,
      status: desvios.length > 0 ? "warn" : "ok",
    },
  ];

  const topTipo = [...tipos].sort((a, b) => Number(b.roiReal || 0) - Number(a.roiReal || 0))[0];
  const topDesvio = [...calibrations].sort((a, b) => Number(b.erroPct || 0) - Number(a.erroPct || 0))[0];

  const brief = buildFourQuestionBrief({
    what: `${countKpi(totalValidadas)} ação(ões) validada(s) com taxa média de ${taxaAcertoMedia != null ? `${taxaAcertoMedia}%` : "Dados indisponíveis"}.`,
    why: topTipo
      ? `${topTipo.tipo || "Tipo dominante"} lidera resultado com ROI ${moneyKpi(topTipo.roiReal)}.`
      : "Evolução comercial em consolidação.",
    where: filiais[0]?.empresaCodigo ? `Filial ${filiais[0].empresaCodigo}` : "Rede consolidada",
    actionNow: topDesvio
      ? `Revisar desvio de ROI em ${topDesvio.tipo || "ação comercial"}.`
      : "Replicar ações com melhor taxa de acerto.",
  });

  const chartBars = buildChartBars(tipos.slice(0, 7), {
    labelKey: "tipo",
    valueKey: "roiReal",
    max: 7,
  });

  const alertSource = desvios.length ? desvios : calibrations;
  const alerts = alertSource.slice(0, 3).map((c) =>
    enrichAlert(
      {
        severity: Number(c.erroPct || 0) > 30 ? "ALTO" : "MÉDIO",
        title: `Desvio de ROI — ${c.tipo || "Ação comercial"}`,
        detail: c.erroPct != null ? `Erro ${c.erroPct}%` : "",
        view: "",
        origin: "Comercial",
      },
      {
        why: "ROI realizado abaixo do previsto",
        where: c.empresaCodigo ? `Filial ${c.empresaCodigo}` : "Rede",
        actionNow: "Ajustar meta e replanejar ação",
      }
    )
  );

  const detail = `
    <div class="exec-detail-toolbar">
      <button type="button" id="commercialLearningRefresh" class="btn-secondary">Atualizar</button>
      <button type="button" id="commercialLearningExport" class="btn-secondary">Exportar CSV</button>
    </div>
    ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
    ${renderTable("Efetividade por tipo de ação", tipos.slice(0, 10), [
      { key: "tipo", label: "Tipo" },
      { key: "validadas", label: "Validadas" },
      { key: "roiReal", label: "ROI real", render: (r) => moneyKpi(r.roiReal) },
      { key: "taxaAcertoPct", label: "Taxa acerto", render: (r) => fmtPct(r.taxaAcertoPct) },
    ])}
    ${renderTable("ROI previsto vs realizado", calibrations.slice(0, 10), [
      { key: "tipo", label: "Tipo" },
      { key: "roiPrevisto", label: "Previsto", render: (r) => moneyKpi(r.roiPrevisto) },
      { key: "roiReal", label: "Realizado", render: (r) => moneyKpi(r.roiReal) },
      { key: "erroPct", label: "Desvio %", render: (r) => fmtPct(r.erroPct) },
      { key: "confidenceLevel", label: "Confiança" },
    ])}
    ${renderTable("Melhores responsáveis", owners.slice(0, 8), [
      { key: "responsavel", label: "Responsável" },
      { key: "acoesValidadas", label: "Validadas" },
      { key: "receitaGerada", label: "Receita", render: (r) => moneyKpi(r.receitaGerada) },
      { key: "roiMedio", label: "ROI médio", render: (r) => moneyKpi(r.roiMedio) },
    ])}
    ${renderTable("Desempenho por filial", filiais.slice(0, 8), [
      { key: "empresaCodigo", label: "Filial" },
      { key: "taxaExecucaoPct", label: "Execução %", render: (r) => fmtPct(r.taxaExecucaoPct) },
      { key: "taxaValidacaoPct", label: "Validação %", render: (r) => fmtPct(r.taxaValidacaoPct) },
      { key: "roiReal", label: "ROI real", render: (r) => moneyKpi(r.roiReal) },
    ])}
    <section class="panel">
      <h3>Resultados das ações</h3>
      <p class="muted">Melhor resultado: <strong>${execReport.melhorAcaoResultado ?? exec["6_melhorAcao"] ?? "Dados indisponíveis"}</strong> · Pior: <strong>${execReport.piorAcao ?? exec["7_piorAcao"] ?? "Dados indisponíveis"}</strong></p>
      <p class="muted">Desvio médio de receita: ${moneyKpi(outcome.erroMedioReceita)} · Evolução no período: ${outcome.melhoraAoLongoDoTempoPct != null ? `${outcome.melhoraAoLongoDoTempoPct}%` : "Dados indisponíveis"}</p>
    </section>
  `;

  node.innerHTML = buildExecutivePageHtml({
    title: options.pageTitle || "Evolução",
    actionsHtml: "",
    kpis,
    brief,
    chartBars,
    chartTitle: "ROI realizado por tipo de ação",
    criticalBranches: mapCriticalBranches(
      filiais.slice(0, 3).map((f) => ({
        name: f.empresaCodigo ? `Filial ${f.empresaCodigo}` : "Rede",
        metric: fmtPct(f.taxaValidacaoPct),
        tag: "Validação",
        view: "",
      }))
    ),
    priorityActions: mapPriorityActions(
      tipos.slice(0, 3).map((t) => ({
        title: t.tipo || "Ação comercial",
        detail: moneyKpi(t.roiReal),
        view: "",
      }))
    ),
    risks: mapRisks(
      desvios.slice(0, 3).map((c) => ({
        title: `Desvio — ${c.tipo || "ação"}`,
        detail: fmtPct(c.erroPct),
        severity: Number(c.erroPct) > 30 ? "ALTO" : "MÉDIO",
      }))
    ),
    opportunities: mapOpportunities(
      owners.slice(0, 3).map((o) => ({
        title: o.responsavel || "Responsável",
        impact: moneyKpi(o.receitaGerada),
        view: "",
      }))
    ),
    alerts,
    detailHtml: detail,
    detailSummary: "Detalhamento de evolução comercial",
  });

  bindExecutiveNav(node, options.onNavigate);
  node.querySelector("#commercialLearningRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#commercialLearningExport")?.addEventListener("click", () => {
    downloadCsv("evolucao-comercial.csv", calibrations);
  });
}
