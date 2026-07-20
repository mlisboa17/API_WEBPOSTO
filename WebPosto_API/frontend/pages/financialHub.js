import { mountHubShell } from "../components/hubShell.js";
import { renderExecutiveEmptyState, setViewTitle } from "../components/executiveFirstFold.js";
import { renderFinancialOverview } from "./financialOverview.js";
import { renderFinancialExpenses } from "./financialExpenses.js";
import { renderSectionSkeleton } from "../components/sectionState.js";

const TABS = [
  { id: "receitas", label: "Receitas" },
  { id: "despesas", label: "Despesas" },
];

const TAB_TITLES = {
  receitas: "Receitas",
  despesas: "Despesas",
};

let shellInstance = null;
let latestProps = null;

function renderHubEmptyState(contentEl, tabId, message) {
  contentEl.innerHTML = renderExecutiveEmptyState({
    title: TAB_TITLES[tabId] || "Visão Financeira",
    message,
    chartTitle: tabId === "receitas" ? "Receitas por filial no período" : "Despesas por natureza",
  });
}

export function renderFinancialHub(container, props) {
  if (!container) return;
  latestProps = props;
  const { activeTab, data, filters, options = {}, companies = [] } = props;
  const tabId = activeTab || "receitas";

  setViewTitle(TAB_TITLES[tabId] || "Visão Financeira");

  if (!container.querySelector("#financialHubShell")) {
    container.innerHTML = `<div id="financialHubShell"></div>`;
    shellInstance = null;
  }

  const host = container.querySelector("#financialHubShell");

  const renderContent = (contentEl, currentTabId) => {
    const p = latestProps || props;
    setViewTitle(TAB_TITLES[currentTabId] || "Visão Financeira");

    if (currentTabId === "receitas") {
      const overview = p.data?.overview;
      const resilience = p.data?.overviewResilience;
      const overviewUi = p.data?.overviewUi || {};

      if (overviewUi.status === "loading") {
        contentEl.innerHTML = renderSectionSkeleton({ title: "Carregando receitas e overview…", lines: 4 });
        return;
      }

      renderFinancialOverview(
        contentEl,
        { data: overview, resilience },
        {
          ...p.options?.receitas,
          filters: p.filters,
          revenueTotal: p.data?.revenueTotal,
          companies: p.companies,
          sectionUi: overviewUi,
          onRetry: p.options?.receitas?.onRetry,
        }
      );
      return;
    }

    const expensesPayload = p.data?.expenses;
    const expensesResilience = p.data?.expensesResilience;

    if (!expensesPayload?.data?.length && expensesResilience?.source === "degraded") {
      renderHubEmptyState(
        contentEl,
        currentTabId,
        "Integração protegida — despesas serão exibidas quando disponíveis."
      );
      return;
    }

    renderFinancialExpenses(
      contentEl,
      { data: expensesPayload, resilience: expensesResilience },
      p.options?.onPageChange,
      { ...p.options?.despesas, filters: p.filters, companies: p.companies }
    );
  };

  if (!shellInstance) {
    shellInstance = mountHubShell(host, {
      tabs: TABS,
      activeTab: tabId,
      onTabChange: options.onTabChange,
      renderContent,
    });
  } else if (activeTab && shellInstance.getTab() !== activeTab) {
    shellInstance.setTab(activeTab);
  } else {
    shellInstance.refresh();
  }
}
