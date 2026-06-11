import {
  mountMultiSelectLogos,
  readEmpresaCodigoFromMultiSelectLogos,
  updateMultiSelectLogos,
} from "./MultiSelectLogos.js";
import {
  mountNatureMultiSelectLogos,
  readExpenseNatureFromMultiSelectLogos,
} from "./NatureMultiSelectLogos.js";
import {
  CASHFLOW_IMPACT_OPTIONS,
  DRE_IMPACT_OPTIONS,
  mountManagementClassMultiSelect,
  mountManagementGroupMultiSelect,
  readManagementClassFromMultiSelect,
  readManagementGroupFromMultiSelect,
} from "./ManagementMultiSelectLogos.js";

function normalizeMultiValue(value) {
  if (Array.isArray(value)) return value.filter((item) => String(item || "").trim() !== "");
  const text = String(value || "").trim();
  if (!text) return [];
  if (!text.includes(",")) return [text];
  return text
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function valueFromCommaInput(value) {
  const normalized = normalizeMultiValue(value).filter(
    (item) => !/^(todos|all|__all__)$/i.test(String(item || "").trim())
  );
  if (normalized.length === 0) return "";
  if (normalized.length === 1) return normalized[0];
  return normalized;
}

function debounce(fn, delayMs) {
  let timeoutId;
  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delayMs);
  };
}

function isVisibleField(visible, key) {
  return visible.includes(key);
}

export function renderFilters(container, state, onChange, onClear, options = {}) {
  const visible = options.visibleFields || [
    "dataInicial",
    "dataFinal",
    "empresaCodigo",
    "centroCusto",
    "tipoDespesa",
    "origem",
    "texto",
    "valorMin",
    "valorMax",
  ];

  const fieldsHtml = [
    isVisibleField(visible, "dataInicial")
      ? `
        <div class="field">
          <label for="dataInicial">Data inicial</label>
          <input id="dataInicial" type="date" value="${state.dataInicial}" />
        </div>
      `
      : "",
    isVisibleField(visible, "dataFinal")
      ? `
        <div class="field">
          <label for="dataFinal">Data final</label>
          <input id="dataFinal" type="date" value="${state.dataFinal}" />
        </div>
      `
      : "",
    isVisibleField(visible, "empresaCodigo")
      ? `
        <div class="field field--empresa">
          <label>Empresa <span id="empresaCodigoCounter" class="small"></span></label>
          <div id="empresaMultiselectHost"></div>
        </div>
      `
      : "",
    isVisibleField(visible, "centroCusto")
      ? `
        <div class="field">
          <label for="centroCusto">Centro de custo</label>
          <input id="centroCusto" type="text" value="${Array.isArray(state.centroCusto) ? state.centroCusto.join(",") : (state.centroCusto || "")}" placeholder="ADMINISTRATIVO, OPERACIONAL" />
          <div class="small">Use vírgula para múltiplos valores</div>
        </div>
      `
      : "",
    isVisibleField(visible, "tipoDespesa")
      ? `
        <div class="field">
          <label for="tipoDespesa">Tipo despesa</label>
          <input id="tipoDespesa" type="text" value="${Array.isArray(state.tipoDespesa) ? state.tipoDespesa.join(",") : (state.tipoDespesa || "")}" placeholder="operacional, financeiro" />
          <div class="small">Use vírgula para múltiplos valores</div>
        </div>
      `
      : "",
    isVisibleField(visible, "expenseNature")
      ? `
        <div class="field field--nature">
          <label>Natureza</label>
          <div id="natureMultiselectHost"></div>
        </div>
      `
      : "",
    isVisibleField(visible, "expenseManagementGroup")
      ? `
        <div class="field field--mgmt-group">
          <label>Grupo Gerencial</label>
          <div id="mgmtGroupMultiselectHost"></div>
        </div>
      `
      : "",
    isVisibleField(visible, "expenseManagementClass")
      ? `
        <div class="field field--mgmt-class">
          <label>Classe Gerencial</label>
          <div id="mgmtClassMultiselectHost"></div>
        </div>
      `
      : "",
    isVisibleField(visible, "dreImpact")
      ? `
        <div class="field">
          <label for="dreImpact">Impacta DRE</label>
          <select id="dreImpact">
            ${DRE_IMPACT_OPTIONS.map(
              (o) => `<option value="${o.value}" ${state.dreImpact === o.value ? "selected" : ""}>${o.label}</option>`
            ).join("")}
          </select>
        </div>
      `
      : "",
    isVisibleField(visible, "cashFlowImpact")
      ? `
        <div class="field">
          <label for="cashFlowImpact">Impacta Caixa</label>
          <select id="cashFlowImpact">
            ${CASHFLOW_IMPACT_OPTIONS.map(
              (o) =>
                `<option value="${o.value}" ${state.cashFlowImpact === o.value ? "selected" : ""}>${o.label}</option>`
            ).join("")}
          </select>
        </div>
      `
      : "",
    isVisibleField(visible, "origem")
      ? `
        <div class="field">
          <label for="origem">Origem</label>
          <select id="origem">
            <option value="" ${!state.origem ? "selected" : ""}>Todos</option>
            <option value="financeiro" ${state.origem === "financeiro" ? "selected" : ""}>Financeiro</option>
            <option value="caixa" ${state.origem === "caixa" ? "selected" : ""}>Caixa</option>
            <option value="pdv" ${state.origem === "pdv" ? "selected" : ""}>PDV</option>
          </select>
        </div>
      `
      : "",
    isVisibleField(visible, "texto")
      ? `
        <div class="field">
          <label for="texto">Texto</label>
          <input id="texto" type="text" value="${state.texto || ""}" placeholder="Descrição, plano de conta..." />
        </div>
      `
      : "",
    isVisibleField(visible, "valorMin")
      ? `
        <div class="field">
          <label for="valorMin">Valor minimo</label>
          <input id="valorMin" type="number" step="0.01" value="${state.valorMin || ""}" />
        </div>
      `
      : "",
    isVisibleField(visible, "valorMax")
      ? `
        <div class="field">
          <label for="valorMax">Valor maximo</label>
          <input id="valorMax" type="number" step="0.01" value="${state.valorMax || ""}" />
        </div>
      `
      : "",
  ].join("");

  container.innerHTML = `
    ${fieldsHtml}
    <div class="field filters-actions">
      <label>Ações</label>
      <div class="filters-actions__buttons">
        ${options.onRefresh ? '<button id="applyFilters" type="button">Atualizar</button>' : ""}
        <button id="clearFilters" type="button">Limpar filtros</button>
      </div>
    </div>
  `;

  const emitChange = debounce(() => {
    const host = container.querySelector("#empresaMultiselectHost");
    const natureHost = container.querySelector("#natureMultiselectHost");
    const mgmtGroupHost = container.querySelector("#mgmtGroupMultiselectHost");
    const mgmtClassHost = container.querySelector("#mgmtClassMultiselectHost");
    const nextState = {
      ...state,
      dataInicial: container.querySelector("#dataInicial")?.value || state.dataInicial,
      dataFinal: container.querySelector("#dataFinal")?.value || state.dataFinal,
      empresaCodigo: host ? readEmpresaCodigoFromMultiSelectLogos(host) : state.empresaCodigo,
      centroCusto: valueFromCommaInput(container.querySelector("#centroCusto")?.value || ""),
      tipoDespesa: valueFromCommaInput(container.querySelector("#tipoDespesa")?.value || ""),
      expenseNature: natureHost ? readExpenseNatureFromMultiSelectLogos(natureHost) : state.expenseNature,
      expenseManagementGroup: mgmtGroupHost
        ? readManagementGroupFromMultiSelect(mgmtGroupHost)
        : state.expenseManagementGroup,
      expenseManagementClass: mgmtClassHost
        ? readManagementClassFromMultiSelect(mgmtClassHost)
        : state.expenseManagementClass,
      dreImpact: container.querySelector("#dreImpact")?.value || "",
      cashFlowImpact: container.querySelector("#cashFlowImpact")?.value || "",
      origem: container.querySelector("#origem")?.value || "",
      texto: container.querySelector("#texto")?.value || "",
      valorMin: container.querySelector("#valorMin")?.value || "",
      valorMax: container.querySelector("#valorMax")?.value || "",
    };
    onChange(nextState);
  }, 300);

  if (container.querySelector("#empresaMultiselectHost")) {
    const host = container.querySelector("#empresaMultiselectHost");
    mountMultiSelectLogos(host, state.empresaCodigo, () => emitChange());
  }

  if (container.querySelector("#natureMultiselectHost")) {
    const natureHost = container.querySelector("#natureMultiselectHost");
    mountNatureMultiSelectLogos(natureHost, state.expenseNature, () => emitChange());
  }

  if (container.querySelector("#mgmtGroupMultiselectHost")) {
    const mgmtGroupHost = container.querySelector("#mgmtGroupMultiselectHost");
    mountManagementGroupMultiSelect(mgmtGroupHost, state.expenseManagementGroup, () => emitChange());
  }

  if (container.querySelector("#mgmtClassMultiselectHost")) {
    const mgmtClassHost = container.querySelector("#mgmtClassMultiselectHost");
    mountManagementClassMultiSelect(mgmtClassHost, state.expenseManagementClass, () => emitChange());
  }

  container.querySelectorAll("input:not([type=search]), select").forEach((element) => {
    if (
      element.closest("#empresaMultiselect") ||
      element.closest("#natureMultiselect") ||
      element.closest("#mgmtGroupMultiselect") ||
      element.closest("#mgmtClassMultiselect")
    )
      return;
    element.addEventListener("change", emitChange);
    element.addEventListener("input", emitChange);
  });

  container.querySelector("#clearFilters")?.addEventListener("click", () => onClear?.());
  container.querySelector("#applyFilters")?.addEventListener("click", () => options.onRefresh?.());
}

export function updateCompanyOptions(container, companies, selectedValue) {
  const host = container.querySelector("#empresaMultiselectHost");
  if (!host) return;
  updateMultiSelectLogos(host, selectedValue);
}
