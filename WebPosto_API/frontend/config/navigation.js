/** UX-01 — Arquitetura de informação (6 macro áreas). */
export const NAV_AREAS = [
  {
    id: "executivo",
    icon: "📊",
    label: "Executivo",
    tabs: [
      { id: "resumo", label: "Resumo", view: "executiveWorkspace" },
      { id: "indicadores", label: "Indicadores", view: "executiveScorecard" },
      { id: "alertas", label: "Alertas", view: "actionCenter" },
      { id: "metas", label: "Metas", view: "goalsCampaign" },
    ],
    motors: [
      "executive",
      "executiveWorkspace",
      "dashboard",
      "executiveScorecard",
      "benchmark",
      "corporateHub",
      "executiveDecision",
      "actionCenter",
      "executiveCopilot",
      "recommendations",
      "learning",
      "goalsCampaign",
    ],
  },
  {
    id: "financeiro",
    icon: "💰",
    label: "Financeiro",
    tabs: [
      { id: "receitas", label: "Receitas", view: "dashboard" },
      { id: "despesas", label: "Despesas", view: "expenses" },
      { id: "contas", label: "Contas", view: "accounts" },
      { id: "fluxo", label: "Fluxo de Caixa", view: "cashFlow" },
      { id: "extratos", label: "Extratos", view: "cashOperations" },
      { id: "conciliacao", label: "Conciliação", view: "financeCenter" },
      { id: "operations_center", label: "Operations Center", view: "financialOperationsCenter" },
      { id: "intelligence", label: "Intelligence", view: "financialIntelligence" },
    ],
    motors: [
      "dashboard",
      "expenses",
      "accounts",
      "financeCenter",
      "cashFlow",
      "cashOperations",
      "financialOperationsCenter",
      "financialIntelligence",
      "operatorPerformance",
      "peopleIntelligence",
      "peopleRoi",
      "operationRoi",
      "managementAction",
    ],
  },
  {
    id: "combustiveis",
    icon: "⛽",
    label: "Combustíveis",
    tabs: [
      { id: "vendas", label: "Vendas", view: "sales" },
      { id: "tanques", label: "Tanques", view: "stock" },
      { id: "bombas", label: "Bombas", view: "fuels" },
      { id: "lmc", label: "LMC", view: "lmcIntelligence" },
      { id: "governanca", label: "Governança", view: "fuelGovernance" },
    ],
    motors: ["sales", "stock", "fuels", "fuelExecutive", "lmcIntelligence", "fuelGovernance"],
  },
  {
    id: "produtos_vendidos",
    icon: "🛒",
    label: "Produtos Vendidos",
    tabs: [
      { id: "vendas", label: "Vendas", view: "nonFuelProducts" },
      { id: "margem", label: "Margem", view: "nonFuelProducts" },
      { id: "mix", label: "Mix", view: "nonFuelProducts" },
      { id: "oportunidades", label: "Oportunidades", view: "commercialCopilot" },
      { id: "acoes", label: "Ações", view: "commercialExecution" },
      { id: "resultados", label: "Resultados", view: "commercialLearning" },
    ],
    motors: ["nonFuelProducts", "commercialExecution", "commercialLearning", "commercialCopilot"],
  },
  {
    id: "fiscal",
    icon: "📑",
    label: "Fiscal",
    tabs: [
      { id: "nfce", label: "NFCE", view: "nfceIntelligence" },
      { id: "conciliacao", label: "Conciliação", view: "fiscalReconciliation" },
      { id: "tributacao", label: "Tributação", view: "fiscalIntelligence" },
      { id: "riscos", label: "Riscos", view: "fiscalIntelligence" },
    ],
    motors: ["nfceIntelligence", "fiscalIntelligence", "fiscalReconciliation"],
  },
  {
    id: "administracao",
    icon: "⚙️",
    label: "Administração",
    tabs: [
      { id: "filiais", label: "Filiais", view: "administration" },
      { id: "usuarios", label: "Usuários", view: "administration" },
      { id: "permissoes", label: "Permissões", view: "administration" },
      { id: "integracoes", label: "Integrações", view: "administration" },
      { id: "configuracoes", label: "Configurações", view: "administration" },
    ],
    motors: ["administration", "financialOperationsCenter"],
  },
];

/** Mapa view → área (para deep links ?view=). */
export const VIEW_TO_AREA = {};
NAV_AREAS.forEach((area) => {
  area.tabs.forEach((tab) => {
    VIEW_TO_AREA[tab.view] = area.id;
  });
  area.motors.forEach((view) => {
    if (!VIEW_TO_AREA[view]) {
      VIEW_TO_AREA[view] = area.id;
    }
  });
});

export function resolveAreaForView(view) {
  return VIEW_TO_AREA[view] || "executivo";
}

export function getAreaById(areaId) {
  return NAV_AREAS.find((area) => area.id === areaId) || NAV_AREAS[0];
}

export function getDefaultViewForArea(areaId) {
  const area = getAreaById(areaId);
  return area.tabs[0]?.view || "executive";
}

export function countLegacyVisibleModules() {
  return 30;
}

export function countVisibleMacroAreas() {
  return NAV_AREAS.length;
}
