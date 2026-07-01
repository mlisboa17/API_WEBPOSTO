import { getAreaById, NAV_AREAS } from "../config/navigation.js";



const MOTOR_LABELS = {

  goalsCampaign: "Metas",

  benchmark: "Comparativo de rede",

  corporateHub: "Visão corporativa",

  accounts: "Contas a pagar",

  cashFlow: "Fluxo de caixa",

  cashOperations: "Extratos",

  financeCenter: "Conciliação",

  lmcIntelligence: "Controle LMC",

  fuels: "Bombas",

  fuelExecutive: "Visão executiva combustível",

  commercialExecution: "Plano de ações",

  operatorPerformance: "Desempenho operadores",

  peopleIntelligence: "Gestão de pessoas",

  learning: "Aprendizado (técnico)",

  executiveCopilot: "Assistente (técnico)",

  recommendations: "Recomendações (técnico)",

};



export function mountNavigationShell({ areaId, view, onAreaChange, onTabChange, onMotorChange }) {

  const sidebar = document.querySelector("#sidebarNav");

  const areaTabs = document.querySelector("#areaTabs");

  const motorStrip = document.querySelector("#motorStrip");

  if (!sidebar || !areaTabs) return;



  document.body.dataset.area = areaId || "executivo";
  document.body.classList.toggle("area-admin", areaId === "administracao");



  sidebar.innerHTML = NAV_AREAS.map(

    (area) => `

      <button

        type="button"

        class="sidebar-item${area.id === areaId ? " active" : ""}"

        data-area="${area.id}"

        title="${area.label}"

      >

        <span class="sidebar-item__icon">${area.icon}</span>

        <span class="sidebar-item__label">${area.label}</span>

      </button>

    `

  ).join("");



  const area = getAreaById(areaId);

  areaTabs.innerHTML = area.tabs

    .map(

      (tab) => `

        <button

          type="button"

          class="area-tab${tab.view === view ? " active" : ""}"

          data-view="${tab.view}"

          data-tab-id="${tab.id}"

        >${tab.label}</button>

      `

    )

    .join("");



  if (motorStrip) {

    const isAdmin = areaId === "administracao";

    const hiddenMotors = isAdmin

      ? area.motors.filter((motorView) => !area.tabs.some((tab) => tab.view === motorView))

      : [];



    motorStrip.className = isAdmin && hiddenMotors.length ? "motor-strip-host" : "motor-strip-host motor-strip--hidden";

    motorStrip.innerHTML =

      isAdmin && hiddenMotors.length

        ? `

          <div class="motor-strip motor-strip--admin">

            <span class="motor-strip__label">Módulos técnicos</span>

            ${hiddenMotors

              .map(

                (motorView) => `

                  <button type="button" class="motor-tab${motorView === view ? " active" : ""}" data-view="${motorView}">

                    ${MOTOR_LABELS[motorView] || motorView}

                  </button>

                `

              )

              .join("")}

          </div>

        `

        : "";

  }



  sidebar.querySelectorAll("[data-area]").forEach((button) => {

    button.addEventListener("click", () => onAreaChange(button.dataset.area));

  });

  areaTabs.querySelectorAll("[data-view]").forEach((button) => {

    button.addEventListener("click", () => onTabChange(button.dataset.view, button.dataset.tabId));

  });

  motorStrip?.querySelectorAll(".motor-tab[data-view]").forEach((button) => {

    button.addEventListener("click", () => onMotorChange(button.dataset.view));

  });

}

