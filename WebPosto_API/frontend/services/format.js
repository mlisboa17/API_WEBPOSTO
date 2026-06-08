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
