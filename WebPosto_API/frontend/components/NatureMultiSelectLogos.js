/**
 * MultiSelectLogos — filtro de Natureza Semântica (F03.2).
 * Mesmo padrão visual do multiselect de empresas.
 */

export const EXPENSE_NATURE_OPTIONS = [
  { value: "DESPESA_FINANCEIRA", label: "Despesa Financeira" },
  { value: "DESPESA_OPERACIONAL", label: "Despesa Operacional" },
  { value: "MOVIMENTACAO_CAIXA", label: "Movimentação Caixa" },
  { value: "ADIANTAMENTO", label: "Adiantamento" },
  { value: "AJUSTE_OPERACIONAL", label: "Ajuste Operacional" },
];

const STYLE_ID = "nature-ms-critical-styles";

function ensureStyles() {
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = `
    .nature-ms { position: relative; width: 100%; }
    .nature-ms__toggle {
      width: 100%; display: flex; align-items: center; justify-content: space-between;
      gap: 0.75rem; text-align: left; border: 1px solid #e7ddcf; background: #fff;
      border-radius: 8px; padding: 0.65rem 0.75rem; cursor: pointer; font-weight: 600;
    }
    .nature-ms__panel {
      position: absolute; z-index: 30; top: calc(100% + 0.35rem); left: 0;
      width: min(100%, 420px); background: #fff; border: 1px solid #e7ddcf;
      border-radius: 12px; box-shadow: 0 10px 30px rgba(31, 26, 20, 0.06); padding: 0.75rem;
    }
    .nature-ms__panel[hidden] { display: none !important; }
    label.nature-ms__row {
      display: grid !important; grid-template-columns: 1.1rem 1fr; align-items: center;
      gap: 0.65rem; padding: 0.45rem 0.35rem; border-bottom: 1px solid #f1ebe3;
      cursor: pointer; font-size: 0.9rem; font-weight: 400;
    }
    .nature-ms__options { max-height: 220px; overflow-y: auto; border: 1px solid #e7ddcf; border-radius: 8px; }
  `;
  document.head.appendChild(style);
}

function withoutAll(values) {
  return (Array.isArray(values) ? values : values ? [values] : [])
    .map((v) => String(v || "").trim())
    .filter((v) => v && v !== "__ALL__" && !/^(todos|all)$/i.test(v));
}

function readSelection(root) {
  const allChecked = root.querySelector("#natureCheckAll")?.checked;
  if (allChecked) return "";
  const checked = Array.from(root.querySelectorAll('input[type="checkbox"][data-nature]:checked'))
    .map((el) => el.value)
    .filter(Boolean);
  if (!checked.length) return "";
  if (checked.length === 1) return checked[0];
  return checked;
}

function summaryLabel(value) {
  const selected = withoutAll(normalizeValue(value));
  if (!selected.length) return "Todos";
  if (selected.length === 1) {
    const opt = EXPENSE_NATURE_OPTIONS.find((o) => o.value === selected[0]);
    return opt?.label || selected[0];
  }
  return `${selected.length} naturezas`;
}

function normalizeValue(value) {
  if (Array.isArray(value)) return value;
  const text = String(value || "").trim();
  if (!text) return [];
  if (!text.includes(",")) return [text];
  return text.split(",").map((s) => s.trim()).filter(Boolean);
}

function renderOptions(selected) {
  const set = new Set(withoutAll(normalizeValue(selected)));
  const allSelected = set.size === 0;
  const rows = EXPENSE_NATURE_OPTIONS.map(
    (opt) => `
      <label class="nature-ms__row">
        <input type="checkbox" data-nature value="${opt.value}" ${set.has(opt.value) ? "checked" : ""} />
        <span>${opt.label}</span>
      </label>
    `
  ).join("");
  return `
    <label class="nature-ms__row">
      <input type="checkbox" id="natureCheckAll" ${allSelected ? "checked" : ""} />
      <span><strong>Todos</strong></span>
    </label>
    ${rows}
  `;
}

export function mountNatureMultiSelectLogos(host, selectedValue, onChange) {
  ensureStyles();
  host.innerHTML = `
    <div class="nature-ms" id="natureMultiselect">
      <button type="button" class="nature-ms__toggle" aria-expanded="false">
        <span class="nature-ms__summary">${summaryLabel(selectedValue)}</span>
        <span aria-hidden="true">▾</span>
      </button>
      <div class="nature-ms__panel" hidden>
        <div class="nature-ms__options">${renderOptions(selectedValue)}</div>
      </div>
    </div>
  `;

  const root = host.querySelector("#natureMultiselect");
  const toggle = root.querySelector(".nature-ms__toggle");
  const panel = root.querySelector(".nature-ms__panel");
  const summary = root.querySelector(".nature-ms__summary");

  const emit = () => {
    const value = readSelection(root);
    summary.textContent = summaryLabel(value);
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

  root.querySelector("#natureCheckAll")?.addEventListener("change", (e) => {
    const checked = e.target.checked;
    root.querySelectorAll('input[data-nature]').forEach((el) => {
      el.checked = false;
      el.disabled = checked;
    });
    emit();
  });

  root.querySelectorAll('input[data-nature]').forEach((el) => {
    el.addEventListener("change", () => {
      const allBox = root.querySelector("#natureCheckAll");
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

export function readExpenseNatureFromMultiSelectLogos(host) {
  const root = host.querySelector("#natureMultiselect");
  if (!root) return "";
  return readSelection(root);
}

export function updateNatureMultiSelectLogos(host, selectedValue) {
  mountNatureMultiSelectLogos(host, selectedValue, null);
}
