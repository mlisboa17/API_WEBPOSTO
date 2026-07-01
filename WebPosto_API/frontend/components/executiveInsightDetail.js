import { renderDecisionPanel, renderExecutiveBrief, renderExecutiveFirstFold, wrapExecutiveDetail } from "./executiveFirstFold.js";

/** RT-06A — Brief + painel de decisão ficam no detalhamento, não na 1ª dobra. */
export function renderExecutiveInsightDetail({ brief, criticalBranches, priorityActions, risks, opportunities } = {}) {
  const briefHtml = brief ? renderExecutiveBrief(brief) : "";
  const panelHtml = renderDecisionPanel({ criticalBranches, priorityActions, risks, opportunities });
  if (!briefHtml && !panelHtml) return "";
  return `<div class="exec-insight-detail">${briefHtml}${panelHtml}</div>`;
}

export function buildExecutivePageHtml(options = {}) {
  const {
    brief,
    criticalBranches,
    priorityActions,
    risks,
    opportunities,
    detailHtml = "",
    detailSummary = "Detalhamento",
    ...firstFoldProps
  } = options;
  const insight = renderExecutiveInsightDetail({
    brief,
    criticalBranches,
    priorityActions,
    risks,
    opportunities,
  });
  return `${renderExecutiveFirstFold(firstFoldProps)}${wrapExecutiveDetail(`${insight}${detailHtml}`, detailSummary)}`;
}
