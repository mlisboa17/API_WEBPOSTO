/** RT-06 Adendo — Brief executivo (4 perguntas) e painéis de decisão. Sem API nova. */

export function buildFourQuestionBrief({ what, why, where, actionNow }) {
  return {
    what: what || "Sem movimento relevante no período.",
    why: why || "Sem causa dominante identificada.",
    where: where || "Rede consolidada.",
    actionNow: actionNow || "Manter monitoramento do período.",
  };
}

export function enrichAlert(alert, { why, where, actionNow } = {}) {
  return {
    ...alert,
    why: why || alert.why || alert.detail || "",
    where: where || alert.where || alert.origin || "",
    actionNow: actionNow || alert.actionNow || (alert.view ? "Abrir tela relacionada" : ""),
  };
}

export function mapCriticalBranches(rows = [], { max = 3, view = "" } = {}) {
  return rows.slice(0, max).map((row) => ({
    name: row.name || row.filial || row.nome || "—",
    metric: row.metric || row.valor || "—",
    tag: row.tag || row.severity || "",
    view: row.view || view,
  }));
}

export function mapPriorityActions(rows = [], { max = 3, defaultView = "" } = {}) {
  return rows.slice(0, max).map((row) => ({
    title: row.title || row.titulo || row.tipo || "Ação prioritária",
    detail: row.detail || row.descricao || row.impact || row.filial || "",
    view: row.view || defaultView,
  }));
}

export function mapRisks(rows = [], { max = 3 } = {}) {
  return rows.slice(0, max).map((row) => ({
    title: row.title || row.titulo || row.tipo || row.nome || "Risco",
    detail: row.detail || row.descricao || row.message || "",
    severity: row.severity || row.level || row.risco || "MÉDIO",
  }));
}

export function mapOpportunities(rows = [], { max = 3, defaultView = "" } = {}) {
  return rows.slice(0, max).map((row) => ({
    title: row.title || row.titulo || row.recomendacao || "Oportunidade",
    impact: row.impact || row.impacto || row.impactoEstimado || "",
    view: row.view || defaultView,
  }));
}

export function topFilialByField(rows, accessor, valueKey = "valor") {
  const totals = {};
  (rows || []).forEach((row) => {
    const name = accessor(row);
    if (!name || name === "—") return;
    totals[name] = (totals[name] || 0) + Number(row[valueKey] || 0);
  });
  const sorted = Object.entries(totals).sort((a, b) => b[1] - a[1]);
  if (!sorted.length) return null;
  return { name: sorted[0][0], total: sorted[0][1] };
}
