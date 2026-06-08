import { formatCurrency } from "../services/format.js";

import { downloadCsv, openPdfPreview } from "../services/export.js";



function fmtMoney(value) {

  if (value === null || value === undefined || value === "") return "—";

  return formatCurrency(value);

}



function bucketRows(buckets, keys, prefix = "") {

  const rows = [];

  keys.forEach((key) => {

    const bucket = buckets?.[key];

    if (!bucket) return;

    rows.push({

      secao: prefix ? `${prefix} · ${key}` : key,

      quantidade: bucket.count ?? 0,

      valor: bucket.valor ?? "0",

    });

  });

  return rows;

}



const EXPORT_COLUMNS = [

  { key: "secao", label: "Seção" },

  { key: "quantidade", label: "Quantidade", type: "number" },

  { key: "valor", label: "Valor", type: "currency", formatter: fmtMoney },

];



const PAYABLE_AGING_KEYS = ["vencido", "emAberto", "aVencer", "pago"];

const RECEIVABLE_AGING_KEYS = ["vencido", "pendente", "aVencer", "recebido"];

const LOGOS_CATEGORIES = [

  "OPERACIONAL",

  "PESSOAL",

  "ADMINISTRATIVA",

  "COMERCIAL",

  "COMPRAS",

  "FINANCEIRO",

  "OUTROS",

];



/** Exporta todos os blocos visíveis (paridade tabela ↔ CSV ↔ PDF). */

export function buildFinanceCenterExportRows(data) {

  const summary = data?.summary || {};

  const expenses = data?.expenses || {};

  const payables = data?.payables || {};

  const receivables = data?.receivables || {};

  const bank = data?.bank || {};

  const cash = data?.cash || {};



  const despesas = summary.despesasGerenciais || expenses.resumo || {};

  const cp = summary.contasPagar || payables.buckets || {};

  const cr = summary.contasReceber || receivables.buckets || {};

  const bankResumo = summary.movimentoBancario || bank.resumo || {};

  const caixa = summary.caixa || {};



  const rows = [

    {

      secao: "Despesas Gerenciais",

      quantidade: despesas.totalRegistros ?? 0,

      valor: despesas.totalValor ?? "0",

    },

    ...bucketRows(cp, PAYABLE_AGING_KEYS, "Contas a Pagar"),

    ...bucketRows(cr, RECEIVABLE_AGING_KEYS, "Contas a Receber"),

    {

      secao: "Tesouraria · Créditos",

      quantidade: bankResumo.creditos?.count ?? 0,

      valor: bankResumo.creditos?.valor ?? "0",

    },

    {

      secao: "Tesouraria · Débitos",

      quantidade: bankResumo.debitos?.count ?? 0,

      valor: bankResumo.debitos?.valor ?? "0",

    },

    {

      secao: "Tesouraria · Transferências",

      quantidade: bankResumo.transferencias?.count ?? 0,

      valor: bankResumo.transferencias?.valor ?? "0",

    },

    {

      secao: "Tesouraria · Tarifas",

      quantidade: bankResumo.tarifas?.count ?? 0,

      valor: bankResumo.tarifas?.valor ?? "0",

    },

    {

      secao: "Movimento Bancário · Líquido",

      quantidade: bankResumo.totalRegistros ?? bank.paginacaoCompleta ?? 0,

      valor: bankResumo.saldoMovimentado?.liquido ?? "0",

    },

  ];



  const porCategoria = despesas.porCategoriaLogos || {};

  LOGOS_CATEGORIES.forEach((cat) => {
    rows.push({
      secao: `LOGOS · ${cat}`,
      quantidade: 0,
      valor: porCategoria[cat] ?? "0",
    });
  });

  Object.entries(porCategoria).forEach(([cat, val]) => {

    if (LOGOS_CATEGORIES.includes(cat)) return;

    rows.push({ secao: `LOGOS · ${cat}`, quantidade: 0, valor: val ?? "0" });

  });



  rows.push(

    {

      secao: "Caixa · Turnos",

      quantidade: caixa.turnos ?? cash.turnos?.count ?? 0,

      valor: "0",

    },

    {

      secao: "Caixa · Despesa Caixa",

      quantidade: 0,

      valor: (caixa.despesaCaixa || cash.despesaCaixa)?.apurado ?? "0",

    },

    {

      secao: "Caixa · Vale Funcionário",

      quantidade: 0,

      valor: (caixa.valeFuncionario || cash.valeFuncionario)?.apurado ?? "0",

    },

    {

      secao: "Caixa · Empréstimos",

      quantidade: 0,

      valor: (caixa.emprestimos || cash.emprestimos)?.apurado ?? "0",

    },

    {

      secao: "Caixa · Diferenças",

      quantidade: caixa.diferencas?.count ?? cash.diferencas?.count ?? 0,

      valor: "0",

    }

  );



  return rows;

}



export function renderFinanceCenter(container, data, filters, options = {}) {

  const summary = data?.summary || {};

  const expenses = data?.expenses || {};

  const payables = data?.payables || {};

  const receivables = data?.receivables || {};

  const bank = data?.bank || {};

  const cash = data?.cash || {};

  const fromSnapshot = data?.fromSnapshot ? "Snapshot" : "Live";

  const lastUpdated = data?.lastUpdated || "—";

  const warnings = [...(data?.warnings || []), ...(summary.warnings || [])].filter(Boolean);



  const despesas = summary.despesasGerenciais || expenses.resumo || {};

  const cp = summary.contasPagar || payables.buckets || {};

  const cr = summary.contasReceber || receivables.buckets || {};

  const bankResumo = summary.movimentoBancario || bank.resumo || {};

  const caixa = summary.caixa || {};

  const intel = data?.intelligence || {};

  const health = data?.healthScore || {};

  const advanced = data?.advanced || {};

  const healthV3 = data?.healthScoreV3 || {};

  const suppliers = data?.supplierIntelligence || {};

  const segPayload = data?.supplierSegmentation?.segmentationV2 || data?.supplierSegmentation || {};

  const supAnalytics = suppliers.analytics || {};

  const segKpis = segPayload.kpis || {};

  const segHighlights = segPayload.highlights || {};

  const cls = intel.classification || {};

  const topCat = intel.topCategories?.[0];

  const topSup = intel.topSuppliers?.[0];

  const healthiest = health.healthiest;

  const critical = health.critical;



  const intelligenceHtml = intel.classification || advanced.accountAnalytics || supAnalytics.topFornecedores?.length || segPayload.topStrategic?.length

    ? `

      <section class="panel fc-intelligence" data-testid="fc-intelligence">

        <h3>Inteligência Financeira</h3>

        <div class="fc-cards fc-cards-inline">

          <article class="fc-card"><h3>Health Score Rede</h3><p class="fc-val">${health.networkScore ?? "—"}</p><span class="small">${health.networkLevel ?? ""}</span></article>

          <article class="fc-card"><h3>Categoria Líder</h3><p class="fc-val">${topCat?.categoriaLogosV2 ?? "—"}</p><span class="small">${fmtMoney(topCat?.valor)}</span></article>

          <article class="fc-card"><h3>Fornecedor Líder</h3><p class="fc-val">${(topSup?.fornecedor || "—").slice(0, 40)}</p><span class="small">${fmtMoney(topSup?.valor)}</span></article>

          <article class="fc-card"><h3>Filial Mais Saudável</h3><p class="fc-val">${healthiest?.empresaCodigo ?? "—"}</p><span class="small">Score ${healthiest?.score ?? "—"}</span></article>

          <article class="fc-card"><h3>Filial Mais Crítica</h3><p class="fc-val">${critical?.empresaCodigo ?? "—"}</p><span class="small">Score ${critical?.score ?? "—"}</span></article>

          <article class="fc-card"><h3>OUTROS (legacy)</h3><p class="fc-val">${cls.outrosPercent ?? "—"}%</p><span class="small">${fmtMoney(cls.outrosValor)} · identificado ${cls.identifiedPercent ?? "—"}%</span></article>

        </div>

        ${renderIntelTable(intel.topExpenses, ["descricao", "valor", "categoriaLogosV2"], ["Descrição", "Valor", "Categoria V2"], "Top Despesas")}

        ${renderIntelTable(intel.topSuppliers, ["fornecedor", "valor", "count"], ["Fornecedor", "Valor", "Qtd"], "Top Fornecedores")}

        <h4>Inteligência Avançada F01.4-B</h4>

        <div class="fc-cards fc-cards-inline" data-testid="fc-advanced-cards">

          <article class="fc-card"><h3>Health Score V3</h3><p class="fc-val">${healthV3.networkScoreV3 ?? "—"}</p><span class="small">${healthV3.networkLevel ?? ""}</span></article>

          <article class="fc-card"><h3>Data Quality</h3><p class="fc-val">${advanced.dataQuality?.score ?? "—"}</p><span class="small">Plano ${advanced.dataQuality?.components?.planoConta ?? "—"}% · Centro ${advanced.dataQuality?.components?.centroCusto ?? "—"}%</span></article>

          <article class="fc-card"><h3>DRE Readiness</h3><p class="fc-val">${advanced.dreReadiness?.coberturaPct ?? "—"}%</p><span class="small">Meta ${advanced.dreReadiness?.metaFuturaPct ?? 85}%</span></article>

          <article class="fc-card"><h3>Alertas</h3><p class="fc-val">${(advanced.anomalies || []).length}</p><span class="small">severidade ≥ MEDIUM</span></article>

        </div>

        ${renderIntelTable(advanced.accountAnalytics?.topPlanosConta, ["descricao", "valorTotal", "participacaoPct", "quantidade"], ["Plano Conta", "Valor", "Part.%", "Qtd"], "Top Planos de Conta")}

        ${renderIntelTable(advanced.costCenterAnalytics?.topCentrosCusto, ["centroCusto", "valorTotal", "participacaoPct", "quantidade"], ["Centro Custo", "Valor", "Part.%", "Qtd"], "Top Centros de Custo")}

        ${renderIntelTable(advanced.benchmark?.filiais, ["empresaCodigo", "gasto", "indiceBenchmarkRede", "classificacaoRede"], ["Filial", "Gasto", "Índice Rede", "Classificação"], "Benchmark Filiais")}

        ${renderIntelTable(advanced.anomalies, ["tipo", "severidade", "periodo", "valor"], ["Tipo", "Severidade", "Período", "Valor"], "Alertas Financeiros")}

        <h4>Supplier Intelligence F01.4-C</h4>

        <div class="fc-cards fc-cards-inline" data-testid="fc-supplier-cards">

          <article class="fc-card"><h3>Fornecedor Líder</h3><p class="fc-val">${(supAnalytics.leader?.supplierCanonicalName || "—").slice(0, 28)}</p><span class="small">${fmtMoney(supAnalytics.leader?.valorTotal)} · ${supAnalytics.leader?.participacaoPct ?? "—"}%</span></article>

          <article class="fc-card"><h3>Mais Concentrado</h3><p class="fc-val">${(supAnalytics.mostConcentrated?.supplierCanonicalName || "—").slice(0, 28)}</p><span class="small">Share ${supAnalytics.mostConcentrated?.supplierShare ?? "—"}%</span></article>

          <article class="fc-card"><h3>Mais Presente</h3><p class="fc-val">${(supAnalytics.mostPresent?.supplierCanonicalName || "—").slice(0, 28)}</p><span class="small">${supAnalytics.mostPresent?.filiaisCount ?? "—"} filiais</span></article>

          <article class="fc-card"><h3>Coverage Score</h3><p class="fc-val">${suppliers.masterSuppliers?.averageCoverageScore ?? "—"}</p><span class="small">Cobertura ${suppliers.lineage?.supplierCoveragePercent ?? "—"}%</span></article>

          <article class="fc-card"><h3>Concentração</h3><p class="fc-val">${suppliers.risk?.supplierConcentrationRisk ?? "—"}%</p><span class="small">Risco ${suppliers.risk?.maxSeverity ?? "—"}</span></article>

          <article class="fc-card"><h3>Alertas Fornecedor</h3><p class="fc-val">${(suppliers.risk?.alerts || []).length}</p><span class="small">${suppliers.masterSuppliers?.uniqueCanonical ?? "—"} canônicos</span></article>

        </div>

        ${renderIntelTable(supAnalytics.topFornecedores, ["supplierCanonicalName", "valorTotal", "participacaoPct", "filiaisCount"], ["Fornecedor", "Valor", "Part.%", "Filiais"], "Top Fornecedores")}

        ${renderIntelTable(suppliers.risk?.alerts, ["tipo", "severidade", "fornecedor", "supplierShare"], ["Tipo", "Severidade", "Fornecedor", "Share %"], "Alertas de Fornecedor")}

        <h4>Supplier Segmentation F01.4-D</h4>

        <div class="fc-cards fc-cards-inline" data-testid="fc-segmentation-cards">

          <article class="fc-card"><h3>Strategic Index</h3><p class="fc-val">${segKpis.strategicSupplierIndex ?? "—"}%</p><span class="small">VIBRA homologada</span></article>

          <article class="fc-card"><h3>Strategic Score VIBRA</h3><p class="fc-val">${segHighlights.vibraStrategicScore ?? "—"}</p><span class="small">Monitoramento ativo</span></article>

          <article class="fc-card"><h3>Confidence Score</h3><p class="fc-val">${segKpis.averageSupplierConfidenceScore ?? "—"}</p><span class="small">Coverage ${segKpis.supplierCoverageIndex ?? "—"}%</span></article>

          <article class="fc-card"><h3>Dependency Index</h3><p class="fc-val">${segKpis.supplierDependencyIndex ?? "—"}%</p><span class="small">Corp Cost ${segKpis.corporateCostIndex ?? "—"}</span></article>

          <article class="fc-card"><h3>Maior Categoria</h3><p class="fc-val">${segHighlights.maiorCategoriaConsumo ?? "—"}</p><span class="small">${segHighlights.maiorPlanoConta ?? "—"}</span></article>

          <article class="fc-card"><h3>Oportunidades</h3><p class="fc-val">${(segPayload.procurementOpportunities || []).length}</p><span class="small">Eco. ${fmtMoney(segKpis.economiaPotencialAnualEstimada)}/ano est.</span></article>

        </div>

        ${renderIntelTable(segPayload.topStrategic, ["supplierCanonicalName", "supplierCategory", "strategicSupplierScore", "valorTotal"], ["Fornecedor", "Categoria", "Score", "Valor"], "Strategic Suppliers")}

        ${renderIntelTable(segPayload.categoryAnalytics, ["supplierCategory", "valorTotal", "participacaoPct", "fornecedoresCount"], ["Categoria", "Valor", "Part.%", "Qtd"], "Supplier Categories")}

        ${renderIntelTable(segPayload.corporateCostMatrix?.slice(0, 15), ["fornecedor", "planoConta", "centroCusto", "filial", "valor"], ["Fornecedor", "Plano", "Centro", "Filial", "Valor"], "Corporate Cost Matrix")}

        ${renderIntelTable(segPayload.procurementOpportunities?.slice(0, 10), ["tipo", "subcategoria", "fornecedorReferencia", "economiaPotencialPeriodo"], ["Tipo", "Subcat.", "Referência", "Economia"], "Procurement Opportunities")}

      </section>`

    : "";



  const warningsHtml =

    warnings.length > 0

      ? `<div class="fc-warnings" role="status"><strong>Avisos:</strong><ul>${warnings

          .map((w) => `<li>${String(w)}</li>`)

          .join("")}</ul></div>`

      : "";



  container.innerHTML = `

    <div class="finance-center" data-testid="finance-center-root">

      <div class="fc-header">

        <div>

          <h2>Centro Financeiro Corporativo</h2>

          <p class="small">Fontes separadas — sem total financeiro único. ${fromSnapshot} · ${lastUpdated}</p>

        </div>

        <div class="fc-actions">

          ${

            options.onRefresh

              ? '<button type="button" id="fcRefresh" class="btn-primary">Atualizar Centro</button>'

              : ""

          }

          <button type="button" id="fcExportCsv" data-testid="fc-export-csv">Exportar CSV</button>

          <button type="button" id="fcExportPdf" data-testid="fc-export-pdf">Exportar PDF</button>

        </div>

      </div>

      ${warningsHtml}



      <div class="fc-cards">

        <article class="fc-card"><h3>Despesas Gerenciais</h3><p class="fc-val">${despesas.totalRegistros ?? 0}</p><span class="small">${fmtMoney(despesas.totalValor)}</span></article>

        <article class="fc-card"><h3>Contas a Pagar</h3><p class="fc-val">${cp.emAberto?.count ?? 0} aberto</p><span class="small">${fmtMoney(cp.emAberto?.valor)}</span></article>

        <article class="fc-card"><h3>Contas a Receber</h3><p class="fc-val">${cr.pendente?.count ?? 0} pendente</p><span class="small">${fmtMoney(cr.pendente?.valor)}</span></article>

        <article class="fc-card"><h3>Movimento Bancário</h3><p class="fc-val">${bankResumo.totalRegistros ?? bank.paginacaoCompleta ?? 0}</p><span class="small">Líq. ${fmtMoney(bankResumo.saldoMovimentado?.liquido)}</span></article>

        <article class="fc-card"><h3>Operação de Caixa</h3><p class="fc-val">${caixa.turnos ?? cash.turnos?.count ?? 0} turnos</p><span class="small">Vale ${fmtMoney((caixa.valeFuncionario || cash.valeFuncionario)?.apurado)}</span></article>

      </div>



      <div class="fc-grid">

        <section class="panel" data-testid="fc-aging-payables"><h3>Aging Contas a Pagar</h3>${renderBucketTable(cp, PAYABLE_AGING_KEYS)}</section>

        <section class="panel" data-testid="fc-aging-receivables"><h3>Aging Contas a Receber</h3>${renderBucketTable(cr, RECEIVABLE_AGING_KEYS)}</section>

        <section class="panel" data-testid="fc-treasury"><h3>Tesouraria</h3>${renderTreasury(bankResumo)}</section>

        <section class="panel" data-testid="fc-logos"><h3>Classificação LOGOS (Despesas)</h3>${renderCategoryTable(despesas.porCategoriaLogos)}</section>

        <section class="panel" data-testid="fc-cash"><h3>Operação de Caixa</h3>${renderCashSection(cash)}</section>

        ${intelligenceHtml}

      </div>

    </div>

  `;



  const exportRows = buildFinanceCenterExportRows(data);



  container.querySelector("#fcRefresh")?.addEventListener("click", () => options.onRefresh?.());

  container.querySelector("#fcExportCsv")?.addEventListener("click", () => {

    downloadCsv(`centro_financeiro_${filters.dataInicial}_${filters.dataFinal}`, EXPORT_COLUMNS, exportRows);

  });

  container.querySelector("#fcExportPdf")?.addEventListener("click", () => {

    openPdfPreview(

      `Centro Financeiro ${filters.dataInicial} — ${filters.dataFinal}`,

      EXPORT_COLUMNS,

      exportRows,

      {

        subtitle: "LOGOS SPACE — blocos separados, sem total único",

        description: "LOGOS SPACE — blocos separados, sem total único",

      }

    );

  });

}



function renderIntelTable(items, keys, labels, title) {
  if (!items?.length) return "";
  const head = labels.map((l) => `<th>${l}</th>`).join("");
  const body = items
    .slice(0, 10)
    .map(
      (row) =>
        `<tr>${keys
          .map((k) => `<td>${k === "valor" ? fmtMoney(row[k]) : row[k] ?? ""}</td>`)
          .join("")}</tr>`
    )
    .join("");
  return `<h4>${title}</h4><table class="table-compact"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

function renderBucketTable(buckets, preferredKeys = []) {

  if (!buckets || Object.keys(buckets).length === 0) return '<p class="small">Sem dados.</p>';

  const keys = preferredKeys.length

    ? preferredKeys.filter((key) => buckets[key])

    : Object.keys(buckets);

  const rows = keys

    .map(

      (key) =>

        `<tr data-bucket="${key}"><td>${labelBucket(key)}</td><td>${buckets[key]?.count ?? 0}</td><td>${fmtMoney(buckets[key]?.valor)}</td></tr>`

    )

    .join("");

  return `<table class="table-compact fc-table-export"><thead><tr><th>Status</th><th>Qtd</th><th>Valor</th></tr></thead><tbody>${rows}</tbody></table>`;

}



function labelBucket(key) {

  const labels = {

    vencido: "Vencido",

    emAberto: "Em aberto",

    aVencer: "A vencer",

    pago: "Pago",

    pendente: "Pendente",

    recebido: "Recebido",

  };

  return labels[key] || key;

}



function renderTreasury(resumo) {

  if (!resumo) return '<p class="small">Sem dados.</p>';

  return `

    <ul class="fc-list fc-table-export">

      <li data-treasury="creditos">Créditos: ${resumo.creditos?.count ?? 0} · ${fmtMoney(resumo.creditos?.valor)}</li>

      <li data-treasury="debitos">Débitos: ${resumo.debitos?.count ?? 0} · ${fmtMoney(resumo.debitos?.valor)}</li>

      <li data-treasury="transferencias">Transferências: ${resumo.transferencias?.count ?? 0} · ${fmtMoney(resumo.transferencias?.valor)}</li>

      <li data-treasury="tarifas">Tarifas: ${resumo.tarifas?.count ?? 0} · ${fmtMoney(resumo.tarifas?.valor)}</li>

    </ul>`;

}



function renderCategoryTable(porCategoria) {

  if (!porCategoria) return '<p class="small">Sem dados.</p>';

  const ordered = LOGOS_CATEGORIES.filter((cat) => porCategoria[cat] !== undefined).map((cat) => [

    cat,

    porCategoria[cat],

  ]);

  const extra = Object.entries(porCategoria).filter(([cat]) => !LOGOS_CATEGORIES.includes(cat));

  const rows = [...ordered, ...extra]

    .map(([cat, val]) => `<tr data-logos="${cat}"><td>${cat}</td><td>${fmtMoney(val)}</td></tr>`)

    .join("");

  return `<table class="table-compact fc-table-export"><thead><tr><th>Categoria LOGOS</th><th>Valor</th></tr></thead><tbody>${rows}</tbody></table>`;

}



function renderCashSection(cash) {

  if (!cash) return '<p class="small">Sem dados.</p>';

  return `

    <ul class="fc-list fc-table-export">

      <li data-cash="turnos">Turnos: ${cash.turnos?.count ?? cash.turnos ?? 0}</li>

      <li data-cash="despesaCaixa">Despesa caixa: ${fmtMoney(cash.despesaCaixa?.apurado)}</li>

      <li data-cash="valeFuncionario">Vale funcionário: ${fmtMoney(cash.valeFuncionario?.apurado)}</li>

      <li data-cash="emprestimos">Empréstimos: ${fmtMoney(cash.emprestimos?.apurado)}</li>

      <li data-cash="diferencas">Diferenças: ${cash.diferencas?.count ?? 0}</li>

    </ul>`;

}

