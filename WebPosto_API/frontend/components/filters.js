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
import { mountDateRangePicker } from "./DateRangePicker.js";
import { isoDateToBr, parseBrDateToIso } from "../services/formatters.js";

function bindBrDateInput(input) {
  if (!input) return;
  input.addEventListener("input", () => {
    const digits = input.value.replace(/\D/g, "").slice(0, 8);
    let formatted = digits;
    if (digits.length > 4) {
      formatted = `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4)}`;
    } else if (digits.length > 2) {
      formatted = `${digits.slice(0, 2)}/${digits.slice(2)}`;
    }
    if (input.value !== formatted) input.value = formatted;
  });
}

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

const PRIMARY_FIELD_KEYS = new Set(["periodo", "empresaCodigo"]);

function fieldHtml(visible, state, key, html) {
  return isVisibleField(visible, key) ? html : "";
}

export function renderFilters(container, state, onChange, onClear, options = {}) {
  const primaryHost = document.getElementById("primaryFiltersHost");
  const advancedHost = document.getElementById("advancedFiltersHost");
  
  const visible = options.visibleFields || [
    "periodo",
    "empresaCodigo",
    "centroCusto",
    "tipoDespesa",
    "origem",
    "texto",
    "valorMin",
    "valorMax",
  ];

  const allFieldsHtml = {
    periodo: fieldHtml(
      visible,
      state,
      "periodo",
      `
        <div class="field field--period">
          <div id="dateRangePickerHost"></div>
        </div>
      `
    ),
    empresaCodigo: fieldHtml(
      visible,
      state,
      "empresaCodigo",
      `
        <div class="field field--empresa">
          <label>Empresa</label>
          <div id="empresaMultiselectHost"></div>
        </div>
      `
    ),
    centroCusto: fieldHtml(
      visible,
      state,
      "centroCusto",
      `
        <div class="field">
          <label for="centroCusto">Centro de custo</label>
          <input id="centroCusto" type="text" value="${Array.isArray(state.centroCusto) ? state.centroCusto.join(",") : state.centroCusto || ""}" placeholder="ADMINISTRATIVO, OPERACIONAL" />
        </div>
      `
    ),
    tipoDespesa: fieldHtml(
      visible,
      state,
      "tipoDespesa",
      `
        <div class="field">
          <label for="tipoDespesa">Tipo despesa</label>
          <input id="tipoDespesa" type="text" value="${Array.isArray(state.tipoDespesa) ? state.tipoDespesa.join(",") : state.tipoDespesa || ""}" placeholder="operacional, financeiro" />
        </div>
      `
    ),
    expenseNature: fieldHtml(
      visible,
      state,
      "expenseNature",
      `
        <div class="field field--nature">
          <label>Natureza</label>
          <div id="natureMultiselectHost"></div>
        </div>
      `
    ),
    expenseManagementGroup: fieldHtml(
      visible,
      state,
      "expenseManagementGroup",
      `
        <div class="field field--mgmt-group">
          <label>Grupo Gerencial</label>
          <div id="mgmtGroupMultiselectHost"></div>
        </div>
      `
    ),
    expenseManagementClass: fieldHtml(
      visible,
      state,
      "expenseManagementClass",
      `
        <div class="field field--mgmt-class">
          <label>Classe Gerencial</label>
          <div id="mgmtClassMultiselectHost"></div>
        </div>
      `
    ),
    dreImpact: fieldHtml(
      visible,
      state,
      "dreImpact",
      `
        <div class="field">
          <label for="dreImpact">Impacta DRE</label>
          <select id="dreImpact">
            ${DRE_IMPACT_OPTIONS.map(
              (o) => `<option value="${o.value}" ${state.dreImpact === o.value ? "selected" : ""}>${o.label}</option>`
            ).join("")}
          </select>
        </div>
      `
    ),
    cashFlowImpact: fieldHtml(
      visible,
      state,
      "cashFlowImpact",
      `
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
    ),
    origem: fieldHtml(
      visible,
      state,
      "origem",
      `
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
    ),
    texto: fieldHtml(
      visible,
      state,
      "texto",
      `
        <div class="field">
          <label for="texto">Texto</label>
          <input id="texto" type="text" value="${state.texto || ""}" placeholder="Descrição, plano de conta..." />
        </div>
      `
    ),
    valorMin: fieldHtml(
      visible,
      state,
      "valorMin",
      `
        <div class="field">
          <label for="valorMin">Valor minimo</label>
          <input id="valorMin" type="number" step="0.01" value="${state.valorMin || ""}" />
        </div>
      `
    ),
    valorMax: fieldHtml(
      visible,
      state,
      "valorMax",
      `
        <div class="field">
          <label for="valorMax">Valor maximo</label>
          <input id="valorMax" type="number" step="0.01" value="${state.valorMax || ""}" />
        </div>
      `
    ),
  };

  const primaryFields = visible.filter((key) => PRIMARY_FIELD_KEYS.has(key));
  const advancedFields = visible.filter((key) => !PRIMARY_FIELD_KEYS.has(key));

  if (primaryHost) {
    primaryHost.innerHTML = `
      <div class="filters-bar filters-bar--premium" id="filtersBar">
        <div class="filters-primary">
          ${primaryFields.map((key) => allFieldsHtml[key] || "").join("")}
          <div class="filters-apply-wrap">
            <button type="button" id="filtersApplyBtn" class="btn-primary filters-apply-btn">Aplicar</button>
          </div>
        </div>
      </div>
    `;
  }

  if (advancedHost) {
    if (advancedFields.length > 0) {
      advancedHost.innerHTML = `
        <details class="filters-advanced">
          <summary>Filtros avançados</summary>
          <div class="filters-advanced__grid">
            ${advancedFields.map((key) => allFieldsHtml[key] || "").join("")}
          </div>
          <div class="filters-advanced__actions">
            <button id="clearFilters" type="button" class="btn-link filters-clear">Limpar filtros</button>
          </div>
        </details>
      `;
    } else {
      advancedHost.innerHTML = "";
    }
  }

  const root = primaryHost || container;
  const advRoot = advancedHost || container;

  let datePicker = null;

  const applyFilters = () => {
    const host = root.querySelector("#empresaMultiselectHost");
    const natureHost = advRoot.querySelector("#natureMultiselectHost");
    const mgmtGroupHost = advRoot.querySelector("#mgmtGroupMultiselectHost");
    const mgmtClassHost = advRoot.querySelector("#mgmtClassMultiselectHost");
    const dataInicialRaw = datePicker?.getRange()?.dataInicial || state.dataInicial;
    const dataFinalRaw = datePicker?.getRange()?.dataFinal || state.dataFinal;
    let dataInicial = dataInicialRaw;
    let dataFinal = dataFinalRaw;
    if (dataInicial && dataFinal && dataInicial > dataFinal) {
      dataFinal = dataInicial;
    }
    const nextState = {
      ...state,
      dataInicial,
      dataFinal,
      empresaCodigo: host ? readEmpresaCodigoFromMultiSelectLogos(host) : state.empresaCodigo,
      centroCusto: valueFromCommaInput(advRoot.querySelector("#centroCusto")?.value || ""),
      tipoDespesa: valueFromCommaInput(advRoot.querySelector("#tipoDespesa")?.value || ""),
      expenseNature: natureHost ? readExpenseNatureFromMultiSelectLogos(natureHost) : state.expenseNature,
      expenseManagementGroup: mgmtGroupHost
        ? readManagementGroupFromMultiSelect(mgmtGroupHost)
        : state.expenseManagementGroup,
      expenseManagementClass: mgmtClassHost
        ? readManagementClassFromMultiSelect(mgmtClassHost)
        : state.expenseManagementClass,
      dreImpact: advRoot.querySelector("#dreImpact")?.value || "",
      cashFlowImpact: advRoot.querySelector("#cashFlowImpact")?.value || "",
      origem: advRoot.querySelector("#origem")?.value || "",
      texto: advRoot.querySelector("#texto")?.value || "",
      valorMin: advRoot.querySelector("#valorMin")?.value || "",
      valorMax: advRoot.querySelector("#valorMax")?.value || "",
    };
    onChange(nextState);
  };

  const emitChange = debounce(applyFilters, 300);

  const pickerHost = root.querySelector("#dateRangePickerHost");
  if (pickerHost) {
    datePicker = mountDateRangePicker(pickerHost, state, (range) => {
      state.dataInicial = range.dataInicial;
      state.dataFinal = range.dataFinal;
      // We don't auto-apply for date picker anymore, wait for "Apply" button
    });
  }

  root.querySelector("#filtersApplyBtn")?.addEventListener("click", applyFilters);

  if (root.querySelector("#empresaMultiselectHost")) {
    const host = root.querySelector("#empresaMultiselectHost");
    mountMultiSelectLogos(host, state.empresaCodigo, () => {});
  }

  if (advRoot.querySelector("#natureMultiselectHost")) {
    const natureHost = advRoot.querySelector("#natureMultiselectHost");
    mountNatureMultiSelectLogos(natureHost, state.expenseNature, () => {});
  }

  if (advRoot.querySelector("#mgmtGroupMultiselectHost")) {
    const mgmtGroupHost = advRoot.querySelector("#mgmtGroupMultiselectHost");
    mountManagementGroupMultiSelect(mgmtGroupHost, state.expenseManagementGroup, () => {});
  }

  if (advRoot.querySelector("#mgmtClassMultiselectHost")) {
    const mgmtClassHost = advRoot.querySelector("#mgmtClassMultiselectHost");
    mountManagementClassMultiSelect(mgmtClassHost, state.expenseManagementClass, () => {});
  }

  advRoot.querySelectorAll("input, select").forEach((element) => {
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

  advRoot.querySelector("#clearFilters")?.addEventListener("click", () => onClear?.());
}

export function updateCompanyOptions(container, companies, selectedValue) {
  const primaryHost = document.getElementById("primaryFiltersHost");
  const host = (primaryHost || container).querySelector("#empresaMultiselectHost");
  if (!host) return;
  updateMultiSelectLogos(host, selectedValue);
}
