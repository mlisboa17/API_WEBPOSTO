import { getAreaById, NAV_AREAS } from "../config/navigation.js";

const MOTOR_LABELS = {
  benchmark: "Benchmark",
  corporateHub: "Corporate Hub",
  executiveDecision: "Decision Engine",
  executiveCopilot: "Executive Copilot",
  recommendations: "Recommendations",
  learning: "Learning",
  operatorPerformance: "Operator Performance",
  peopleIntelligence: "People Intelligence",
  peopleRoi: "People ROI",
  operationRoi: "Operation ROI",
  managementAction: "Management Action",
};

export function mountNavigationShell({ areaId, view, onAreaChange, onTabChange, onMotorChange }) {
  const sidebar = document.querySelector("#sidebarNav");
  const areaTabs = document.querySelector("#areaTabs");
  const motorStrip = document.querySelector("#motorStrip");
  if (!sidebar || !areaTabs) return;

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
    const hiddenMotors = area.motors.filter(
      (motorView) => !area.tabs.some((tab) => tab.view === motorView) && motorView !== "administration"
    );
    motorStrip.innerHTML =
      hiddenMotors.length === 0
        ? ""
        : `
          <div class="motor-strip">
            <span class="motor-strip__label">Motores da área</span>
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
        `;
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
