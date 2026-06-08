import { getFiliaisOptions } from "./filiais.js";

const EMPRESA_MS_STYLE_ID = "empresa-ms-critical-styles";

function ensureEmpresaMultiselectStyles() {
  if (document.getElementById(EMPRESA_MS_STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = EMPRESA_MS_STYLE_ID;
  style.textContent = `
    .empresa-ms { position: relative; width: 100%; }
    .empresa-ms__toggle {
      width: 100%; display: flex; align-items: center; justify-content: space-between;
      gap: 0.75rem; text-align: left; border: 1px solid #e7ddcf; background: #fff;
      border-radius: 8px; padding: 0.65rem 0.75rem; cursor: pointer; font-weight: 600;
    }
    .empresa-ms__summary { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .empresa-ms__panel {
      position: absolute; z-index: 30; top: calc(100% + 0.35rem); left: 0;
      width: min(100%, 520px); background: #fff; border: 1px solid #e7ddcf;
      border-radius: 12px; box-shadow: 0 10px 30px rgba(31, 26, 20, 0.06); padding: 0.75rem;
    }
    .empresa-ms__panel[hidden], .empresa-ms__chips[hidden] { display: none !important; }
    label.empresa-ms__row {
      display: grid !important; grid-template-columns: 1.1rem 1fr auto; align-items: center;
      gap: 0.65rem; padding: 0.45rem 0.35rem; border-bottom: 1px solid #f1ebe3;
      cursor: pointer; text-transform: none; letter-spacing: normal; box-shadow: none;
      font-size: 0.9rem; font-weight: 400; color: #1f1a14;
    }
    .empresa-ms__options { max-height: 260px; overflow-y: auto; border: 1px solid #e7ddcf; border-radius: 8px; }
    .empresa-ms__name { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .empresa-ms__code { color: #6b6257; font-size: 0.75rem; white-space: nowrap; }
  `;
  document.head.appendChild(style);
}

function setPanelOpen(panel, toggle, open) {
  if (!panel) return;
  if (open) {
    panel.classList.remove("hidden");
    panel.removeAttribute("hidden");
  } else {
    panel.classList.add("hidden");
    panel.setAttribute("hidden", "");
  }
  toggle?.setAttribute("aria-expanded", open ? "true" : "false");
}

function setChipsVisible(chipsNode, visible) {
  if (!chipsNode) return;
  if (visible) {
    chipsNode.classList.remove("hidden");
    chipsNode.removeAttribute("hidden");
  } else {
    chipsNode.classList.add("hidden");
    chipsNode.setAttribute("hidden", "");
  }
}

function foldText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function escapeHtml(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function withoutAll(values) {
  const list = Array.isArray(values) ? values : values ? [values] : [];
  return list
    .map((item) => String(item || "").trim())
    .filter((item) => item && item !== "__ALL__" && !/^(todos|all)$/i.test(item));
}

function readSelectedFromDom(root) {
  const allChecked = root.querySelector("#empresaCheckAll")?.checked;
  if (allChecked) return { mode: "all", values: [] };
  const checked = Array.from(root.querySelectorAll("#empresaCodigoOptions input[type=checkbox]:checked"))
    .map((el) => el.value)
    .filter(Boolean);
  return { mode: "selected", values: withoutAll(checked) };
}

function toEmpresaCodigoState(values) {
  if (!values.length) return "";
  if (values.length === 1) return values[0];
  return values;
}

/** Contrato A–F: rede (Todos) → ""; seleção explícita → código(s). */
export function buildEmpresaCodigoFromSelection(selection) {
  const mode = selection?.mode === "all" ? "all" : "selected";
  const values = withoutAll(selection?.values);
  if (mode === "all") return "";
  return toEmpresaCodigoState(values);
}

function allFiliaisCodes(options) {
  return options.map((opt) => String(opt.value));
}

function selectAllFiliais(root, options, onChange, emit = false) {
  const allCheckbox = root.querySelector("#empresaCheckAll");
  if (allCheckbox) allCheckbox.checked = false;
  syncUi(root, options, allFiliaisCodes(options), false);
  if (emit) emitState(root, onChange);
}

function updateToggleSummary(root, options, selectedValues, allMode) {
  const summary = root.querySelector("#empresaCodigoSummary");
  if (!summary) return;
  const total = options.length;
  if (allMode || selectedValues.length === 0) {
    summary.textContent = `Todos os postos (${total} filiais)`;
    return;
  }
  if (selectedValues.length === 1) {
    const opt = options.find((o) => String(o.value) === String(selectedValues[0]));
    summary.textContent = opt?.label || selectedValues[0];
    return;
  }
  summary.textContent = `${selectedValues.length} postos selecionados`;
}

function renderChips(root, options, selectedValues, allMode) {
  const chipsNode = root.querySelector("#empresaCodigoChips");
  if (!chipsNode) return;

  if (allMode || selectedValues.length === 0) {
    chipsNode.innerHTML = "";
    setChipsVisible(chipsNode, false);
    return;
  }

  setChipsVisible(chipsNode, true);
  const maxVisible = 4;
  const visible = selectedValues.slice(0, maxVisible);
  const extra = selectedValues.length - visible.length;

  const html = visible
    .map((code) => {
      const opt = options.find((o) => String(o.value) === String(code));
      const label = escapeHtml(opt?.label || code);
      return `<span class="empresa-ms__chip" data-code="${escapeHtml(code)}">${label}<button type="button" class="empresa-ms__chip-remove" data-code="${escapeHtml(code)}" aria-label="Remover">×</button></span>`;
    })
    .join("");

  chipsNode.innerHTML =
    html + (extra > 0 ? `<span class="empresa-ms__chip empresa-ms__chip--more">+${extra}</span>` : "");
}

function updateCounter(root, selectedValues, allMode, totalOptions) {
  const counter = root.closest(".field")?.querySelector("#empresaCodigoCounter");
  if (!counter) return;
  if (allMode || selectedValues.length === 0) {
    counter.textContent = `(Todos · ${totalOptions} filiais)`;
    return;
  }
  const n = selectedValues.length;
  counter.textContent = n === 1 ? "(1 selecionada)" : `(${n} selecionadas)`;
}

function renderOptions(root, options, selectedValues, searchText = "") {
  const listNode = root.querySelector("#empresaCodigoOptions");
  if (!listNode) return;
  const selectedSet = new Set(selectedValues.map(String));
  const q = foldText(searchText);
  const filtered = options.filter((opt) => {
    if (!q) return true;
    return foldText(opt.label).includes(q) || String(opt.value || "").includes(q);
  });

  if (filtered.length === 0) {
    listNode.innerHTML = '<p class="empresa-ms__empty">Nenhuma filial encontrada.</p>';
    return;
  }

  listNode.innerHTML = filtered
    .map(
      (opt) => `
      <label class="empresa-ms__row">
        <input type="checkbox" value="${escapeHtml(opt.value)}" ${selectedSet.has(String(opt.value)) ? "checked" : ""} />
        <span class="empresa-ms__name">${escapeHtml(opt.label)}</span>
        <span class="empresa-ms__code">${escapeHtml(opt.value)}</span>
      </label>
    `
    )
    .join("");
}

function syncUi(root, options, selectedValues, allMode) {
  renderOptions(root, options, selectedValues, root.querySelector("#empresaCodigoSearch")?.value || "");
  renderChips(root, options, selectedValues, allMode);
  updateCounter(root, selectedValues, allMode, options.length);
  updateToggleSummary(root, options, selectedValues, allMode);
}

function emitState(root, onChange) {
  onChange?.(buildEmpresaCodigoFromSelection(readSelectedFromDom(root)));
}

function setAllMode(root, options, onChange, emit = false) {
  const allCheckbox = root.querySelector("#empresaCheckAll");
  if (allCheckbox) allCheckbox.checked = true;
  root.querySelectorAll("#empresaCodigoOptions input[type=checkbox]").forEach((el) => {
    el.checked = false;
  });
  syncUi(root, options, [], true);
  if (emit) emitState(root, onChange);
}

export function mountEmpresaMultiselect(host, selectedValue, onChange) {
  ensureEmpresaMultiselectStyles();

  if (!host.querySelector("#empresaMultiselect")) {
    host.innerHTML = `
      <div id="empresaMultiselect" class="empresa-ms">
        <button type="button" id="empresaCodigoToggle" class="empresa-ms__toggle" aria-expanded="false">
          <span id="empresaCodigoSummary" class="empresa-ms__summary">Todos os postos</span>
          <span class="empresa-ms__chevron" aria-hidden="true">▾</span>
        </button>
        <div id="empresaCodigoChips" class="empresa-ms__chips hidden" hidden></div>
        <div id="empresaCodigoPanel" class="empresa-ms__panel hidden" hidden role="dialog" aria-label="Selecionar empresas">
          <input type="search" id="empresaCodigoSearch" class="empresa-ms__search" placeholder="Buscar por nome ou código..." />
          <div class="empresa-ms__actions">
            <button type="button" id="empresaSelectAll">Selecionar Tudo</button>
            <button type="button" id="empresaClearAll">Limpar Seleção</button>
            <button type="button" id="empresaApply" class="btn-primary">Aplicar</button>
          </div>
          <label class="empresa-ms__row empresa-ms__row--all">
            <input type="checkbox" id="empresaCheckAll" />
            <span class="empresa-ms__name">Todos os postos</span>
            <span class="empresa-ms__code">rede</span>
          </label>
          <div id="empresaCodigoOptions" class="empresa-ms__options"></div>
        </div>
      </div>
    `;

    const root = host.querySelector("#empresaMultiselect");
    const panel = host.querySelector("#empresaCodigoPanel");
    const toggle = host.querySelector("#empresaCodigoToggle");

    toggle?.addEventListener("click", (event) => {
      event.stopPropagation();
      const open = panel?.hasAttribute("hidden");
      setPanelOpen(panel, toggle, open);
    });

    document.addEventListener("click", (event) => {
      if (!host.contains(event.target)) {
        setPanelOpen(panel, toggle, false);
      }
    });

    host.querySelector("#empresaSelectAll")?.addEventListener("click", () => {
      selectAllFiliais(root, getFiliaisOptions(), onChange, false);
    });

    host.querySelector("#empresaClearAll")?.addEventListener("click", () => {
      setAllMode(root, getFiliaisOptions(), onChange, true);
    });

    host.querySelector("#empresaApply")?.addEventListener("click", () => {
      setPanelOpen(panel, toggle, false);
      emitState(root, onChange);
    });

    host.querySelector("#empresaCodigoSearch")?.addEventListener("input", (event) => {
      const selected = withoutAll(readSelectedFromDom(root).values);
      renderOptions(root, getFiliaisOptions(), selected, event.target.value);
    });

    host.querySelector("#empresaCheckAll")?.addEventListener("change", (event) => {
      if (event.target.checked) {
        setAllMode(root, getFiliaisOptions(), onChange, false);
      }
    });

    host.querySelector("#empresaCodigoOptions")?.addEventListener("change", (event) => {
      if (event.target.type !== "checkbox") return;
      root.querySelector("#empresaCheckAll").checked = false;
      const selected = withoutAll(readSelectedFromDom(root).values);
      syncUi(root, getFiliaisOptions(), selected, false);
    });

    host.querySelector("#empresaCodigoChips")?.addEventListener("click", (event) => {
      const btn = event.target.closest(".empresa-ms__chip-remove");
      if (!btn) return;
      const code = btn.dataset.code;
      const checkbox = root.querySelector(`#empresaCodigoOptions input[value="${code}"]`);
      if (checkbox) checkbox.checked = false;
      const selected = withoutAll(readSelectedFromDom(root).values);
      if (selected.length === 0) {
        setAllMode(root, getFiliaisOptions(), onChange, false);
      } else {
        syncUi(root, getFiliaisOptions(), selected, false);
      }
      emitState(root, onChange);
    });
  }

  updateEmpresaMultiselect(host, selectedValue);
}

export function updateEmpresaMultiselect(host, selectedValue) {
  const root = host.querySelector("#empresaMultiselect");
  if (!root) return;
  const options = getFiliaisOptions();
  const selected = withoutAll(selectedValue);
  const allMode = selected.length === 0;
  const allCheckbox = root.querySelector("#empresaCheckAll");
  if (allCheckbox) allCheckbox.checked = allMode;
  syncUi(root, options, selected, allMode);
}

export function readEmpresaCodigoFromMultiselect(host) {
  const root = host.querySelector("#empresaMultiselect");
  if (!root) return "";
  return buildEmpresaCodigoFromSelection(readSelectedFromDom(root));
}
