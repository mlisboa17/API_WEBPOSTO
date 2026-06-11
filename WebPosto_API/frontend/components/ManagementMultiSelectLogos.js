/**
 * MultiSelectLogos — filtros gerenciais F03.3 (grupo e classe).
 */

export const MANAGEMENT_GROUP_OPTIONS = [
  { value: "OPERACIONAL", label: "Operacional" },
  { value: "PESSOAL", label: "Pessoal" },
  { value: "TESOURARIA", label: "Tesouraria" },
  { value: "PERDAS", label: "Perdas" },
  { value: "ADMINISTRATIVO", label: "Administrativo" },
  { value: "FINANCEIRO", label: "Financeiro" },
];

export const MANAGEMENT_CLASS_OPTIONS = [
  { value: "SALARIO", label: "Salário" },
  { value: "QUINZENA", label: "Quinzena" },
  { value: "VALE", label: "Vale" },
  { value: "EXTRA", label: "Extra" },
  { value: "FOLGUISTA", label: "Folguista" },
  { value: "PERDA_CAIXA_FUNCIONARIO", label: "Perda Caixa Funcionário" },
  { value: "PERDA_CAIXA_EMPRESA", label: "Perda Caixa Empresa" },
  { value: "ENERGIA", label: "Energia" },
  { value: "AGUA", label: "Água" },
  { value: "TELEFONIA", label: "Telefonia" },
  { value: "BOBINA", label: "Bobina" },
  { value: "EMPRESTIMO", label: "Empréstimo" },
  { value: "ADIANTAMENTO", label: "Adiantamento" },
];

export const DRE_IMPACT_OPTIONS = [
  { value: "", label: "Todos" },
  { value: "SIM", label: "Impacta DRE" },
  { value: "NAO", label: "Não impacta DRE" },
  { value: "PARCIAL", label: "Impacto parcial" },
];

export const CASHFLOW_IMPACT_OPTIONS = [
  { value: "", label: "Todos" },
  { value: "SIM", label: "Impacta Caixa" },
  { value: "NAO", label: "Não impacta Caixa" },
  { value: "PARCIAL", label: "Impacto parcial" },
];

const STYLE_ID = "mgmt-ms-critical-styles";

function ensureStyles() {
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = `
    .mgmt-ms { position: relative; width: 100%; }
    .mgmt-ms__toggle {
      width: 100%; display: flex; align-items: center; justify-content: space-between;
      gap: 0.75rem; text-align: left; border: 1px solid #e7ddcf; background: #fff;
      border-radius: 8px; padding: 0.65rem 0.75rem; cursor: pointer; font-weight: 600;
    }
    .mgmt-ms__panel {
      position: absolute; z-index: 30; top: calc(100% + 0.35rem); left: 0;
      width: min(100%, 420px); background: #fff; border: 1px solid #e7ddcf;
      border-radius: 12px; box-shadow: 0 10px 30px rgba(31, 26, 20, 0.06); padding: 0.75rem;
    }
    .mgmt-ms__panel[hidden] { display: none !important; }
    label.mgmt-ms__row {
      display: grid !important; grid-template-columns: 1.1rem 1fr; align-items: center;
      gap: 0.65rem; padding: 0.45rem 0.35rem; border-bottom: 1px solid #f1ebe3;
      cursor: pointer; font-size: 0.9rem; font-weight: 400;
    }
    .mgmt-ms__options { max-height: 220px; overflow-y: auto; border: 1px solid #e7ddcf; border-radius: 8px; }
  `;
  document.head.appendChild(style);
}

function withoutAll(values) {
  return (Array.isArray(values) ? values : values ? [values] : [])
    .map((v) => String(v || "").trim())
    .filter((v) => v && v !== "__ALL__" && !/^(todos|all)$/i.test(v));
}

function normalizeValue(value) {
  if (Array.isArray(value)) return value;
  const text = String(value || "").trim();
  if (!text) return [];
  if (!text.includes(",")) return [text];
  return text.split(",").map((s) => s.trim()).filter(Boolean);
}

function summaryLabel(value, options, emptyLabel) {
  const selected = withoutAll(normalizeValue(value));
  if (!selected.length) return emptyLabel;
  if (selected.length === 1) {
    const opt = options.find((o) => o.value === selected[0]);
    return opt?.label || selected[0];
  }
  return `${selected.length} selecionados`;
}

function renderOptions(selected, options, dataAttr) {
  const set = new Set(withoutAll(normalizeValue(selected)));
  const allSelected = set.size === 0;
  const rows = options.map(
    (opt) => `
      <label class="mgmt-ms__row">
        <input type="checkbox" ${dataAttr} value="${opt.value}" ${set.has(opt.value) ? "checked" : ""} />
        <span>${opt.label}</span>
      </label>
    `
  ).join("");
  return `
    <label class="mgmt-ms__row">
      <input type="checkbox" class="mgmt-ms__all" ${allSelected ? "checked" : ""} />
      <span><strong>Todos</strong></span>
    </label>
    ${rows}
  `;
}

function mountMulti(host, selectedValue, options, dataAttr, emptyLabel, onChange, rootId) {
  ensureStyles();
  host.innerHTML = `
    <div class="mgmt-ms" id="${rootId}">
      <button type="button" class="mgmt-ms__toggle" aria-expanded="false">
        <span class="mgmt-ms__summary">${summaryLabel(selectedValue, options, emptyLabel)}</span>
        <span aria-hidden="true">▾</span>
      </button>
      <div class="mgmt-ms__panel" hidden>
        <div class="mgmt-ms__options">${renderOptions(selectedValue, options, dataAttr)}</div>
      </div>
    </div>
  `;

  const root = host.querySelector(`#${rootId}`);
  const toggle = root.querySelector(".mgmt-ms__toggle");
  const panel = root.querySelector(".mgmt-ms__panel");
  const summary = root.querySelector(".mgmt-ms__summary");

  const readSelection = () => {
    const allChecked = root.querySelector(".mgmt-ms__all")?.checked;
    if (allChecked) return "";
    const checked = Array.from(root.querySelectorAll(`input[type="checkbox"][${dataAttr}]:checked`))
      .map((el) => el.value)
      .filter(Boolean);
    if (!checked.length) return "";
    if (checked.length === 1) return checked[0];
    return checked;
  };

  const emit = () => {
    const value = readSelection();
    summary.textContent = summaryLabel(value, options, emptyLabel);
    onChange?.(value);
  };

  toggle.addEventListener("click", () => {
    const open = panel.hasAttribute("hidden");
    if (open) {
      panel.removeAttribute("hidden");
      toggle.setAttribute("aria-expanded", "true");
    } else {
      panel.setAttribute("hidden", "");
      toggle.setAttribute("aria-expanded", "false");
    }
  });

  root.querySelector(".mgmt-ms__all")?.addEventListener("change", (e) => {
    const checked = e.target.checked;
    root.querySelectorAll(`input[${dataAttr}]`).forEach((el) => {
      el.checked = false;
      el.disabled = checked;
    });
    emit();
  });

  root.querySelectorAll(`input[${dataAttr}]`).forEach((el) => {
    el.addEventListener("change", () => {
      const allBox = root.querySelector(".mgmt-ms__all");
      if (allBox) allBox.checked = false;
      emit();
    });
  });

  document.addEventListener("click", (e) => {
    if (!root.contains(e.target)) {
      panel.setAttribute("hidden", "");
      toggle.setAttribute("aria-expanded", "false");
    }
  });
}

export function mountManagementGroupMultiSelect(host, selectedValue, onChange) {
  mountMulti(host, selectedValue, MANAGEMENT_GROUP_OPTIONS, "data-mgmt-group", "Todos os grupos", onChange, "mgmtGroupMultiselect");
}

export function mountManagementClassMultiSelect(host, selectedValue, onChange) {
  mountMulti(host, selectedValue, MANAGEMENT_CLASS_OPTIONS, "data-mgmt-class", "Todas as classes", onChange, "mgmtClassMultiselect");
}

function readFromRoot(host, rootId, dataAttr) {
  const root = host.querySelector(`#${rootId}`);
  if (!root) return "";
  const allChecked = root.querySelector(".mgmt-ms__all")?.checked;
  if (allChecked) return "";
  const checked = Array.from(root.querySelectorAll(`input[type="checkbox"][${dataAttr}]:checked`))
    .map((el) => el.value)
    .filter(Boolean);
  if (!checked.length) return "";
  if (checked.length === 1) return checked[0];
  return checked;
}

export function readManagementGroupFromMultiSelect(host) {
  return readFromRoot(host, "mgmtGroupMultiselect", "data-mgmt-group");
}

export function readManagementClassFromMultiSelect(host) {
  return readFromRoot(host, "mgmtClassMultiselect", "data-mgmt-class");
}
