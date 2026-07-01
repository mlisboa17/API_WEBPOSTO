import { mountHubShell } from "../components/hubShell.js";
import { renderExecutiveEmptyState, setViewTitle } from "../components/executiveFirstFold.js";
import { renderNonFuelProducts } from "./nonFuelProducts.js";
import { renderCommercialCopilot } from "./commercialCopilot.js";
import { renderCommercialLearning } from "./commercialLearning.js";

const TABS = [
  { id: "mix", label: "Mix & Vendas" },
  { id: "oportunidades", label: "Ações comerciais" },
  { id: "performance", label: "Evolução" },
];

const TAB_TITLES = {
  mix: "Mix & Vendas",
  oportunidades: "Ações comerciais",
  performance: "Evolução",
};

const HUB_CHART_TITLES = {
  mix: "Top produtos por receita (Pareto)",
  oportunidades: "Oportunidades por ROI estimado",
  performance: "ROI realizado por tipo de ação",
};

const HUB_PAYLOAD_KEYS = {
  mix: "nonFuelProducts",
  oportunidades: "commercialCopilot",
  performance: "commercialLearning",
};

function renderHubEmpty(contentEl, tabId) {
  contentEl.innerHTML = renderExecutiveEmptyState({
    title: TAB_TITLES[tabId] || "Produtos Vendidos",
    message: "Não foi possível montar esta visão no período selecionado.",
    chartTitle: HUB_CHART_TITLES[tabId] || "Desempenho no período",
  });
}

let shellInstance = null;
let latestProps = null;

export function renderProductsHub(container, props) {
  if (!container) return;
  latestProps = props;
  const { activeTab, data, filters, options = {} } = props;
  const tabId = activeTab || "mix";

  setViewTitle(TAB_TITLES[tabId] || "Produtos Vendidos");

  if (!container.querySelector("#productsHubShell")) {
    container.innerHTML = `<div id="productsHubShell"></div>`;
    shellInstance = null;
  }

  const host = container.querySelector("#productsHubShell");

  const renderContent = (contentEl, currentTabId) => {
    const p = latestProps || props;
    setViewTitle(TAB_TITLES[currentTabId] || "Produtos Vendidos");
    const payloadKey = HUB_PAYLOAD_KEYS[currentTabId];
    const tabPayload = payloadKey ? p.data?.[payloadKey] : null;

    if (!tabPayload) {
      renderHubEmpty(contentEl, currentTabId);
      return;
    }

    switch (currentTabId) {
      case "oportunidades":
        renderCommercialCopilot(contentEl, tabPayload, p.filters, {
          ...p.options?.oportunidades,
          onAsk: p.options?.onCopilotAsk,
          pageTitle: TAB_TITLES.oportunidades,
        });
        break;
      case "performance":
        renderCommercialLearning(contentEl, tabPayload, p.filters, {
          ...p.options?.performance,
          pageTitle: TAB_TITLES.performance,
        });
        break;
      case "mix":
      default:
        renderNonFuelProducts(contentEl, tabPayload, p.filters, {
          ...p.options?.mix,
          onNavigate: p.options?.onNavigate,
          pageTitle: TAB_TITLES.mix,
        });
        break;
    }
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
