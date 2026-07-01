/** UX-01 + RT-03B + RT-07 + RT-07.2 — Navegação executiva simplificada. */



export const NAV_AREAS = [

  {

    id: "executivo",

    icon: "📊",

    label: "Executivo",

    tabs: [

      { id: "presidente", label: "Presidente", view: "presidentDashboard" },

      { id: "resumo", label: "Resumo", view: "executiveWorkspace" },

      { id: "indicadores", label: "Indicadores", view: "executiveScorecard" },

      { id: "alertas", label: "Alertas", view: "actionCenter" },

    ],

    motors: [],

  },

  {

    id: "financeiro",

    icon: "💰",

    label: "Financeiro",

    tabs: [

      { id: "visao", label: "Visão Financeira", view: "financialHub" },

      { id: "inteligencia", label: "Inteligência", view: "financialIntelligence" },

      { id: "tesouraria", label: "Tesouraria", view: "treasuryHub" },

    ],

    motors: [],

  },

  {

    id: "combustiveis",

    icon: "⛽",

    label: "Combustíveis",

    tabs: [

      { id: "vendas", label: "Vendas", view: "sales" },

      { id: "estoque", label: "Estoque", view: "stock" },

      { id: "governanca", label: "Governança", view: "fuelGovernance" },

    ],

    motors: [],

  },

  {

    id: "produtos_vendidos",

    icon: "🛒",

    label: "Produtos Vendidos",

    tabs: [{ id: "produtos", label: "Produtos Vendidos", view: "productsHub" }],

    motors: [],

  },

  {

    id: "fiscal",

    icon: "📑",

    label: "Fiscal",

    tabs: [

      { id: "nfce", label: "NFCE", view: "nfceIntelligence" },

      { id: "conciliacao", label: "Conciliação", view: "fiscalReconciliation" },

      { id: "tributacao", label: "Tributação", view: "fiscalIntelligence" },

    ],

    motors: [],

  },

  {

    id: "administracao",

    icon: "⚙️",

    label: "Administração",

    tabs: [

      { id: "sistema", label: "Sistema", view: "administration" },

      { id: "diagnostico", label: "Diagnóstico Técnico", view: "financialOperationsCenter" },

    ],

    motors: ["operatorPerformance", "peopleIntelligence", "learning", "executiveCopilot", "recommendations"],

  },

];



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



const ADMIN_VIEWS = new Set(["financialOperationsCenter", "financialMonitoring", "financialOperations"]);



VIEW_TO_AREA.financialOperationsCenter = "administracao";

VIEW_TO_AREA.financialMonitoring = "administracao";

VIEW_TO_AREA.financialOperations = "administracao";



VIEW_TO_AREA.financialHub = "financeiro";

VIEW_TO_AREA.treasuryHub = "financeiro";

VIEW_TO_AREA.productsHub = "produtos_vendidos";



export function resolveAreaForView(view) {

  if (ADMIN_VIEWS.has(view)) return "administracao";

  return VIEW_TO_AREA[view] || "executivo";

}



export function getAreaById(areaId) {

  return NAV_AREAS.find((area) => area.id === areaId) || NAV_AREAS[0];

}



export function getDefaultViewForArea(areaId) {

  const area = getAreaById(areaId);

  return area.tabs[0]?.view || "executiveWorkspace";

}



export function countLegacyVisibleModules() {

  return NAV_AREAS.reduce((sum, area) => sum + area.tabs.length, 0);

}



export function countVisibleMacroAreas() {

  return NAV_AREAS.length;

}

