export const COMPANIES = [
  { code: "all", name: "Comparar as 3 unidades" },
  { code: "11495", name: "POSTO VIP" },
  { code: "5555", name: "AP CASA CAIADA" },
  { code: "74014", name: "POSTO DOZE FILIAL II" },
] as const;
export const DEPARTMENTS = [{ code: "all", name: "Comparar departamentos" }, { code: "combustiveis", name: "Combustíveis" }, { code: "conveniencia", name: "Conveniência" }, { code: "lubrificantes", name: "Lubrificantes" }, { code: "compartilhado", name: "Corporativo/Compartilhado" }, { code: "nao_classificado", name: "Não classificado" }] as const;

export interface FlowPoint { period: string; inflow: number; outflow: number; balance: number; best: number | null; expected: number | null; worst: number | null }
export interface TreasuryRow { id: string; date: string; dueDate?: string; description: string; unit: string; category: string; value: number; risk: "critical" | "warning" | "normal" }
export interface UnitSummary { code: string; name: string; inflow: number; outflow: number; balance: number; available: boolean }
export interface ExpenseRow { id: string; accountCode: string; date: string; description: string; unit: string; value: number; category: string; department: "Combustíveis" | "Conveniência" | "Lubrificantes" | "Compartilhado/Quarentena"; confidence: number; status: "Comprovada" | "Provável" | "Quarentena"; source: string; employeeCode: string; employeeName: string; employeeRelated: boolean }
export interface ExpenseCategory { name: string; value: number; count: number }
export interface PaymentNatureSummary { code: string; label: string; calculated: number; presented: number; difference: number; items: number; open: number; autoMatched: number; humanConfirmed: number }
export interface CashDestination { destination: string; amount: number; destinationDate?: string; bankAccount?: string; bankMovementCode?: string; reference?: string; responsibleUser: string; note?: string; updatedAt?: string }
export interface CashDailySummary { date: string; company: string; companyCode: string; calculated: number; presented: number; difference: number; sangria: number; turns: number; consolidated: number; notConsolidated: number; consolidationUnknown: number; candidateDeposit: number; otherBankCredits: number; candidateCount: number; allocation?: CashDestination }
export interface CashClosingSummary { calculated: number; presented: number; difference: number; pending: number; turns: number; sangria: number; cashExpenses: number; employeeAdvances: number; paymentMethods: PaymentNatureSummary[]; dailyCash: CashDailySummary[]; unavailableCompanies: string[] }
export interface CardAdministratorSummary { company: string; date: string; code: string; name: string; method: string; gross: number; fee: number; expectedNet: number; records: number; pending: number; source: string }
export interface CardCatalogSummary { items: CardAdministratorSummary[]; premiaConfigured: { company: string; code: string; name: string; type: string }[]; unmappedRecords: number; unavailableCompanies: string[] }
export interface DepartmentOperationalEvidence { status: string; revenue: number; cost: number; grossMargin: number; coveragePct: number | null; itemsCollected: number; itemsAccepted: number; itemsQuarantined: number; paginationComplete: boolean; paginationPages: number }
export interface DepartmentDreLine { companyCode: string; companyName: string; department: string; revenue: number | null; cost: number | null; grossMargin: number | null; expenses: number | null; operatingResult: number | null; operatingMarginPct: number | null; status: string; missingEvidence: string[]; operationalEvidence: DepartmentOperationalEvidence | null }
export interface PeriodicAuditCycle { id: string; empresa_codigo: string; centro_custo: "PISTA" | "CONVENIENCIA"; periodicidade_dias: number; responsavel: string; data_corte: string; ativo: boolean; proximaAuditoria: string; statusAgenda: string }
export interface TreasuryData {
  selectedDepartment: string;
  updatedAt: string | null; source: "live" | "snapshot" | "unavailable"; sources: string[];
  kpis: { inflow: number; outflow: number; projected: number; accumulated: number; liquidity: number };
  flow: FlowPoint[]; composition: { name: string; value: number }[]; rows: TreasuryRow[]; units: UnitSummary[];
  expenses: ExpenseRow[]; expenseCategories: ExpenseCategory[];
  cashClosing: CashClosingSummary;
  cardCatalog: CardCatalogSummary;
  departmentalDre: DepartmentDreLine[];
  periodicAudits: PeriodicAuditCycle[];
}

type JsonRecord = Record<string, unknown>;
const API = process.env.WEBPOSTO_API_URL || "http://127.0.0.1:8000";
const number = (value: unknown) => Number(value || 0);
const nullableNumber = (value: unknown) => value === null || value === undefined || value === "" ? null : Number(value);
const object = (value: unknown): JsonRecord => value && typeof value === "object" && !Array.isArray(value) ? value as JsonRecord : {};
const array = (value: unknown): JsonRecord[] => Array.isArray(value) ? value as JsonRecord[] : [];
const companyName = (code: unknown) => COMPANIES.find(item => item.code === String(code))?.name || "Unidade não identificada";

async function fetchCashFlow(start: string, end: string, company?: string): Promise<JsonRecord> {
  const query = new URLSearchParams({ dataInicial: start, dataFinal: end });
  if (company && company !== "all") query.set("empresaCodigo", company);
  const response = await fetch(`${API}/api/v1/finance/cash-flow?${query}`, { cache: "no-store", signal: AbortSignal.timeout(30000) });
  if (!response.ok) throw new Error(`cash-flow ${response.status}`);
  const envelope = object(await response.json());
  return object(envelope.data || envelope);
}

async function fetchExpenses(start: string, end: string, company?: string): Promise<JsonRecord[]> {
  const query = new URLSearchParams({ dataInicial: start, dataFinal: end, page: "1", limit: "500" });
  if (company && company !== "all") query.set("empresaCodigo", company);
  const load = async (page: number, endpoint: "expenses" | "expenses-snapshot") => {
    const pageQuery = new URLSearchParams(query);
    pageQuery.set("page", String(page));
    const response = await fetch(`${API}/api/v1/finance/center/${endpoint}?${pageQuery}`, { cache: "no-store", signal: AbortSignal.timeout(endpoint === "expenses" ? 10000 : 15000) });
    if (!response.ok) throw new Error(`expenses ${response.status}`);
    const envelope = object(await response.json());
    if (envelope.success === false) throw new Error("expenses unavailable");
    return object(envelope.data);
  };
  const collect = async (endpoint: "expenses" | "expenses-snapshot") => {
    const first = await load(1, endpoint);
    const pages = Math.ceil(number(first.total) / 500);
    if (pages <= 1) return array(first.data);
    const remaining = await Promise.all(Array.from({ length: pages - 1 }, (_, index) => load(index + 2, endpoint)));
    return [...array(first.data), ...remaining.flatMap(page => array(page.data))];
  };
  try { return await collect("expenses"); }
  catch { return collect("expenses-snapshot"); }
}

async function fetchClassifications(): Promise<JsonRecord> {
  const response = await fetch(`${API}/api/v1/finance/director-reconciliation/expense-classifications`, { cache: "no-store", signal: AbortSignal.timeout(10000) });
  if (!response.ok) return {};
  return object(object(await response.json()).data);
}

async function fetchCashReconciliation(start: string, end: string, company: string): Promise<JsonRecord> {
  const query = new URLSearchParams({ dataInicial: start, dataFinal: end, empresaCodigo: company });
  const response = await fetch(`${API}/api/v1/cash-reconciliation/summary?${query}`, { cache: "no-store", signal: AbortSignal.timeout(60000) });
  if (!response.ok) throw new Error(`cash-reconciliation ${response.status}`);
  return object(object(await response.json()).data);
}

async function fetchCashDestinations(start: string, end: string, company: string): Promise<JsonRecord[]> {
  const query = new URLSearchParams({ dataInicial: start, dataFinal: end, empresaCodigo: company });
  const response = await fetch(`${API}/api/v1/cash-reconciliation/cash-destinations?${query}`, { cache: "no-store", signal: AbortSignal.timeout(10000) });
  if (!response.ok) return [];
  return array(object(await response.json()).data);
}

function emptyCashClosing(): CashClosingSummary { return { calculated: 0, presented: 0, difference: 0, pending: 0, turns: 0, sangria: 0, cashExpenses: 0, employeeAdvances: 0, paymentMethods: [], dailyCash: [], unavailableCompanies: [] }; }
function emptyCardCatalog(): CardCatalogSummary { return { items: [], premiaConfigured: [], unmappedRecords: 0, unavailableCompanies: [] }; }

function aggregateCashClosing(results: PromiseSettledResult<JsonRecord>[], allocationResults: PromiseSettledResult<JsonRecord[]>[], companies: readonly { code: string; name: string }[]): CashClosingSummary {
  const output = emptyCashClosing();
  const methods = new Map<string, PaymentNatureSummary>();
  results.forEach((result, index) => {
    if (result.status === "rejected") { output.unavailableCompanies.push(companies[index].name); return; }
    const summary = object(result.value.summary);
    const meta = object(result.value.meta);
    output.calculated += number(summary.valorApurado);
    output.presented += number(summary.valorApresentado);
    output.difference += number(summary.valorApresentado) - number(summary.valorApurado);
    output.pending += number(summary.valorPendente);
    output.turns += number(meta.caixaTurnos);
    output.sangria += number(meta.sangriaTotal);
    for (const raw of array(result.value.items)) {
      if (String(raw.paymentNature) !== "DINHEIRO") continue;
      const evidence = object(array(raw.evidences)[0]);
      const date = String(evidence.effectiveDate || raw.periodoInicio || "");
      const calculated = number(raw.valorApurado); const presented = number(raw.valorApresentado);
      const consolidation = String(raw.consolidationStatus || "UNKNOWN");
      output.dailyCash.push({ date, company: companies[index].name, companyCode: companies[index].code, calculated, presented, difference: presented - calculated, sangria: number(raw.sangria), turns: 1, consolidated: consolidation === "CONSOLIDATED" ? 1 : 0, notConsolidated: consolidation === "NOT_CONSOLIDATED" ? 1 : 0, consolidationUnknown: consolidation === "UNKNOWN" ? 1 : 0, candidateDeposit: 0, otherBankCredits: 0, candidateCount: 0 });
    }
    for (const credit of array(meta.bankCredits)) {
      const date = String(credit.dataMovimento || "");
      let daily = output.dailyCash.find(item => item.date === date && item.company === companies[index].name);
      if (!daily) { daily = { date, company: companies[index].name, companyCode: companies[index].code, calculated: 0, presented: 0, difference: 0, sangria: 0, turns: 0, consolidated: 0, notConsolidated: 0, consolidationUnknown: 0, candidateDeposit: 0, otherBankCredits: 0, candidateCount: 0 }; output.dailyCash.push(daily); }
      if (credit.candidatoDepositoEspecie === true) { daily.candidateDeposit += number(credit.valor); daily.candidateCount += 1; }
      else daily.otherBankCredits += number(credit.valor);
    }
    for (const raw of array(summary.natureCards)) {
      const code = String(raw.paymentNature || "OUTRO");
      if (code === "DESPESA") output.cashExpenses += number(raw.valorApurado);
      if (code === "VALE_FUNCIONARIO" || code === "EMPRESTIMO") output.employeeAdvances += number(raw.valorApurado);
      if (["DESPESA", "VALE_FUNCIONARIO", "EMPRESTIMO"].includes(code)) continue;
      const label = code === "TRANSFERENCIA_CREDITO" ? "PIX/Transferência bancária" : code === "CARTAO" ? "Cartões" : String(raw.label || code);
      const current = methods.get(code) || { code, label, calculated: 0, presented: 0, difference: 0, items: 0, open: 0, autoMatched: 0, humanConfirmed: 0 };
      current.calculated += number(raw.valorApurado); current.presented += number(raw.valorApresentado);
      current.difference += number(raw.diferenca); current.items += number(raw.itemsCount); current.open += number(raw.openCount); current.autoMatched += number(raw.autoMatchedCount); current.humanConfirmed += number(raw.humanConfirmedCount);
      methods.set(code, current);
    }
  });
  allocationResults.forEach((result, index) => { if (result.status === "rejected") return; for (const allocation of result.value) { const daily = output.dailyCash.find(item => item.companyCode === companies[index].code && item.date === String(allocation.movementDate || "")); if (daily) daily.allocation = { destination: String(allocation.destination || ""), amount: number(allocation.amount), destinationDate: String(allocation.destinationDate || "") || undefined, bankAccount: String(allocation.bankAccount || "") || undefined, bankMovementCode: String(allocation.bankMovementCode || "") || undefined, reference: String(allocation.reference || "") || undefined, responsibleUser: String(allocation.responsibleUser || ""), note: String(allocation.note || "") || undefined, updatedAt: String(allocation.updatedAt || "") || undefined }; } });
  output.paymentMethods = [...methods.values()].sort((a, b) => b.calculated - a.calculated);
  return output;
}

async function fetchPaymentMethodCatalog(start: string, end: string, company: string): Promise<JsonRecord> {
  const query = new URLSearchParams({ dataInicial: start, dataFinal: end, empresaCodigo: company });
  const response = await fetch(`${API}/api/v1/cash-reconciliation/payment-methods?${query}`, { cache: "no-store", signal: AbortSignal.timeout(120000) });
  if (!response.ok) throw new Error(`payment-methods ${response.status}`);
  return object(object(await response.json()).data);
}

async function fetchDepartmentalDre(start: string, end: string, company?: string): Promise<JsonRecord[]> {
  const query = new URLSearchParams({ dataInicial: start, dataFinal: end });
  if (company && company !== "all") query.set("empresaCodigo", company);
  const response = await fetch(`${API}/api/v1/finance/director-reconciliation/dre-complete?${query}`, { cache: "no-store", signal: AbortSignal.timeout(180000) });
  if (!response.ok) return [];
  return array(object(object(await response.json()).data).lines);
}

async function fetchPeriodicAudits(): Promise<PeriodicAuditCycle[]> {
  const response = await fetch(`${API}/api/v1/auditorias-periodicas/ciclos`, { cache: "no-store", signal: AbortSignal.timeout(10000) });
  if (!response.ok) return [];
  return array(object(await response.json()).data) as unknown as PeriodicAuditCycle[];
}

function aggregateCardCatalog(results: PromiseSettledResult<JsonRecord>[], companies: readonly { code: string; name: string }[]): CardCatalogSummary {
  const output = emptyCardCatalog();
  results.forEach((result, index) => {
    const company = companies[index];
    if (result.status === "rejected") { output.unavailableCompanies.push(company.name); return; }
    const quality = object(result.value.qualidade);
    const source = String(quality.fonteMovimentos || "SEM FONTE");
    output.unmappedRecords += number(quality.cartoesNaoIdentificados);
    for (const item of array(result.value.cartoes)) output.items.push({
      company: company.name, date: String(item.dataMovimento || ""), code: String(item.administradoraCodigo || ""), name: String(item.administradora || "Não identificada"), method: String(item.modalidade || "NAO_IDENTIFICADO"),
      gross: number(item.valorBruto), fee: number(item.taxaEstimada), expectedNet: number(item.valorLiquidoEsperado), records: number(item.registros), pending: number(item.pendentes), source,
    });
    for (const admin of array(result.value.administradoras)) {
      const name = String(admin.descricao || "");
      if (/PREMM?IA/i.test(name)) output.premiaConfigured.push({ company: company.name, code: String(admin.administradoraCodigo || ""), name, type: String(admin.tipo || "") });
    }
  });
  output.items.sort((a, b) => b.gross - a.gross);
  return output;
}

function classifyDepartment(description: string, costCenter: string): Pick<ExpenseRow, "department" | "status"> {
  const normalize = (value: string) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase();
  const text = normalize(description);
  const center = normalize(costCenter);
  const match = (pattern: RegExp, department: ExpenseRow["department"]) => pattern.test(center) ? { department, status: "Comprovada" as const } : pattern.test(text) ? { department, status: "Provável" as const } : null;
  const fuel = match(/GASOLINA|DIESEL|ETANOL|COMBUSTIV|PISTA|VIBRA ENERGIA|IPIRANGA|RAIZEN|PETROBRAS/, "Combustíveis");
  if (fuel) return fuel;
  const lubricant = match(/LUBRAX|LUBRIFIC|OLEO MOTOR|ADITIVO|FLUIDO|FILTRO|PALHETA|ARLA/, "Lubrificantes");
  if (lubricant) return lubricant;
  const convenience = match(/BEBIDA|REFRIGERANTE|CERVEJA|ENERGETICO|SALGADO|DOCE|CHOCOLATE|SORVETE|TABAC|RESTAURANTE|FOOD|GELO|CONVENIENCIA/, "Conveniência");
  if (convenience) return convenience;
  return { department: "Compartilhado/Quarentena", status: "Quarentena" };
}

export async function getTreasuryData(start: string, end: string, company = "all", department = "all"): Promise<TreasuryData> {
  try {
    const licensed = COMPANIES.filter(item => item.code !== "all");
    const reconciliationCompanies = company === "all" ? COMPANIES.filter(item => item.code !== "all") : COMPANIES.filter(item => item.code === company);
    const [data, unitResults, expenseRecords, classifications, reconciliationResults, allocationResults, cardCatalogResults, dreRecords, periodicAudits] = await Promise.all([
      fetchCashFlow(start, end, company).catch((): JsonRecord => ({})),
      company === "all" ? Promise.allSettled(licensed.map(item => fetchCashFlow(start, end, item.code))) : Promise.resolve([]),
      fetchExpenses(start, end, company).catch(() => []),
      fetchClassifications().catch((): JsonRecord => ({})),
      Promise.allSettled(reconciliationCompanies.map(item => fetchCashReconciliation(start, end, item.code))),
      Promise.allSettled(reconciliationCompanies.map(item => fetchCashDestinations(start, end, item.code))),
      Promise.allSettled(reconciliationCompanies.map(item => fetchPaymentMethodCatalog(start, end, item.code))),
      fetchDepartmentalDre(start, end, company).catch(() => []),
      fetchPeriodicAudits().catch(() => []),
    ]);
    const cards = object(data.cards);
    const daily = array(data.daily);
    const inflow = number(cards.entradasPrevistas);
    const outflow = number(cards.saidasPrevistas);
    const flow: FlowPoint[] = daily.map(item => ({
      period: String(item.periodo || ""),
      inflow: number(item.entradasPrevistas), outflow: number(item.saidasPrevistas),
      balance: number(item.saldoProjetado),
      best: nullableNumber(item.melhorCenario), expected: nullableNumber(item.cenarioEsperado), worst: nullableNumber(item.piorCenario),
    }));
    const rows: TreasuryRow[] = array(data.overdueEvents).map((item, index) => ({
      id: String(item.codigo || index), date: String(item.dataMovimento || item.data || ""), dueDate: String(item.vencimento || ""),
      description: String(item.descricao || "Movimentação financeira"), unit: companyName(item.empresaCodigo),
      category: String(item.tipo || "Financeiro").replaceAll("_", " "), value: number(item.valor),
      risk: item.aging === "vencido" ? "critical" : item.aging === "hoje" ? "warning" : "normal",
    }));
    const units: UnitSummary[] = company === "all" ? unitResults.map((result, index) => {
      const unit = licensed[index];
      if (result.status === "rejected") return { code: unit.code, name: unit.name, inflow: 0, outflow: 0, balance: 0, available: false };
      const unitCards = object(result.value.cards);
      return { code: unit.code, name: unit.name, inflow: number(unitCards.entradasPrevistas), outflow: number(unitCards.saidasPrevistas), balance: number(unitCards.saldoProjetado), available: true };
    }) : [];
    const reviews = new Map(array(classifications.reviews).map(item => [String(item.fact_id), item]));
    const rules = new Map(array(classifications.rules).filter(item => item.active !== false).map(item => [String(item.management_account_code), item]));
    const expenses: ExpenseRow[] = expenseRecords.map((item, index) => {
      const description = String(item.planoConta || "Despesa sem descrição");
      const confidence = number(item.confidenceScoreV3);
      const department = classifyDepartment(description, String(item.centroCusto || ""));
      const category = String(item.categoriaLogosV3 || item.categoriaLogos || "OUTROS");
      const id = String(item.codigo || `${item.empresaCodigo}-${item.data}-${item.planoContaCodigo}-${index}`);
      const accountCode = String(item.planoContaCodigo || "");
      const decision = reviews.get(id) || rules.get(accountCode);
      const employeeCode = String(item.funcionarioCodigo || "");
      const employeeName = String(decision?.recipient_name || item.employeeName || "").trim();
      const employeeRelated = category === "PESSOAL" || /FUNCION|VALE|ADIANTAMENTO|SALÁRIO|SALARIO|EMPRÉSTIMO|EMPRESTIMO/i.test(description);
      const decidedDepartment = String(decision?.department || "");
      const departmentLabel = decidedDepartment === "combustiveis" ? "Combustíveis" : decidedDepartment === "conveniencia" ? "Conveniência" : decidedDepartment === "lubrificantes" ? "Lubrificantes" : department.department;
      return {
        id, accountCode, date: String(item.data || start), description, unit: companyName(item.empresaCodigo), value: number(item.valor),
        category: String(decision?.category || category), department: departmentLabel, confidence: decision ? 1 : confidence,
        source: decision ? (reviews.has(id) ? "REVISÃO DIRETORIA" : "REGRA PERMANENTE") : String(item.classificationSource || "SEM REGRA"),
        employeeCode, employeeName, employeeRelated,
        status: decision ? "Comprovada" : department.status,
      };
    });
    const categoryMap = new Map<string, ExpenseCategory>();
    for (const expense of expenses) {
      const current = categoryMap.get(expense.category) || { name: expense.category, value: 0, count: 0 };
      current.value += expense.value; current.count += 1; categoryMap.set(expense.category, current);
    }
    const departmentMap: Record<string, string> = { combustiveis: "Combustíveis", conveniencia: "Conveniência", lubrificantes: "Lubrificantes", compartilhado: "Compartilhado/Quarentena", nao_classificado: "Compartilhado/Quarentena" };
    const filteredExpenses = department === "all" ? expenses : expenses.filter(item => item.department === departmentMap[department]);
    const departmentalDre: DepartmentDreLine[] = dreRecords.map(row => {
      const evidence = object(row.operationalEvidence);
      const pagination = object(evidence.pagination);
      return { companyCode: String(row.companyCode || ""), companyName: String(row.companyName || companyName(row.companyCode)), department: String(row.department || "nao_classificado"), revenue: nullableNumber(row.revenue), cost: nullableNumber(row.cost), grossMargin: nullableNumber(row.grossMargin), expenses: nullableNumber(row.expenses), operatingResult: nullableNumber(row.operatingResult), operatingMarginPct: nullableNumber(row.operatingMarginPct), status: row.status === "LIBERADO" ? "LIBERADO" : "BLOQUEADO", missingEvidence: Array.isArray(row.missingEvidence) ? row.missingEvidence.map(String) : [], operationalEvidence: Object.keys(evidence).length ? { status: String(evidence.status || "INCOMPLETO"), revenue: number(evidence.revenue), cost: number(evidence.cost), grossMargin: number(evidence.grossMargin), coveragePct: nullableNumber(evidence.coveragePct), itemsCollected: number(evidence.itemsCollected), itemsAccepted: number(evidence.itemsAccepted), itemsQuarantined: number(evidence.itemsQuarantined), paginationComplete: pagination.complete === true, paginationPages: number(pagination.pages) } : null };
    }).filter(row => department === "all" || row.department === department);
    return {
      selectedDepartment: department,
      updatedAt: String(data.referenceDate || "") || null, source: Object.keys(data).length ? "live" : "unavailable",
      sources: Array.isArray(data.sources) ? data.sources.map(String) : [],
      kpis: { inflow, outflow, projected: number(cards.saldoProjetado), accumulated: number(cards.saldoAcumulado), liquidity: outflow ? inflow / outflow : 0 },
      flow, composition: [{ name: "Créditos bancários identificados", value: inflow }, { name: "Saídas previstas", value: outflow }], rows, units,
      expenses: filteredExpenses, expenseCategories: [...categoryMap.values()].sort((a, b) => b.value - a.value),
      cashClosing: aggregateCashClosing(reconciliationResults, allocationResults, reconciliationCompanies),
      cardCatalog: aggregateCardCatalog(cardCatalogResults, reconciliationCompanies),
      departmentalDre,
      periodicAudits,
    };
  } catch {
    return { selectedDepartment: department, updatedAt: null, source: "unavailable", sources: [], kpis: { inflow: 0, outflow: 0, projected: 0, accumulated: 0, liquidity: 0 }, flow: [], composition: [], rows: [], units: [], expenses: [], expenseCategories: [], cashClosing: emptyCashClosing(), cardCatalog: emptyCardCatalog(), departmentalDre: [], periodicAudits: [] };
  }
}
