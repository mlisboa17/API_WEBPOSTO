import { renderDashboard } from "./dashboard.js";
import {
  bindSectionRetry,
  friendlySectionError,
  renderSectionError,
  renderSectionSkeleton,
} from "../components/sectionState.js";

export function renderFinancialOverview(container, payload, options = {}) {
  if (!container) return;

  const sectionUi = options.sectionUi || {};
  const onRetry = options.onRetry;

  if (sectionUi.status === "loading") {
    container.innerHTML = renderSectionSkeleton({
      title: "Carregando visão financeira (overview)…",
      lines: 4,
    });
    return;
  }

  if (sectionUi.status === "error") {
    container.innerHTML = renderSectionError({
      title: "Visão financeira indisponível",
      message: friendlySectionError(sectionUi.error, "a visão financeira"),
      retryId: "overviewSectionRetry",
    });
    bindSectionRetry(container, "overviewSectionRetry", onRetry);
    return;
  }

  const overview = payload?.data ?? payload;
  const resilience = payload?.resilience;

  container.innerHTML = "";

  if (!overview) {
    container.innerHTML = renderSectionError({
      title: "Sem dados consolidados",
      message: "Não há visão financeira para o período selecionado.",
      retryId: "overviewSectionRetry",
      retryLabel: "Recarregar seção",
    });
    bindSectionRetry(container, "overviewSectionRetry", onRetry);
    return;
  }

  const postos = overview?.postos || [];
  if (resilience?.source === "degraded" && postos.length === 0) {
    const hint =
      resilience?.banner ||
      "Integração protegida — dados consolidados serão exibidos quando disponíveis.";
    container.innerHTML = renderSectionError({
      title: "Dados temporariamente indisponíveis",
      message: hint,
      retryId: "overviewSectionRetry",
      retryLabel: "Tentar novamente",
      icon: "⏳",
    });
    bindSectionRetry(container, "overviewSectionRetry", onRetry);
    return;
  }

  renderDashboard(container, overview, { ...options, resilience });
}
