import { mountHubShell } from "../components/hubShell.js";
import { renderCashFlow } from "./cashFlow.js";
import { renderAccountsPayable } from "./accountsPayable.js";
import { renderCashOperations } from "./cashOperations.js";
import { renderFinanceCenter } from "./financeCenter.js";
import { periodSubtitle } from "../services/executiveKpis.js";

const TABS = [
  { id: "fluxo", label: "Fluxo de caixa" },
  { id: "contas", label: "Contas a pagar" },
  { id: "extratos", label: "Extratos" },
  { id: "conciliacao", label: "Conciliação" },
];

let shellInstance = null;
let latestProps = null;

export function renderTreasuryHub(container, props) {
  if (!container) return;
  latestProps = props;
  const { activeTab, data, filters, options = {} } = props;

  if (!container.querySelector("#treasuryHubShell")) {
    container.innerHTML = `<div id="treasuryHubShell"></div>`;
    shellInstance = null;
  }

  const host = container.querySelector("#treasuryHubShell");

  const renderContent = (contentEl, tabId) => {
    const p = latestProps || props;
    switch (tabId) {
      case "contas":
        renderAccountsPayable(contentEl, p.data?.accounts, p.options?.onAccountsPageChange, {
          ...p.options?.accounts,
          filters: p.filters,
        });
        break;
      case "extratos":
        renderCashOperations(contentEl, p.data?.cashOperations, p.filters, p.options?.extratos);
        break;
      case "conciliacao":
        renderFinanceCenter(contentEl, p.data?.financeCenter, p.filters, p.options?.conciliacao);
        break;
      case "fluxo":
      default:
        renderCashFlow(contentEl, p.data?.cashFlow, p.filters, p.options?.fluxo);
        break;
    }
  };

  if (!shellInstance) {
    shellInstance = mountHubShell(host, {
      tabs: TABS,
      activeTab: activeTab || "fluxo",
      onTabChange: options.onTabChange,
      renderContent,
    });
  } else if (activeTab && shellInstance.getTab() !== activeTab) {
    shellInstance.setTab(activeTab);
  } else {
    shellInstance.refresh();
  }
}
