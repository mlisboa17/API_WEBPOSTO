function suffix(filters) {
  const empresa = String(filters?.empresaCodigo || "").trim();
  return empresa && !/^(todos|all|__all__)$/i.test(empresa) ? empresa.replace(/,/g, "_") : "all";
}

async function jsonOrNull(path) {
  try {
    const response = await fetch(path, { cache: "no-cache" });
    if (!response.ok) return null;
    return await response.json();
  } catch {
    return null;
  }
}

export async function fetchPresidentSnapshotBundle(filters) {
  const key = `${filters.dataInicial}_${filters.dataFinal}_${suffix(filters)}`;
  const [overview, expenses, sales, stock, scorecard, fuelGovernance, products] = await Promise.all([
    jsonOrNull(`/snapshots/financial/financial_overview_${key}.json`),
    jsonOrNull(`/snapshots/financial/financial_expenses_${key}.json`),
    jsonOrNull(`/snapshots/financial/financial_sales_${key}.json`),
    jsonOrNull(`/snapshots/financial/financial_stock_${key}.json`),
    jsonOrNull(`/snapshots/executive_scorecard/executive_scorecard_${key}.json`),
    jsonOrNull(`/snapshots/fuel_governance/fuel_gov_${key}.json`),
    jsonOrNull(`/snapshots/non_fuel_products/nonfuel_products_${key}.json`),
  ]);

  const hit = Boolean(overview || expenses || sales || stock || scorecard || fuelGovernance || products);
  return {
    hit,
    overview,
    expenses,
    sales,
    stock,
    scorecard,
    fuelGovernance,
    products,
  };
}
