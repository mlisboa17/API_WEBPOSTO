import { formatCurrency } from "../services/format.js";
import { downloadCsv } from "../services/export.js";
import { bindExecutiveNav } from "../components/executiveFirstFold.js";
import { buildExecutivePageHtml } from "../components/executiveInsightDetail.js";
import { buildChartBars, countKpi } from "../services/executiveKpis.js";
import {
  buildFourQuestionBrief,
  enrichAlert,
  mapOpportunities,
  mapPriorityActions,
  mapRisks,
} from "../services/executiveBrief.js";

function fmtMoney(v) {
  if (v === null || v === undefined) return "Dados indisponíveis";
  return formatCurrency(v);
}

function fmtCount(v) {
  if (v == null || v === "") return "Dados indisponíveis";
  return String(v);
}

function renderAnswerCard(item) {
  const labels = (item.labels || []).map((l) => `<span class="tag">${l}</span>`).join(" ");
  const sourceHint = (item.lineage || [])
    .slice(0, 1)
    .map((l) => l.origem)
    .filter(Boolean)
    .join("");
  return `
    <article class="panel commercial-answer">
      <p><strong>${item.answer || "Dados indisponíveis"}</strong></p>
      <p class="muted">Nível de confiança: ${item.confidenceLevel || "Dados indisponíveis"} ${labels}</p>
      ${sourceHint ? `<p class="muted">Fonte: ${sourceHint}</p>` : ""}
      ${item.blocked ? `<p class="warn">Informação não disponível para decisão neste recorte.</p>` : ""}
    </article>
  `;
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
          if (c.money) return `<td>${fmtMoney(val)}</td>`;
          return `<td>${val ?? "Dados indisponíveis"}</td>`;
        })
        .join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");
  return `<section class="panel"><h3>${title}</h3><table class="data-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></section>`;
}

export function renderCommercialCopilot(node, payload, filters, options = {}) {
  if (!node) return;
  if (!payload) {
    node.innerHTML = `<p class="muted">Dados indisponíveis para este período.</p>`;
    return;
  }

  const cockpit = payload.cockpit || {};
  const exec = payload.executiveAnswers || {};
  const faq = cockpit.perguntasHomologadas || payload.commercialReasoningEngine?.catalog || [];
  const recs = payload.commercialRecommendationEngine?.recommendations || cockpit.recomendacoes || [];
  const ac = payload.commercialActionCenterIntegration || {};
  const parecer = payload.parecerFinal || "";

  const oportunidades = exec["6_totalRecomendacoes"] ?? recs.length;
  const validadas = exec["9_acoesValidadas"] ?? ac.acoesValidadas;
  const roiReal = exec["10_roiRealCitavel"] ?? ac.acoesComRoiReal;
  const alertasCount = recs.filter((r) => /alta|crit/i.test(String(r.classificacao || r.prioridade || ""))).length || recs.length;

  const kpis = [
    { label: "Oportunidades", value: countKpi(oportunidades), trendPct: null, status: "ok" },
    { label: "Ações validadas", value: countKpi(validadas), trendPct: null, status: "ok" },
    { label: "ROI realizado", value: countKpi(roiReal), trendPct: null, status: "ok" },
    {
      label: "Alertas",
      value: fmtCount(alertasCount),
      trendPct: null,
      status: alertasCount > 0 ? "warn" : "ok",
    },
  ];

  const topRec = recs[0];
  const brief = buildFourQuestionBrief({
    what: `${countKpi(oportunidades)} oportunidade(s) comercial(is) identificada(s) no período.`,
    why: topRec
      ? `${topRec.titulo || topRec.tipo || "Ação prioritária"} — ${topRec.classificacao || "prioridade comercial"}.`
      : "Sem recomendações dominantes no recorte.",
    where: topRec?.empresaCodigo ? `Filial ${topRec.empresaCodigo}` : "Rede consolidada",
    actionNow: topRec
      ? `Validar: ${topRec.titulo || topRec.tipo || "ação comercial"}.`
      : "Revisar oportunidades pendentes de validação.",
  });

  const chartBars = buildChartBars(recs.slice(0, 7), {
    labelKey: "titulo",
    valueKey: "roiEstimado",
    max: 7,
  });

  const alerts = recs.slice(0, 3).map((r) =>
    enrichAlert(
      {
        severity: /alta|crit/i.test(String(r.classificacao || "")) ? "ALTO" : "MÉDIO",
        title: r.titulo || r.tipo || "Oportunidade comercial",
        detail: fmtMoney(r.roiEstimado),
        view: "commercialExecution",
        origin: "Comercial",
      },
      {
        why: r.classificacao || r.tipo || "Potencial de receita incremental",
        where: r.empresaCodigo ? `Filial ${r.empresaCodigo}` : "Rede",
        actionNow: "Validar e executar plano comercial",
      }
    )
  );

  const detail = `
    <div class="exec-detail-toolbar">
      <button type="button" id="commercialCopilotRefresh" class="btn-secondary">Atualizar</button>
      <button type="button" id="commercialCopilotExport" class="btn-secondary">Exportar CSV</button>
    </div>
    ${parecer ? `<p class="parecer">${parecer}</p>` : ""}
    <section class="panel">
      <h3>Consulta comercial</h3>
      <div class="commercial-ask-row">
        <input type="text" id="commercialCopilotQuestionInput" placeholder="Ex.: Qual produto gera mais receita?" class="commercial-input" />
        <button type="button" id="commercialCopilotAskBtn" class="btn-primary">Consultar</button>
      </div>
      <div id="commercialCopilotAskResult"></div>
    </section>
    <section class="panel"><h3>Perguntas frequentes</h3><div class="commercial-faq">${faq.slice(0, 6).map(renderAnswerCard).join("")}</div></section>
    ${renderTable("Recomendações comerciais", recs.slice(0, 8), [
      { key: "classificacao", label: "Prioridade" },
      { key: "tipo", label: "Tipo" },
      { key: "titulo", label: "Ação" },
      { key: "roiEstimado", label: "ROI estimado", money: true },
      { key: "confidenceLevel", label: "Confiança" },
    ])}
    ${renderTable("Ações em acompanhamento", ac.listagem || [], [
      { key: "tipo", label: "Tipo" },
      { key: "status", label: "Status" },
      { key: "roiReal", label: "ROI realizado", money: true },
      { key: "empresaCodigo", label: "Filial" },
    ])}
  `;

  node.innerHTML = buildExecutivePageHtml({
    title: options.pageTitle || "Ações comerciais",
    actionsHtml: "",
    kpis,
    brief,
    chartBars,
    chartTitle: "Oportunidades por ROI estimado",
    criticalBranches: [],
    priorityActions: mapPriorityActions(
      recs.slice(0, 3).map((r) => ({
        title: r.titulo || r.tipo,
        detail: r.classificacao || "",
        view: "commercialExecution",
      }))
    ),
    risks: mapRisks(
      recs
        .filter((r) => /alta|crit/i.test(String(r.classificacao || "")))
        .slice(0, 3)
        .map((r) => ({
          title: r.titulo || r.tipo || "Oportunidade prioritária",
          detail: fmtMoney(r.roiEstimado),
          severity: "ALTO",
        }))
    ),
    opportunities: mapOpportunities(
      recs.slice(0, 3).map((r) => ({
        title: r.titulo || r.tipo,
        impact: fmtMoney(r.roiEstimado),
        view: "commercialExecution",
      }))
    ),
    alerts,
    detailHtml: detail,
    detailSummary: "Detalhamento comercial",
  });

  node.querySelector("#commercialCopilotRefresh")?.addEventListener("click", () => options.onRefresh?.());
  node.querySelector("#commercialCopilotExport")?.addEventListener("click", () => {
    downloadCsv("acoes-comerciais.csv", recs);
  });
  node.querySelector("#commercialCopilotAskBtn")?.addEventListener("click", async () => {
    const input = node.querySelector("#commercialCopilotQuestionInput");
    const resultNode = node.querySelector("#commercialCopilotAskResult");
    const q = input?.value?.trim();
    if (!q || !options.onAsk) return;
    resultNode.innerHTML = `<p class="muted">Consultando…</p>`;
    try {
      const data = await options.onAsk(q);
      const resp = data?.answer || data?.resposta || data;
      resultNode.innerHTML = renderAnswerCard(resp);
    } catch (err) {
      resultNode.innerHTML = `<p class="warn">Não foi possível obter resposta: ${err.message || err}</p>`;
    }
  });
  bindExecutiveNav(node, options.onNavigate);
}
