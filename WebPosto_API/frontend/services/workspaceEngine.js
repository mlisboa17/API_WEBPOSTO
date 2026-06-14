/** UX-02 — Agrega dados existentes do cockpit em modelo de workspace (sem API nova). */
import { getFiliaisAtivas, getNomeFilial } from "../components/filiais.js";
import { formatCurrency } from "./format.js";

function num(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function money(value) {
  if (value === null || value === undefined || value === "") return "—";
  return formatCurrency(num(value));
}

function severityRank(level) {
  return { CRÍTICO: 0, CRITICO: 0, ALTO: 1, MÉDIO: 2, MEDIO: 2, BAIXO: 3 }[String(level || "").toUpperCase()] ?? 9;
}

function normalizeSeverity(raw) {
  const value = String(raw || "MÉDIO").toUpperCase();
  if (value.includes("CRIT")) return "CRÍTICO";
  if (value === "ALTO" || value === "HIGH") return "ALTO";
  if (value === "BAIXO" || value === "LOW") return "BAIXO";
  return "MÉDIO";
}

export function buildExecutiveWorkspace(data = {}) {
  const scorecard = data.executiveScorecard?.cockpit || data.executiveScorecard || {};
  const scoreExec = data.executiveScorecard?.executiveAnswers || {};
  const commercial = data.commercialExecution || {};
  const commCockpit = commercial.cockpit || {};
  const commExec = commercial.executiveAnswers || {};
  const commPerf = commercial.commercialPerformance || {};
  const products = data.nonFuelProducts || {};
  const prodCockpit = products.cockpit || {};
  const prodExec = products.executiveAnswers || {};
  const fuel = data.fuelGovernance || {};
  const fuelCockpit = fuel.cockpit || {};
  const fuelExec = fuel.executiveAnswers || {};
  const nfce = data.nfceIntelligence || {};
  const nfceCockpit = nfce.cockpit || {};
  const nfceRisks = nfce.nfceRiskEngine?.risks || nfceCockpit.riscoFiscal || [];
  const action = data.actionCenter || {};
  const actionCockpit = action.cockpit || {};
  const learning = data.commercialLearning || {};
  const learnCockpit = learning.cockpit || {};
  const benchmark = data.benchmark || {};
  const benchCockpit = benchmark.cockpit || {};

  const summary = [
    { key: "receita", label: "Receita", value: money(scoreExec["1_faturamento"] ?? scorecard.faturamento ?? prodExec["1_receitaProdutosVendidos"] ?? prodCockpit.receitaTotal), hint: "Rede consolidada" },
    { key: "margem", label: "Margem", value: money(commExec["9_margemRealizada"] ?? commCockpit.margemRealizada ?? prodCockpit.margemBruta), hint: "Produtos Vendidos + execução" },
    { key: "combustivel", label: "Combustível", value: `${fuelCockpit.conformidadeLmc ?? fuelExec["3_taxaConformidadeLmc"] ?? "—"}% LMC`, hint: "Conformidade operacional" },
    { key: "produtos", label: "Produtos Vendidos", value: money(prodExec["1_receitaProdutosVendidos"] ?? prodCockpit.receitaTotal), hint: "Receita não combustível" },
    { key: "nfce", label: "NFCE", value: `${nfceCockpit.taxaConciliacao ?? nfceCockpit.conciliacaoPct ?? "—"}%`, hint: "Conciliação fiscal" },
    { key: "filiais", label: "Filiais Ativas", value: String(getFiliaisAtivas().length), hint: "Registry Onda 1" },
  ];

  const alerts = [];

  (fuel.delayAnalysisEngine?.atrasos || fuelCockpit.atrasos || []).slice(0, 5).forEach((item) => {
    alerts.push({
      severity: normalizeSeverity(item.severidade || "ALTO"),
      origin: "Combustível",
      title: "LMC atrasado",
      detail: `${getNomeFilial(item.empresaCodigo || item.filial)} · ${item.diasAtraso ?? item.atraso ?? "—"} dia(s)`,
      view: "fuelGovernance",
    });
  });

  if (num(fuelExec["2_diasSemLmc"] ?? fuelCockpit.diasSemLmc) > 0) {
    alerts.push({
      severity: "ALTO",
      origin: "Combustível",
      title: "Dias sem LMC na rede",
      detail: `${fuelExec["2_diasSemLmc"] ?? fuelCockpit.diasSemLmc} dia(s) sem evidência`,
      view: "lmcIntelligence",
    });
  }

  nfceRisks.slice(0, 4).forEach((risk) => {
    alerts.push({
      severity: normalizeSeverity(risk.severidade || risk.level || "MÉDIO"),
      origin: "Fiscal",
      title: risk.tipo || risk.title || "Risco NFCE",
      detail: risk.descricao || risk.message || "Revisar conciliação fiscal",
      view: "nfceIntelligence",
    });
  });

  if ((actionCockpit.semEvidencia || []).length > 0) {
    alerts.push({
      severity: "MÉDIO",
      origin: "Financeiro",
      title: "Conciliação / evidência pendente",
      detail: `${actionCockpit.semEvidencia.length} ação(ões) sem evidência`,
      view: "actionCenter",
    });
  }

  if (num(prodCockpit.mixAbaixoMetaPct ?? prodExec["mixAbaixoMeta"]) > 0) {
    alerts.push({
      severity: "MÉDIO",
      origin: "Comercial",
      title: "Mix abaixo da meta",
      detail: "Mix de Produtos Vendidos requer atenção",
      view: "nonFuelProducts",
    });
  }

  alerts.sort((a, b) => severityRank(a.severity) - severityRank(b.severity));

  const opportunities = [];
  const recoActions = commercial.commercialAssignmentEngine?.actions || commCockpit.planoAcao || [];
  recoActions.slice(0, 6).forEach((item) => {
    opportunities.push({
      title: item.tipo || item.actionType || "Ação comercial",
      impact: money(item.roiEsperado ?? item.deltaReceita ?? item.impactoFinanceiro),
      filial: getNomeFilial(item.empresaCodigo),
      priority: item.prioridade || "MÉDIO",
      owner: item.responsavelNome || item.ownerName || "—",
      view: "commercialExecution",
    });
  });

  (learnCockpit.recomendacoes || learning.recommendations || []).slice(0, 4).forEach((item) => {
    opportunities.push({
      title: item.recomendacao || item.titulo || "Recomendação comercial",
      impact: money(item.impactoEstimado ?? item.deltaMargem),
      filial: getNomeFilial(item.empresaCodigo),
      priority: item.prioridade || "ALTO",
      owner: item.responsavel || "—",
      view: "commercialLearning",
    });
  });

  if (benchCockpit.gaps?.length) {
    benchCockpit.gaps.slice(0, 3).forEach((gap) => {
      opportunities.push({
        title: gap.indicador || "Benchmark não atingido",
        impact: gap.delta ?? gap.gap ?? "—",
        filial: getNomeFilial(gap.empresaCodigo),
        priority: "MÉDIO",
        owner: "—",
        view: "benchmark",
      });
    });
  }

  const execution = {
    abertas: num(commExec["1_totalAcoes"] ?? commCockpit.totalAcoes),
    executadas: num(commExec["2_acoesExecutadas"] ?? commCockpit.acoesExecutadas),
    validadas: num(commExec["3_acoesValidadas"] ?? commCockpit.acoesValidadas),
    roi: money(commExec["6_receitaRealizada"] ?? commCockpit.receitaRealizada ?? actionCockpit.roiRealizadoTotal),
    taxaExecucao: commExec["15_taxaExecucaoPct"] ?? "—",
  };

  const porFilial = commPerf.porFilial || [];
  const fuelRanking = fuel.branchComplianceRanking?.ranking || fuelCockpit.rankingFiliais || [];
  const branchRows = porFilial.length ? porFilial : fuelRanking;

  const branches = {
    top: [...branchRows]
      .sort((a, b) => num(b.receita ?? b.score ?? b.conformidade) - num(a.receita ?? a.score ?? a.conformidade))
      .slice(0, 5)
      .map((row) => ({
        filial: getNomeFilial(row.empresaCodigo ?? row.codigo),
        metric: money(row.receita ?? row.margem ?? row.score ?? row.conformidade),
        tag: "Destaque",
      })),
    risk: [...branchRows]
      .sort((a, b) => num(a.score ?? a.conformidade ?? 100) - num(b.score ?? b.conformidade ?? 100))
      .slice(0, 5)
      .map((row) => ({
        filial: getNomeFilial(row.empresaCodigo ?? row.codigo),
        metric: row.risco || row.status || `${row.conformidade ?? "—"}%`,
        tag: "Risco",
      })),
    semLmc: (fuel.delayAnalysisEngine?.atrasos || fuelCockpit.atrasos || [])
      .slice(0, 5)
      .map((row) => ({
        filial: getNomeFilial(row.empresaCodigo),
        metric: `${row.diasAtraso ?? "—"}d atraso`,
        tag: "LMC",
      })),
    bestMix: [...(prodCockpit.mixPorFilial || products.mixHealthCommercial?.porFilial || [])]
      .sort((a, b) => num(b.mixProdutosVendidosPct ?? b.mixPct) - num(a.mixProdutosVendidosPct ?? a.mixPct))
      .slice(0, 5)
      .map((row) => ({
        filial: getNomeFilial(row.empresaCodigo ?? row.codigo),
        metric: `${row.mixProdutosVendidosPct ?? row.mixPct ?? "—"}% mix`,
        tag: "Mix",
      })),
    fuelDependency: [...(prodCockpit.dependenciaCombustivel || fuel.fuelRiskEngine?.filiaisRisco || [])]
      .sort((a, b) => num(b.dependenciaCombustivelPct ?? b.dependenciaPct) - num(a.dependenciaCombustivelPct ?? a.dependenciaPct))
      .slice(0, 5)
      .map((row) => ({
        filial: getNomeFilial(row.empresaCodigo ?? row.codigo),
        metric: `${row.dependenciaCombustivelPct ?? row.dependenciaPct ?? "—"}% comb.`,
        tag: "Dependência",
      })),
  };

  return { summary, alerts, opportunities, execution, branches };
}
