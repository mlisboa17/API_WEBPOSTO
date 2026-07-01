/** RT-07 — Redirects de views legadas para hubs (UX only). */

export const HUB_VIEWS = new Set(["financialHub", "treasuryHub", "productsHub"]);

export const VIEW_REDIRECTS = {
  dashboard: { view: "financialHub", hubTab: "receitas" },
  expenses: { view: "financialHub", hubTab: "despesas" },
  accounts: { view: "treasuryHub", hubTab: "contas" },
  cashFlow: { view: "treasuryHub", hubTab: "fluxo" },
  cashOperations: { view: "treasuryHub", hubTab: "extratos" },
  financeCenter: { view: "treasuryHub", hubTab: "conciliacao" },
  nonFuelProducts: { view: "productsHub", hubTab: "mix" },
  commercialCopilot: { view: "productsHub", hubTab: "oportunidades" },
  commercialLearning: { view: "productsHub", hubTab: "performance" },
  commercialExecution: { view: "productsHub", hubTab: "mix" },
  executive: { view: "executiveWorkspace" },
  executiveCopilot: { view: "executiveWorkspace" },
  recommendations: { view: "actionCenter" },
  learning: { view: "actionCenter" },
  executiveDecision: { view: "actionCenter" },
  managementAction: { view: "actionCenter" },
  peopleRoi: { view: "administration" },
  operationRoi: { view: "administration" },
  goalsCampaign: { view: "executiveScorecard" },
  benchmark: { view: "executiveScorecard" },
  corporateHub: { view: "executiveWorkspace" },
  lmcIntelligence: { view: "stock" },
  fuels: { view: "sales" },
  fuelExecutive: { view: "sales" },
};

export function resolveViewRoute(view, hubTab = "") {
  const redirect = VIEW_REDIRECTS[view];
  if (!redirect) {
    return { view, hubTab: HUB_VIEWS.has(view) ? hubTab || defaultHubTab(view) : "" };
  }
  if (typeof redirect === "string") {
    return { view: redirect, hubTab: "" };
  }
  return {
    view: redirect.view,
    hubTab: hubTab || redirect.hubTab || defaultHubTab(redirect.view),
  };
}

function defaultHubTab(view) {
  if (view === "financialHub") return "receitas";
  if (view === "treasuryHub") return "fluxo";
  if (view === "productsHub") return "mix";
  return "";
}

export const HUB_TAB_DEFAULTS = {
  financialHub: "receitas",
  treasuryHub: "fluxo",
  productsHub: "mix",
};
