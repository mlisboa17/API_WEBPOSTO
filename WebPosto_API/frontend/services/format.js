const currencyFormatter = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

const numberFormatter = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

const dateFormatter = new Intl.DateTimeFormat("pt-BR", {
  timeZone: "UTC",
});

/** Converte ISO (yyyy-mm-dd) para exibição dd/mm/aaaa. */
export function isoDateToBr(value) {
  if (!value) return "";
  const raw = String(value).trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
    const [year, month, day] = raw.split("-");
    return `${day}/${month}/${year}`;
  }
  return raw;
}

/** Converte dd/mm/aaaa (ou yyyy-mm-dd) para ISO yyyy-mm-dd. */
export function parseBrDateToIso(value) {
  if (!value) return "";
  const raw = String(value).trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;

  const match = raw.match(/^(\d{2})[/.-](\d{2})[/.-](\d{4})$/);
  if (!match) return "";

  const [, day, month, year] = match;
  const dayNum = Number(day);
  const monthNum = Number(month);
  const yearNum = Number(year);
  if (monthNum < 1 || monthNum > 12 || dayNum < 1 || dayNum > 31) return "";

  const iso = `${year}-${month}-${day}`;
  const check = new Date(Date.UTC(yearNum, monthNum - 1, dayNum));
  if (
    check.getUTCFullYear() !== yearNum ||
    check.getUTCMonth() !== monthNum - 1 ||
    check.getUTCDate() !== dayNum
  ) {
    return "";
  }
  return iso;
}

export function formatPeriodBr(dataInicial, dataFinal) {
  const ini = isoDateToBr(dataInicial) || "—";
  const fin = isoDateToBr(dataFinal) || "—";
  return `${ini} → ${fin}`;
}

export function formatCurrency(value) {
  if (value === null || value === undefined || value === "") return "sem dados";
  const number = Number(String(value).replace(",", "."));
  if (Number.isNaN(number)) return formatMissing(value);
  return currencyFormatter.format(number);
}

export function formatDate(value) {
  if (!value) return "sem dados";
  const raw = String(value).slice(0, 10);
  const [year, month, day] = raw.split("-").map(Number);
  if (!year || !month || !day) return formatMissing(value);
  const date = new Date(Date.UTC(year, month - 1, day));
  return dateFormatter.format(date);
}

export function asText(value) {
  if (value === null || value === undefined || value === "") return "";
  return String(value);
}

export function formatMissing(value) {
  const text = asText(value).trim();
  return text || "—";
}

export function formatNumber(value) {
  if (value === null || value === undefined || value === "") return "sem dados";
  const number = Number(value);
  if (Number.isNaN(number)) return formatMissing(value);
  return numberFormatter.format(number);
}

export function toSearchText(value) {
  return asText(value).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}
