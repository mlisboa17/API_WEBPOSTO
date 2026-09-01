import { formatCurrency } from "./format.js";

/** Converte "R$ 7,501" (formato US no título do detector) para R$ 7.501,00. */
function parseLooseMoneyToken(token) {
  const raw = String(token || "").trim();
  if (!raw) return null;
  if (/^\d{1,3}(,\d{3})+(\.\d+)?$/.test(raw)) {
    return Number(raw.replace(/,/g, ""));
  }
  if (/^\d{1,3}(\.\d{3})*(,\d+)?$/.test(raw)) {
    const normalized = raw.replace(/\./g, "").replace(",", ".");
    const n = Number(normalized);
    return Number.isNaN(n) ? null : n;
  }
  const n = Number(raw.replace(",", "."));
  return Number.isNaN(n) ? null : n;
}

/** Normaliza valores monetários embutidos em títulos vindos do backend. */
export function formatMoneyInText(text) {
  if (!text) return text;
  return String(text).replace(/R\$\s*([\d.,]+)/g, (match, amount) => {
    const value = parseLooseMoneyToken(amount);
    return value == null ? match : formatCurrency(value);
  });
}

export function splitDecisionAlert(title) {
  const formatted = formatMoneyInText(title || "");
  const moneyMatch = formatted.match(/^(R\$\s*[\d.,]+)\s*(.*)$/);
  if (moneyMatch) {
    return {
      amount: moneyMatch[1].trim(),
      context: moneyMatch[2].trim() || "Valor sob atenção",
    };
  }
  return { amount: null, context: formatted };
}
