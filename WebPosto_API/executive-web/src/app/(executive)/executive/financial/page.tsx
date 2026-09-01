"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  RefreshCcw,
  Wallet,
  TrendingUp,
  TrendingDown,
  Package,
  Receipt,
  Fuel,
  Search,
  AlertTriangle,
  Building2,
  CheckCircle2,
  BarChart3,
  FileDown,
  FileSpreadsheet,
  Trophy,
  Layers,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { GlobalFilterHeader } from "@/components/executive/global-filter-header";
import { ExpenseDetailModal } from "@/components/executive/expense-detail-modal";
import { DrePanel } from "@/components/executive/dre-panel";
import { BranchBenchmarkPanel } from "@/components/executive/branch-benchmark-panel";
import { DreIntelligencePanel } from "@/components/executive/dre-intelligence-panel";
import { DreMultidimensionalPanel } from "@/components/executive/dre-multidimensional-panel";
import { ExecutiveHealthSynthesisCard } from "@/components/executive/executive-health-synthesis-card";
import { ExpenseClassificationModal } from "@/components/executive/expense-classification-modal";
import { DailyAvgBadge } from "@/components/executive/trend-badge";
import { ExecutiveBriefing } from "@/components/executive/executive-briefing";
import { useGlobalFilter } from "@/contexts/global-filter-context";
import { useOfflineMode } from "@/contexts/offline-mode-context";
import { apiService } from "@/lib/api";
import { exportDataAuditExcel, exportDataAuditPdf } from "@/lib/export-executive-report";
import { inclusiveDays } from "@/lib/period";
import {
  buildMonthProjection,
  daysElapsedInMonth,
  daysInMonthOf,
  movingWindow30,
  type MonthProjectionResult,
} from "@/lib/dre-projection";
import {
  REGIME_OPTIONS,
  classifyPeriodLock,
  type DreRegime,
} from "@/lib/dre-period";
import {
  breakevenLitros,
  buildDelta,
  comparePeriodFor,
  compareScaleFor,
  detectVariances,
  formatDeltaPct,
  formatDeltaRs,
  margemMediaRsLitro,
  topVariances,
  type CompareMode,
  type DeltaBlock,
  type VarianceAlert,
} from "@/lib/dre-variance";
import {
  TREND_OPTIONS,
  classifyExpenseLeverage,
  formatPctRl,
  scaleBaseline,
  verticalPct,
} from "@/lib/dre-analytics";
import type {
  BranchBenchmarkResponse,
  DataAuditExpenseCategory,
  DataAuditFilial,
  DataAuditResponse,
  DreIntelligenceResponse,
  DreLine,
  DreMultidimensionalResponse,
  ExecutiveHealthSynthesisResponse,
  ReviewableFact,
  SalesCompositionResponse,
} from "@/types/api";
import { cn } from "@/lib/utils";

const FILIAL_ORDER = [5555, 11495, 74014];
const SECTOR_COLORS = ["#3b82f6", "#f97316", "#22c55e", "#a855f7"];
const FUEL_COLORS = ["#3b82f6", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444", "#06b6d4"];

type TabType = "overview" | "dre" | "multidim" | "benchmark" | "reconciliation";

const VALID_TABS = new Set<TabType>(["overview", "dre", "multidim", "benchmark", "reconciliation"]);

function parseTabParam(value: string | null): TabType {
  if (value && VALID_TABS.has(value as TabType)) return value as TabType;
  return "overview";
}

export default function ExecutiveFinancialPage() {
  return (
    <Suspense fallback={<div className="p-8 text-slate-400 text-sm">Carregando Centro Financeiro…</div>}>
      <ExecutiveFinancialPageInner />
    </Suspense>
  );
}

function ExecutiveFinancialPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [tab, setTabState] = useState<TabType>(() => parseTabParam(searchParams.get("tab")));
  const [loading, setLoading] = useState(true);
  const [dreLoading, setDreLoading] = useState(false);
  const [dreStale, setDreStale] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [audit, setAudit] = useState<DataAuditResponse | null>(null);
  const [prevAudit, setPrevAudit] = useState<DataAuditResponse | null>(null);
  const [d30Audit, setD30Audit] = useState<DataAuditResponse | null>(null);
  const [composition, setComposition] = useState<SalesCompositionResponse | null>(null);
  const [dreLines, setDreLines] = useState<DreLine[]>([]);
  const [facts, setFacts] = useState<ReviewableFact[]>([]);
  const [classifyOpen, setClassifyOpen] = useState(false);
  const [regime, setRegime] = useState<DreRegime>("competencia");
  const [forceProject, setForceProject] = useState(false);
  const [compareMode, setCompareMode] = useState<CompareMode>("m1");
  const [benchmark, setBenchmark] = useState<BranchBenchmarkResponse | null>(null);
  const [benchmarkLoading, setBenchmarkLoading] = useState(false);
  const [benchmarkSelected, setBenchmarkSelected] = useState<number[]>([...FILIAL_ORDER]);
  const [intelligence, setIntelligence] = useState<DreIntelligenceResponse | null>(null);
  const [intelLoading, setIntelLoading] = useState(false);
  const [forecastHorizon, setForecastHorizon] = useState<"mes" | "trimestre" | "ano">("mes");
  const [multidim, setMultidim] = useState<DreMultidimensionalResponse | null>(null);
  const [multidimLoading, setMultidimLoading] = useState(false);
  const [healthSynth, setHealthSynth] = useState<ExecutiveHealthSynthesisResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [selectedCat, setSelectedCat] = useState<{
    filial: DataAuditFilial;
    cat: DataAuditExpenseCategory;
  } | null>(null);

  const {
    selectedFilial,
    isConsolidated,
    periodDates,
    periodLabel,
    filialShortLabel,
  } = useGlobalFilter();
  const { writesAllowed } = useOfflineMode();
  const empresaCodigo = isConsolidated ? undefined : selectedFilial;

  const setTab = useCallback(
    (next: TabType) => {
      setTabState(next);
      const params = new URLSearchParams(searchParams.toString());
      if (next === "overview") params.delete("tab");
      else params.set("tab", next);
      const qs = params.toString();
      router.replace(qs ? `/executive/financial?${qs}` : "/executive/financial", { scroll: false });
    },
    [router, searchParams]
  );

  useEffect(() => {
    const fromUrl = parseTabParam(searchParams.get("tab"));
    setTabState((prev) => (prev === fromUrl ? prev : fromUrl));
  }, [searchParams]);

  const periodLock = useMemo(
    () => classifyPeriodLock(periodDates.start, periodDates.end),
    [periodDates.start, periodDates.end]
  );

  // Período fechado: projeção só se o usuário ativar manualmente
  useEffect(() => {
    if (periodLock.mode === "closed") {
      setForceProject(false);
    }
  }, [periodLock.mode, periodDates.start, periodDates.end]);

  const projectionEnabled =
    periodLock.mode === "open" ? periodLock.autoProject : forceProject;

  const fetchDre = useCallback(
    async (refresh = false) => {
      setDreLoading(true);
      setDreStale(false);
      try {
        const dre = await apiService.getCompleteDre(
          periodDates.start,
          periodDates.end,
          empresaCodigo,
          { refresh, timeoutMs: 12000, regime }
        );
        setDreLines(dre?.lines || []);
        setDreStale(Boolean(dre?.stale || dre?.fromCache));
      } catch {
        setDreLines([]);
      } finally {
        setDreLoading(false);
      }
    },
    [periodDates.start, periodDates.end, empresaCodigo, regime]
  );

  const compareDates = useMemo(
    () => comparePeriodFor(compareMode, periodDates.start, periodDates.end),
    [compareMode, periodDates.start, periodDates.end]
  );

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const d30 = movingWindow30(periodDates.end);
      const needD30 =
        projectionEnabled || daysElapsedInMonth(periodDates.end) <= 15;
      const regimeOpts = { regime };
      // Hot-path: overview sem DRE (lazy) — evita travar a tela no dre-complete
      const [auditRes, prevAuditRes, compositionRes, reviewable, d30Res] = await Promise.all([
        apiService.getDataAudit(periodDates.start, periodDates.end, empresaCodigo, regimeOpts),
        apiService
          .getDataAudit(compareDates.start, compareDates.end, empresaCodigo, regimeOpts)
          .catch(() => null),
        apiService.getSalesComposition(periodDates.start, periodDates.end, empresaCodigo),
        apiService
          .getReviewableFacts(periodDates.start, periodDates.end, empresaCodigo)
          .catch(() => [] as ReviewableFact[]),
        needD30
          ? apiService
              .getDataAudit(d30.start, d30.end, empresaCodigo, regimeOpts)
              .catch(() => null)
          : Promise.resolve(null),
      ]);
      setAudit(auditRes);
      setPrevAudit(prevAuditRes);
      setComposition(compositionRes);
      setFacts(Array.isArray(reviewable) ? reviewable : []);
      setD30Audit(d30Res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar painel financeiro");
    } finally {
      setLoading(false);
    }
  }, [
    periodDates.start,
    periodDates.end,
    empresaCodigo,
    regime,
    projectionEnabled,
    compareDates.start,
    compareDates.end,
  ]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  const fetchBenchmark = useCallback(async () => {
    setBenchmarkLoading(true);
    try {
      const data = await apiService.getBranchBenchmark(
        periodDates.start,
        periodDates.end,
        { regime, compare: compareMode }
      );
      setBenchmark(data);
    } catch {
      setBenchmark(null);
    } finally {
      setBenchmarkLoading(false);
    }
  }, [periodDates.start, periodDates.end, regime, compareMode]);

  const fetchIntelligence = useCallback(async () => {
    setIntelLoading(true);
    try {
      const data = await apiService.getDreIntelligence(
        periodDates.start,
        periodDates.end,
        {
          regime,
          compare: compareMode,
          horizon: forecastHorizon,
          company: empresaCodigo,
        }
      );
      setIntelligence(data);
    } catch {
      setIntelligence(null);
    } finally {
      setIntelLoading(false);
    }
  }, [
    periodDates.start,
    periodDates.end,
    regime,
    compareMode,
    forecastHorizon,
    empresaCodigo,
  ]);

  useEffect(() => {
    if (tab === "dre") {
      void fetchDre(false);
    }
  }, [tab, fetchDre]);

  const fetchMultidim = useCallback(async () => {
    setMultidimLoading(true);
    try {
      const data = await apiService.getDreMultidimensional(
        periodDates.start,
        periodDates.end,
        { regime, company: empresaCodigo }
      );
      setMultidim(data);
    } catch {
      setMultidim(null);
    } finally {
      setMultidimLoading(false);
    }
  }, [periodDates.start, periodDates.end, regime, empresaCodigo]);

  const fetchHealthSynth = useCallback(async () => {
    setHealthLoading(true);
    try {
      const data = await apiService.getHealthSynthesis(
        periodDates.start,
        periodDates.end,
        { regime, compare: compareMode, company: empresaCodigo }
      );
      setHealthSynth(data);
    } catch {
      setHealthSynth(null);
    } finally {
      setHealthLoading(false);
    }
  }, [periodDates.start, periodDates.end, regime, compareMode, empresaCodigo]);

  useEffect(() => {
    if (tab === "benchmark") {
      void fetchBenchmark();
    }
  }, [tab, fetchBenchmark]);

  useEffect(() => {
    if (tab === "multidim") {
      void fetchMultidim();
    }
  }, [tab, fetchMultidim]);

  useEffect(() => {
    if (tab === "overview" || tab === "dre") {
      void fetchIntelligence();
    }
  }, [tab, fetchIntelligence]);

  useEffect(() => {
    if (tab === "overview" || tab === "dre") {
      void fetchHealthSynth();
    }
  }, [tab, fetchHealthSynth]);

  const localUnavailable = Boolean(audit?.unavailable || composition?.unavailable);

  const formatBRL = (v: number) =>
    new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(v || 0);

  const filiais = useMemo(
    () =>
      (audit?.filiais || [])
        .slice()
        .sort(
          (a, b) =>
            FILIAL_ORDER.indexOf(a.empresaCodigo) - FILIAL_ORDER.indexOf(b.empresaCodigo)
        ),
    [audit?.filiais]
  );

  const kpis = useMemo(() => {
    const c = audit?.consolidado || {};
    const fat = Number(c.faturamentoTotal || 0);
    const litros = Number(c.volumeLitros || 0);
    const desp = Number(
      c.despesasTotal ??
        filiais.reduce((s, f) => s + (f.despesasTotal || 0), 0)
    );
    const resultado = Number(
      c.resultadoOperacionalDiario ??
        filiais.reduce((s, f) => s + (f.resultadoOperacionalDiario || 0), 0)
    );
    let cpv = Number(c.cpvCombustivel || c.cpvTotal || 0);
    let pessoal = 0;
    let admin = 0;
    let outras = 0;
    for (const f of filiais) {
      for (const cat of f.despesasPorCategoria || []) {
        const key = (cat.categoriaKey || "").toUpperCase();
        const val = Number(cat.valor || 0);
        if (key === "CPV") {
          if (!c.cpvTotal && !c.cpvCombustivel) cpv += val;
        } else if (key === "PESSOAL") pessoal += val;
        else if (key === "ADMINISTRATIVA") admin += val;
        else if (key !== "CPV") outras += val;
      }
    }
    const margemBruta = Number(c.margemBruta ?? fat - cpv);
    const margemRsLitro = Number(
      c.margemBrutaMediaRsLitro ?? (litros > 0 ? margemBruta / litros : 0)
    );
    return {
      fat,
      litros,
      desp,
      resultado,
      cpv,
      pessoal,
      admin,
      outras,
      margemBruta,
      margemRsLitro,
    };
  }, [audit?.consolidado, filiais]);

  const dias = inclusiveDays(periodDates.start, periodDates.end);
  const prevCons = prevAudit?.consolidado || {};
  const prevFiliais = prevAudit?.filiais || [];

  const compareScale = compareScaleFor(compareMode);

  const compareKpis = useMemo(() => {
    const fatRaw = Number(prevCons.faturamentoTotal || 0);
    const litrosRaw = Number(prevCons.volumeLitros || 0);
    const despRaw = Number(
      prevCons.despesasTotal ??
        prevFiliais.reduce((s, f) => s + (f.despesasTotal || 0), 0)
    );
    const resultadoRaw = Number(
      prevCons.resultadoOperacionalDiario ??
        prevFiliais.reduce((s, f) => s + (f.resultadoOperacionalDiario || 0), 0)
    );
    let cpvRaw = Number(prevCons.cpvCombustivel || prevCons.cpvTotal || 0);
    for (const f of prevFiliais) {
      for (const cat of f.despesasPorCategoria || []) {
        if ((cat.categoriaKey || "").toUpperCase() === "CPV" && !prevCons.cpvTotal) {
          cpvRaw += Number(cat.valor || 0);
        }
      }
    }
    const margemRaw = Number(prevCons.margemBruta ?? fatRaw - cpvRaw);
    // Tendência 3/6/12m: baseline = média do período (total da janela ÷ N)
    return {
      fat: scaleBaseline(fatRaw, compareScale),
      litros: scaleBaseline(litrosRaw, compareScale),
      desp: scaleBaseline(despRaw, compareScale),
      resultado: scaleBaseline(resultadoRaw, compareScale),
      cpv: scaleBaseline(cpvRaw, compareScale),
      margemBruta: scaleBaseline(margemRaw, compareScale),
    };
  }, [prevCons, prevFiliais, compareScale]);

  const deltaFat = buildDelta(kpis.fat, compareKpis.fat);
  const deltaCpv = buildDelta(kpis.cpv, compareKpis.cpv);
  const deltaDesp = buildDelta(kpis.desp, compareKpis.desp);
  const deltaRes = buildDelta(kpis.resultado, compareKpis.resultado);
  const deltaMargem = buildDelta(kpis.margemBruta, compareKpis.margemBruta);

  const compareLabel =
    TREND_OPTIONS.find((o) => o.id === compareMode)?.label.replace(/^[^ ]+ /, "") ||
    (compareMode === "y1" ? "Y-1" : "M-1");

  const expenseLeverage = useMemo(
    () =>
      classifyExpenseLeverage({
        despCur: Math.max(0, kpis.desp - kpis.cpv),
        despPrev: Math.max(0, compareKpis.desp - compareKpis.cpv),
        fatCur: kpis.fat,
        fatPrev: compareKpis.fat,
        lucroCur: kpis.resultado,
        lucroPrev: compareKpis.resultado,
      }),
    [kpis, compareKpis]
  );

  const pistaMarginRsL = useMemo(() => {
    const margemComb = Number(
      audit?.consolidado?.margemBrutaCombustivel ?? kpis.margemBruta
    );
    return margemMediaRsLitro(margemComb, kpis.litros);
  }, [audit?.consolidado, kpis.margemBruta, kpis.litros]);

  const despesasFixas = useMemo(() => {
    const fromAudit = Number(audit?.consolidado?.despesasOperacionais ?? NaN);
    if (Number.isFinite(fromAudit)) return Math.max(0, fromAudit);
    return Math.max(0, kpis.desp - kpis.cpv);
  }, [audit?.consolidado, kpis.desp, kpis.cpv]);

  const breakevenL = useMemo(
    () => breakevenLitros(despesasFixas, pistaMarginRsL),
    [despesasFixas, pistaMarginRsL]
  );

  const monthProjection = useMemo(() => {
    const d30 = d30Audit?.consolidado || {};
    return buildMonthProjection({
      periodDays: dias,
      daysElapsedInMonth: daysElapsedInMonth(periodDates.end),
      daysInMonth: daysInMonthOf(periodDates.end),
      fatPeriod: kpis.fat,
      despPeriod: kpis.desp,
      resPeriod: kpis.resultado,
      fatD30: Number(d30.faturamentoTotal || 0) || undefined,
      despD30: Number(d30.despesasTotal || 0) || undefined,
      resD30: Number(d30.resultadoOperacionalDiario || 0) || undefined,
      d30Days: 30,
    });
  }, [dias, kpis.fat, kpis.desp, kpis.resultado, d30Audit, periodDates.end]);

  const sectorMargins = useMemo(() => {
    const summary = composition?.summary;
    const sectors = composition?.compositionBySector || [];
    const fatFuel =
      Number(summary?.faturamentoCombustivel || 0) ||
      Number(
        sectors.find((s) => /combust/i.test(s.setor || ""))?.faturamento || 0
      ) ||
      kpis.fat;
    const fatConv =
      Number(summary?.faturamentoConveniencia || 0) ||
      Number(
        sectors.find((s) => /conven/i.test(s.setor || ""))?.faturamento || 0
      );
    const litros = Number(summary?.litrosVendidos || kpis.litros || 0);
    const cpvFuel = kpis.cpv;
    const margemFuel = fatFuel - cpvFuel;
    const margemFuelRsL = litros > 0 ? margemFuel / litros : kpis.margemRsLitro;
    const margemConvPct = Number(
      sectors.find((s) => /conven/i.test(s.setor || ""))?.margem || 0
    );
    // Se composition não trouxe % da loja, estima 0 (sem inventar CPV loja)
    return {
      pista: {
        fat: fatFuel,
        litros,
        cpv: cpvFuel,
        margem: margemFuel,
        margemRsL: margemFuelRsL,
      },
      loja: {
        fat: fatConv,
        margemPct: margemConvPct,
      },
    };
  }, [composition, kpis.fat, kpis.cpv, kpis.litros, kpis.margemRsLitro]);

  const sectorChart = useMemo(() => {
    const sectors = composition?.compositionBySector || [];
    if (sectors.length) {
      return sectors.map((s) => ({
        name: s.setor || "Setor",
        value: Number(s.faturamento || 0),
        margem: Number(s.margem || 0),
      }));
    }
    const summary = composition?.summary;
    if (!summary) return [];
    return [
      {
        name: "Combustíveis",
        value: Number(summary.faturamentoCombustivel || 0),
        margem: sectorMargins.pista.margemRsL,
      },
      { name: "Produtos de Pista", value: Number(summary.faturamentoProdutosPista || 0), margem: 0 },
      {
        name: "Conveniência",
        value: Number(summary.faturamentoConveniencia || 0),
        margem: sectorMargins.loja.margemPct,
      },
    ].filter((x) => x.value > 0);
  }, [composition, sectorMargins]);

  const fuelChart = useMemo(() => {
    const list = composition?.combustiveis || [];
    return list.slice(0, 8).map((f) => ({
      name: String(f.categoria || "Fuel").slice(0, 18),
      faturamento: Number(f.faturamento || 0),
      litros: Number(f.litros || 0),
    }));
  }, [composition]);

  const planoRows = useMemo(() => {
    const map = new Map<
      string,
      {
        key: string;
        label: string;
        valor: number;
        qtd: number;
        prevValor: number;
        delta: DeltaBlock;
        filiais: DataAuditFilial[];
        sampleFilial?: DataAuditFilial;
        sampleCat?: DataAuditExpenseCategory;
      }
    >();
    const prevMap = new Map<string, number>();
    for (const f of prevFiliais) {
      for (const cat of f.despesasPorCategoria || []) {
        const key = cat.categoriaKey || cat.categoria;
        prevMap.set(key, (prevMap.get(key) || 0) + Number(cat.valor || 0));
      }
    }
    for (const f of filiais) {
      for (const cat of f.despesasPorCategoria || []) {
        const key = cat.categoriaKey || cat.categoria;
        const prev = map.get(key) || {
          key,
          label: cat.categoria,
          valor: 0,
          qtd: 0,
          prevValor: prevMap.get(key) || 0,
          delta: buildDelta(0, 0),
          filiais: [] as DataAuditFilial[],
        };
        prev.valor += Number(cat.valor || 0);
        prev.qtd += Number(cat.qtd_lancamentos || 0);
        if ((cat.qtd_lancamentos || 0) > 0 && !prev.sampleCat) {
          prev.sampleFilial = f;
          prev.sampleCat = cat;
        }
        map.set(key, prev);
      }
    }
    return Array.from(map.values()).map((row) => {
      const prevValor = scaleBaseline(prevMap.get(row.key) || 0, compareScale);
      return {
        ...row,
        prevValor,
        delta: buildDelta(row.valor, prevValor),
        pctRl: verticalPct(row.valor, kpis.fat),
      };
    });
  }, [filiais, prevFiliais, compareScale, kpis.fat]);

  const varianceAlerts = useMemo(() => {
    const currentGroups: Record<string, number> = {
      "Faturamento": kpis.fat,
      CPV: kpis.cpv,
      "Despesas Totais": kpis.desp,
      "Lucro Líquido": kpis.resultado,
      "Margem Bruta": kpis.margemBruta,
    };
    const previousGroups: Record<string, number> = {
      "Faturamento": compareKpis.fat,
      CPV: compareKpis.cpv,
      "Despesas Totais": compareKpis.desp,
      "Lucro Líquido": compareKpis.resultado,
      "Margem Bruta": compareKpis.margemBruta,
    };
    for (const row of planoRows) {
      if ((row.key || "").toUpperCase() === "CPV") continue;
      currentGroups[`Despesa ${row.label}`] = row.valor;
      previousGroups[`Despesa ${row.label}`] = row.prevValor;
    }
    return detectVariances(currentGroups, previousGroups);
  }, [kpis, compareKpis, planoRows]);

  const top3Variances = useMemo(
    () => topVariances(varianceAlerts, 3),
    [varianceAlerts]
  );

  return (
    <div className="p-4 lg:p-8 max-w-[1600px] mx-auto space-y-6">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge className="bg-blue-600 hover:bg-blue-700 border-0">LOGOS</Badge>
            <span className="text-[10px] text-slate-300 uppercase tracking-widest font-bold">
              Executive Intelligence
            </span>
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-2">
            <Building2 className="text-blue-400" size={28} />
            LOGOS | Executive Intelligence
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Dashboard do Presidente • Centro Financeiro • {filialShortLabel} • {periodLabel}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={!audit || loading}
            onClick={() =>
              audit &&
              exportDataAuditPdf(audit, {
                filialLabel: filialShortLabel,
                periodLabel,
              })
            }
            className="border-rose-500/30 text-rose-200 hover:bg-rose-500/10"
          >
            <FileDown size={14} className="mr-2" />
            Baixar PDF Executivo
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={!audit || loading}
            onClick={() => audit && exportDataAuditExcel(audit)}
            className="border-emerald-500/30 text-emerald-200 hover:bg-emerald-500/10"
          >
            <FileSpreadsheet size={14} className="mr-2" />
            Exportar Excel
          </Button>
          <Button
            size="sm"
            onClick={() => {
              void fetchData();
              if (tab === "dre") void fetchDre(true);
              if (tab === "benchmark") void fetchBenchmark();
              if (tab === "multidim") void fetchMultidim();
              if (tab === "overview" || tab === "dre") {
                void fetchIntelligence();
                void fetchHealthSynth();
              }
            }}
            disabled={
              loading ||
              dreLoading ||
              benchmarkLoading ||
              intelLoading ||
              multidimLoading ||
              healthLoading
            }
            className="bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20"
          >
            <RefreshCcw
              size={14}
              className={cn("mr-2", (loading || dreLoading) && "animate-spin")}
            />
            Atualizar
          </Button>
        </div>
      </header>

      <GlobalFilterHeader />

      {/* Controles DRE — 2 linhas; Filial/Período só no GlobalFilterHeader */}
      <div className="rounded-lg border border-slate-800/80 bg-slate-900/40 px-3 py-2.5 space-y-2">
        <div className="flex flex-col sm:flex-row sm:items-center gap-2 flex-wrap">
          <span className="text-[10px] uppercase tracking-widest text-slate-500 font-bold shrink-0 w-[72px]">
            Regime
          </span>
          <div className="flex flex-wrap items-center gap-1.5 flex-1">
            {(
              [
                { id: "competencia" as const, short: "📄 Nota", title: REGIME_OPTIONS[0].label },
                { id: "caixa" as const, short: "🏦 Boleto", title: REGIME_OPTIONS[1].label },
              ] as const
            ).map((opt) => (
              <button
                key={opt.id}
                type="button"
                title={opt.title}
                onClick={() => setRegime(opt.id)}
                className={cn(
                  "rounded-md border px-2.5 py-1 text-[11px] font-medium transition-colors",
                  regime === opt.id
                    ? "border-cyan-500/50 bg-cyan-500/10 text-cyan-100"
                    : "border-slate-700/80 bg-slate-950/40 text-slate-400 hover:text-slate-200"
                )}
              >
                {opt.short}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-1.5 sm:ml-auto">
            {healthSynth?.health ? (
              <Badge
                className={cn(
                  "text-[10px] font-semibold px-2 py-0.5",
                  healthSynth.health.classification?.color === "green" &&
                    "bg-emerald-500/15 text-emerald-100 border-emerald-500/30",
                  healthSynth.health.classification?.color === "blue" &&
                    "bg-sky-500/15 text-sky-100 border-sky-500/30",
                  healthSynth.health.classification?.color === "yellow" &&
                    "bg-amber-500/15 text-amber-100 border-amber-500/30",
                  healthSynth.health.classification?.color === "red" &&
                    "bg-rose-500/15 text-rose-100 border-rose-500/30"
                )}
                title={healthSynth.health.classification?.badge}
              >
                Saúde {healthSynth.health.score.toFixed(0)}/100
              </Badge>
            ) : null}
            {periodLock.mode === "open" ? (
              <Badge className="bg-emerald-500/15 text-emerald-200 border-emerald-500/30 text-[10px] font-medium px-2 py-0.5">
                🟢 {periodLock.badgeLabel}
              </Badge>
            ) : (
              <Badge className="bg-slate-700/40 text-slate-200 border-slate-600/40 text-[10px] font-medium px-2 py-0.5">
                ✅ {periodLock.badgeLabel}
              </Badge>
            )}
            {periodLock.mode === "closed" ? (
              <button
                type="button"
                onClick={() => setForceProject((v) => !v)}
                className={cn(
                  "rounded-md border px-2 py-0.5 text-[10px] transition-colors",
                  forceProject
                    ? "border-violet-500/40 bg-violet-500/15 text-violet-200"
                    : "border-slate-700 bg-slate-950/50 text-slate-400 hover:text-slate-200"
                )}
              >
                🔮 Simular/Projetar
              </button>
            ) : null}
          </div>
        </div>
        <div className="flex flex-col sm:flex-row sm:items-center gap-2 flex-wrap border-t border-slate-800/60 pt-2">
          <span className="text-[10px] uppercase tracking-widest text-slate-500 font-bold shrink-0 w-[72px]">
            Comparar
          </span>
          <div className="flex flex-wrap items-center gap-1.5 flex-1">
            {(
              [
                { id: "m1" as const, short: "M-1" },
                { id: "y1" as const, short: "Y-1" },
                { id: "t3" as const, short: "TM3" },
                { id: "t6" as const, short: "TM6" },
                { id: "t12" as const, short: "TM12" },
              ] as const
            ).map((opt) => (
              <button
                key={opt.id}
                type="button"
                title={TREND_OPTIONS.find((t) => t.id === opt.id)?.label || opt.short}
                onClick={() => setCompareMode(opt.id)}
                className={cn(
                  "rounded-md border px-2.5 py-1 text-[11px] font-medium transition-colors",
                  compareMode === opt.id
                    ? "border-sky-500/40 bg-sky-500/15 text-sky-100"
                    : "border-slate-700/80 bg-slate-950/40 text-slate-400 hover:text-slate-200"
                )}
              >
                {opt.short}
              </button>
            ))}
          </div>
          <Badge
            className={cn(
              "text-[10px] sm:ml-auto",
              expenseLeverage.code === "gargalo"
                ? "bg-rose-500/15 text-rose-100 border-rose-500/30"
                : expenseLeverage.code === "neutro"
                  ? "bg-slate-700/40 text-slate-300 border-slate-600/40"
                  : "bg-emerald-500/15 text-emerald-100 border-emerald-500/30"
            )}
            title={
              compareScale > 1
                ? `${expenseLeverage.detail} · média ÷ ${compareScale}`
                : expenseLeverage.detail
            }
          >
            {expenseLeverage.badge}
          </Badge>
        </div>
      </div>

      <ExecutiveHealthSynthesisCard data={healthSynth} loading={healthLoading} />

      <ExecutiveBriefing
        empresaCodigo={empresaCodigo}
        dataReferencia={periodDates.end}
        filialLabel={isConsolidated ? "Consolidado" : filialShortLabel}
      />

      <div className="flex items-center gap-1 bg-slate-900/50 p-1 rounded-lg border border-slate-800 w-fit">
        <TabButton
          active={tab === "overview"}
          onClick={() => setTab("overview")}
          icon={<BarChart3 size={16} />}
          label="Visão Executiva"
        />
        <TabButton
          active={tab === "dre"}
          onClick={() => setTab("dre")}
          icon={<Receipt size={16} />}
          label="DRE"
        />
        <TabButton
          active={tab === "multidim"}
          onClick={() => setTab("multidim")}
          icon={<Layers size={16} />}
          label="DRE Multi"
        />
        <TabButton
          active={tab === "benchmark"}
          onClick={() => setTab("benchmark")}
          icon={<Trophy size={16} />}
          label="Benchmark Filiais"
        />
        <TabButton
          active={tab === "reconciliation"}
          onClick={() => setTab("reconciliation")}
          icon={<CheckCircle2 size={16} />}
          label="Conciliação"
          badge={facts.length}
        />
      </div>

      {tab === "benchmark" ? (
        <div className="space-y-4 animate-in fade-in duration-300">
          <BranchBenchmarkPanel
            data={benchmark}
            loading={benchmarkLoading}
            compareLabel={compareLabel}
            selectedCodes={benchmarkSelected}
            onSelectedCodesChange={setBenchmarkSelected}
          />
        </div>
      ) : tab === "multidim" ? (
        <div className="space-y-4 animate-in fade-in duration-300">
          <DreMultidimensionalPanel data={multidim} loading={multidimLoading} />
        </div>
      ) : tab === "dre" ? (
        <div className="space-y-4 animate-in fade-in duration-300">
          {dreLoading && dreLines.length === 0 ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                {[1, 2, 3, 4].map((i) => (
                  <Skeleton key={i} className="h-24 w-full" />
                ))}
              </div>
              <Skeleton className="h-80 w-full" />
              <p className="text-xs text-slate-500 text-center">
                Carregando DRE resumida (cache RAM / agregação)…
              </p>
            </div>
          ) : (
            <>
              {dreStale ? (
                <div className="rounded-md border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-xs text-amber-200">
                  Exibindo DRE em cache local (timeout/ERP lento). Clique em Atualizar para
                  forçar recálculo.
                </div>
              ) : null}
              {!projectionEnabled ? <ClosedPeriodBanner /> : null}
              <TopVariancePanel alerts={top3Variances} compareLabel={compareLabel} />
              <Card className="border-slate-800 bg-slate-900/90 ring-1 ring-cyan-500/10">
                <CardHeader>
                  <CardTitle className="text-xl text-white">
                    DRE do Período Selecionado
                  </CardTitle>
                  <CardDescription>
                    {filialShortLabel} • {periodLabel} •{" "}
                    {regime === "caixa" ? "Regime de Caixa" : "Competência"} •{" "}
                    <span className="text-emerald-300/90">Foco no Realizado</span>
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {dreLoading ? <Skeleton className="h-10 w-48 mb-4" /> : null}
                  <DrePanel
                    lines={dreLines}
                    onInspectPending={() => setTab("reconciliation")}
                    pendingCount={facts.length}
                    regime={regime}
                    compareLabel={compareLabel}
                    compareSummary={{
                      fat: compareKpis.fat,
                      cpv: compareKpis.cpv,
                      margem: compareKpis.margemBruta,
                      desp: compareKpis.desp,
                      resultado: compareKpis.resultado,
                    }}
                    sectorKpis={{
                      combustiveis: {
                        fat: Number(composition?.summary?.faturamentoCombustivel || 0),
                        margem: Number(
                          (composition?.compositionBySector || []).find((s) =>
                            /combust/i.test(s.setor || "")
                          )?.margem || 0
                        ),
                      },
                      produtos_pista: {
                        fat: Number(composition?.summary?.faturamentoProdutosPista || 0),
                        margem: Number(
                          (composition?.compositionBySector || []).find((s) =>
                            /pista/i.test(s.setor || "")
                          )?.margem || 0
                        ),
                      },
                      conveniencia: {
                        fat: Number(composition?.summary?.faturamentoConveniencia || 0),
                        margem: Number(
                          (composition?.compositionBySector || []).find((s) =>
                            /conven/i.test(s.setor || "")
                          )?.margem || 0
                        ),
                      },
                    }}
                  />
                </CardContent>
              </Card>
              <DreIntelligencePanel
                data={intelligence}
                loading={intelLoading}
                horizon={forecastHorizon}
                onHorizonChange={setForecastHorizon}
              />
              {projectionEnabled ? (
                <div className="space-y-3 pt-2 border-t border-slate-800">
                  <p className="text-[10px] uppercase tracking-widest text-violet-300/80 font-bold">
                    Projeção (secundário) — Realizado + Projetado
                  </p>
                  <MonthRunRateCard projection={monthProjection} formatBRL={formatBRL} />
                  <ProjectionExplainCard
                    mode={monthProjection.mode}
                    hasD30={Boolean(d30Audit?.consolidado)}
                  />
                </div>
              ) : null}
            </>
          )}
        </div>
      ) : loading ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
          <Skeleton className="h-72 w-full" />
        </div>
      ) : error ? (
        <Card className="border-red-500/30 bg-red-500/5 p-8 text-center">
          <AlertTriangle className="mx-auto text-red-400 mb-2" />
          <p className="text-red-300 font-medium">{error}</p>
          <Button className="mt-4" variant="outline" onClick={() => void fetchData()}>
            Tentar novamente
          </Button>
        </Card>
      ) : tab === "overview" ? (
        <div className="space-y-6 animate-in fade-in duration-300">
          {localUnavailable ? (
            <Card className="border-amber-500/30 bg-amber-500/5 p-6 text-center">
              <p className="text-amber-200 text-sm">
                Fonte local indisponível neste modo offline. Nenhum valor foi inventado.
              </p>
            </Card>
          ) : (
            <>
          {!projectionEnabled ? <ClosedPeriodBanner /> : null}

          <TopVariancePanel alerts={top3Variances} compareLabel={compareLabel} />

          <DreIntelligencePanel
            data={intelligence}
            loading={intelLoading}
            horizon={forecastHorizon}
            onHorizonChange={setForecastHorizon}
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Kpi
              label="Margem Média de Pista (R$/Litro)"
              value={pistaMarginRsL.toLocaleString("pt-BR", {
                style: "currency",
                currency: "BRL",
                minimumFractionDigits: 3,
              })}
              icon={<Fuel className="text-amber-300" size={16} />}
              badges={
                <span className="text-[10px] text-slate-400">
                  Margem bruta combustíveis ÷ volumetria
                </span>
              }
            />
            <Kpi
              label="Ponto de Equilíbrio (Breakeven em Litros)"
              value={
                breakevenL == null
                  ? "n/d"
                  : `${breakevenL.toLocaleString("pt-BR", { maximumFractionDigits: 0 })} L`
              }
              icon={<TrendingUp className="text-sky-300" size={16} />}
              badges={
                <span className="text-[10px] text-slate-400">
                  Desp. operacionais fixas ÷ margem R$/L
                </span>
              }
            />
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
            <Kpi
              label="Faturamento Total"
              value={formatBRL(kpis.fat)}
              icon={<Wallet className="text-emerald-400" size={16} />}
              badges={
                <>
                  <DailyAvgBadge value={kpis.fat / dias} format={formatBRL} />
                  <DeltaChip delta={deltaFat} compareLabel={compareLabel} formatBRL={formatBRL} />
                </>
              }
            />
            <Kpi
              label="Margem Bruta Pista"
              value={formatBRL(kpis.margemBruta)}
              icon={<TrendingUp className="text-cyan-400" size={16} />}
              badges={
                <>
                  <span className="text-[10px] font-mono text-cyan-300/90">
                    {pistaMarginRsL.toLocaleString("pt-BR", {
                      style: "currency",
                      currency: "BRL",
                      minimumFractionDigits: 2,
                    })}
                    /L
                  </span>
                  <DeltaChip delta={deltaMargem} compareLabel={compareLabel} formatBRL={formatBRL} />
                </>
              }
            />
            <Kpi
              label="CPV Combustíveis"
              value={formatBRL(kpis.cpv)}
              icon={<Package className="text-violet-400" size={16} />}
              badges={
                <DeltaChip delta={deltaCpv} compareLabel={compareLabel} formatBRL={formatBRL} invert />
              }
            />
            <Kpi
              label="Total Despesas"
              value={formatBRL(kpis.desp)}
              icon={<Receipt className="text-amber-400" size={16} />}
              badges={
                <DeltaChip delta={deltaDesp} compareLabel={compareLabel} formatBRL={formatBRL} invert />
              }
            />
            <Kpi
              label="Resultado Líquido"
              value={formatBRL(kpis.resultado)}
              icon={<TrendingDown className="text-rose-400" size={16} />}
              highlight={kpis.resultado < 0 || deltaRes.anomaly}
              badges={
                <DeltaChip delta={deltaRes} compareLabel={compareLabel} formatBRL={formatBRL} />
              }
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Card className="border-slate-800 bg-slate-900/90">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-white flex items-center gap-2">
                  <Fuel className="text-amber-400" size={16} />
                  Pista (Combustíveis)
                </CardTitle>
                <CardDescription>Margem no padrão de revenda (R$/L)</CardDescription>
              </CardHeader>
              <CardContent className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-[10px] uppercase text-slate-500 font-bold">Faturamento</p>
                  <p className="font-mono text-white">{formatBRL(sectorMargins.pista.fat)}</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-slate-500 font-bold">Volume</p>
                  <p className="font-mono text-white">
                    {sectorMargins.pista.litros.toLocaleString("pt-BR", {
                      maximumFractionDigits: 0,
                    })}{" "}
                    L
                  </p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-slate-500 font-bold">CPV Real</p>
                  <p className="font-mono text-violet-300">{formatBRL(sectorMargins.pista.cpv)}</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-slate-500 font-bold">Margem Bruta</p>
                  <p className="font-mono text-cyan-300">
                    {formatBRL(sectorMargins.pista.margem)}{" "}
                    <span className="text-xs text-cyan-400/80">
                      (
                      {sectorMargins.pista.margemRsL.toLocaleString("pt-BR", {
                        style: "currency",
                        currency: "BRL",
                      })}
                      /L)
                    </span>
                  </p>
                </div>
              </CardContent>
            </Card>
            <Card className="border-slate-800 bg-slate-900/90">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-white flex items-center gap-2">
                  <Package className="text-orange-400" size={16} />
                  Loja de Conveniência
                </CardTitle>
                <CardDescription>Margem bruta em % do faturamento da loja</CardDescription>
              </CardHeader>
              <CardContent className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-[10px] uppercase text-slate-500 font-bold">Faturamento</p>
                  <p className="font-mono text-white">{formatBRL(sectorMargins.loja.fat)}</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-slate-500 font-bold">Margem Bruta</p>
                  <p className="font-mono text-orange-300">
                    {sectorMargins.loja.margemPct > 0
                      ? `${sectorMargins.loja.margemPct.toFixed(1)}%`
                      : "—"}
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            <Card className="border-slate-800 bg-slate-900/90">
              <CardHeader className="pb-2">
                <CardTitle className="text-base text-white flex items-center gap-2">
                  <Fuel className="text-blue-400" size={18} />
                  Vendas por Setor
                </CardTitle>
                <CardDescription>
                  Participação no faturamento • Pista em R$/L · Loja em %
                </CardDescription>
              </CardHeader>
              <CardContent className="h-64">
                {sectorChart.length === 0 ? (
                  <EmptyChart />
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={sectorChart}
                        dataKey="value"
                        nameKey="name"
                        innerRadius={55}
                        outerRadius={90}
                        paddingAngle={2}
                      >
                        {sectorChart.map((_, i) => (
                          <Cell key={i} fill={SECTOR_COLORS[i % SECTOR_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={tooltipStyle}
                        formatter={(v) => formatBRL(Number(v))}
                      />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>

            <Card className="border-slate-800 bg-slate-900/90">
              <CardHeader className="pb-2">
                <CardTitle className="text-base text-white flex items-center gap-2">
                  <Fuel className="text-amber-400" size={18} />
                  Combustíveis — Faturamento
                </CardTitle>
                <CardDescription>Top produtos no período filtrado</CardDescription>
              </CardHeader>
              <CardContent className="h-64">
                {fuelChart.length === 0 ? (
                  <EmptyChart />
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={fuelChart}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                      <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                      <YAxis tick={{ fill: "#64748b", fontSize: 11 }} />
                      <Tooltip
                        contentStyle={tooltipStyle}
                        formatter={(v, name) =>
                          name === "litros"
                            ? [`${Number(v).toLocaleString("pt-BR")} L`, "Volume"]
                            : [formatBRL(Number(v)), "Faturamento"]
                        }
                      />
                      <Bar dataKey="faturamento" radius={[4, 4, 0, 0]}>
                        {fuelChart.map((_, i) => (
                          <Cell key={i} fill={FUEL_COLORS[i % FUEL_COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>
          </div>

          <Card className="border-slate-800 bg-slate-900/90">
            <CardHeader className="pb-2">
              <CardTitle className="text-base text-white">Despesas por Plano de Contas</CardTitle>
              <CardDescription>
                Clique em uma categoria com lançamentos para abrir o drill-down oficial webPosto
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-[10px] uppercase tracking-wider text-slate-300 border-b border-slate-800">
                      <th className="text-left py-2 pr-3 font-bold">Categoria</th>
                      <th className="text-right py-2 pr-3 font-bold">Lançamentos</th>
                      <th className="text-right py-2 pr-3 font-bold">Valor</th>
                      <th className="text-right py-2 pr-3 font-bold">% RL</th>
                      <th className="text-right py-2 pr-3 font-bold">Δ {compareLabel}</th>
                      <th className="text-right py-2 font-bold">Ação</th>
                    </tr>
                  </thead>
                  <tbody>
                    {planoRows.map((row) => {
                      const clickable = row.qtd > 0 && !!row.sampleCat && !!row.sampleFilial;
                      const isExpense = (row.key || "").toUpperCase() !== "CPV";
                      const rowLeverage =
                        isExpense && row.delta.deltaPct != null && row.delta.deltaPct > 0
                          ? classifyExpenseLeverage({
                              despCur: row.valor,
                              despPrev: row.prevValor,
                              fatCur: kpis.fat,
                              fatPrev: compareKpis.fat,
                              lucroCur: kpis.resultado,
                              lucroPrev: compareKpis.resultado,
                            })
                          : null;
                      const showAnomaly =
                        row.delta.anomaly &&
                        (!rowLeverage || rowLeverage.code === "gargalo");
                      return (
                        <tr
                          key={row.key}
                          className={cn(
                            "border-b border-slate-800 hover:bg-white/[0.02]",
                            showAnomaly && "bg-amber-500/5"
                          )}
                        >
                          <td className="py-3 pr-3 text-slate-200">
                            <div className="flex flex-wrap items-center gap-2">
                              <span>{row.label}</span>
                              {rowLeverage && rowLeverage.code !== "neutro" ? (
                                <Badge
                                  className={cn(
                                    "text-[10px]",
                                    rowLeverage.code === "gargalo"
                                      ? "bg-rose-500/15 text-rose-100 border-rose-500/30"
                                      : "bg-emerald-500/15 text-emerald-100 border-emerald-500/30"
                                  )}
                                >
                                  {rowLeverage.badge}
                                </Badge>
                              ) : showAnomaly ? (
                                <Badge className="bg-amber-500/15 text-amber-200 border-amber-500/30 text-[10px]">
                                  {row.delta.deltaPct != null && row.delta.deltaPct > 0
                                    ? `⚠️ +${Math.abs(row.delta.deltaPct).toFixed(0)}%`
                                    : `🔴 ${formatDeltaPct(row.delta.deltaPct)}`}
                                </Badge>
                              ) : null}
                            </div>
                          </td>
                          <td className="py-3 pr-3 text-right text-slate-400 font-mono">
                            {row.qtd}
                          </td>
                          <td className="py-3 pr-3 text-right font-semibold text-white font-mono">
                            {formatBRL(row.valor)}
                          </td>
                          <td className="py-3 pr-3 text-right font-mono text-cyan-300/80 text-xs">
                            {formatPctRl(row.pctRl)}
                          </td>
                          <td className="py-3 pr-3 text-right">
                            <DeltaChip
                              delta={row.delta}
                              compareLabel={compareLabel}
                              formatBRL={formatBRL}
                              invert
                            />
                          </td>
                          <td className="py-3 text-right">
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={!clickable}
                              onClick={() =>
                                clickable &&
                                setSelectedCat({
                                  filial: row.sampleFilial!,
                                  cat: row.sampleCat!,
                                })
                              }
                              className="border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/10 disabled:opacity-40"
                            >
                              <Search size={12} className="mr-1" />
                              Ver Detalhes
                            </Button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                  <tfoot>
                    <tr className="border-t border-white/10">
                      <td colSpan={4} className="py-3 text-right text-slate-300 text-xs uppercase font-bold">
                        Resultado = Faturamento − (CPV + Pessoal + Admin + Outras)
                      </td>
                      <td className="py-3 text-right font-bold text-amber-300 font-mono">
                        {formatBRL(kpis.resultado)}
                      </td>
                      <td />
                    </tr>
                  </tfoot>
                </table>
              </div>

              {filiais.length > 1 && (
                <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-3">
                  {filiais.map((f) => (
                    <div
                      key={f.empresaCodigo}
                      className="rounded-lg border border-slate-800 bg-white/[0.03] p-3 space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-semibold text-white">{f.empresaNome}</p>
                        <Badge variant="outline" className="text-[10px] border-white/10 text-slate-400">
                          {f.empresaCodigo}
                        </Badge>
                      </div>
                      {(f.despesasPorCategoria || []).map((c) => (
                        <button
                          key={c.categoriaKey || c.categoria}
                          type="button"
                          disabled={(c.qtd_lancamentos || 0) === 0}
                          onClick={() => setSelectedCat({ filial: f, cat: c })}
                          className={cn(
                            "w-full flex justify-between text-xs rounded-md px-2 py-1.5 border border-transparent",
                            (c.qtd_lancamentos || 0) > 0
                              ? "hover:border-cyan-500/40 hover:bg-cyan-500/[0.06] cursor-pointer"
                              : "opacity-50 cursor-default"
                          )}
                        >
                          <span className="text-slate-400 truncate pr-2">{c.categoria}</span>
                          <span className="font-mono text-slate-200 shrink-0">
                            {formatBRL(c.valor || 0)}
                          </span>
                        </button>
                      ))}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {projectionEnabled ? (
            <div className="space-y-3 pt-2 border-t border-slate-800">
              <p className="text-[10px] uppercase tracking-widest text-violet-300/80 font-bold">
                Projeção (secundário) — Realizado + Projetado
              </p>
              <MonthRunRateCard projection={monthProjection} formatBRL={formatBRL} />
              <ProjectionExplainCard
                mode={monthProjection.mode}
                hasD30={Boolean(d30Audit?.consolidado)}
              />
            </div>
          ) : null}
            </>
          )}
        </div>
      ) : (
        <Card className="border-slate-800 bg-slate-900/90">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Fila de Conciliação</CardTitle>
              <CardDescription>Despesas aguardando classificação departamental</CardDescription>
            </div>
            <Badge variant="outline" className="text-yellow-500 border-yellow-500/20">
              {facts.length} Pendentes
            </Badge>
          </CardHeader>
          <CardContent>
            {facts.length === 0 ? (
              <div className="py-16 text-center flex flex-col items-center gap-3">
                <CheckCircle2 size={48} className="text-green-500" />
                <h3 className="text-xl font-bold text-white">Tudo em dia!</h3>
                <p className="text-slate-400">Sem pendências no período filtrado.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {facts.slice(0, 20).map((fact) => (
                  <div
                    key={fact.factId}
                    className="flex items-center justify-between gap-3 rounded-md border border-slate-800 bg-white/[0.03] px-3 py-2"
                  >
                    <div className="min-w-0">
                      <p className="text-sm text-white truncate">{fact.description}</p>
                      <p className="text-[11px] text-slate-300">
                        {fact.companyName} • {fact.supplier || "—"}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="font-mono text-sm text-amber-300">
                        {formatBRL(fact.amount)}
                      </span>
                      <Button
                        size="sm"
                        onClick={() => setClassifyOpen(true)}
                        disabled={!writesAllowed}
                        title={!writesAllowed ? "Modo local offline — escrita desabilitada" : undefined}
                      >
                        Classificar
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {selectedCat ? (
        <ExpenseDetailModal
          key={`${selectedCat.filial.empresaCodigo}-${selectedCat.cat.categoriaKey}`}
          isOpen
          onClose={() => setSelectedCat(null)}
          empresaCodigo={selectedCat.filial.empresaCodigo}
          empresaNome={selectedCat.filial.empresaNome}
          categoria={selectedCat.cat.categoria}
          categoriaKey={selectedCat.cat.categoriaKey || selectedCat.cat.categoria}
          cardTotal={selectedCat.cat.valor ?? 0}
          periodStart={periodDates.start}
          periodEnd={periodDates.end}
          seedItens={selectedCat.cat.itens || []}
          onReclassified={() => void fetchData()}
        />
      ) : null}

      <ExpenseClassificationModal
        isOpen={classifyOpen}
        onClose={() => setClassifyOpen(false)}
        start={periodDates.start}
        end={periodDates.end}
      />
    </div>
  );
}

const tooltipStyle = {
  background: "#0f172a",
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: 8,
  color: "#e2e8f0",
};

function ClosedPeriodBanner() {
  return (
    <div className="rounded-md border border-slate-700 bg-slate-900/70 px-3 py-2 text-xs text-slate-300">
      Período fechado — exibindo <span className="text-white font-semibold">100% Realizado</span>.
      Projeções desativadas por padrão. Use{" "}
      <span className="text-violet-300">🔮 Simular/Projetar</span> para estimar o fechamento.
    </div>
  );
}

function TopVariancePanel({
  alerts,
  compareLabel,
}: {
  alerts: VarianceAlert[];
  compareLabel: string;
}) {
  if (!alerts.length) {
    return (
      <div className="rounded-md border border-slate-800 bg-slate-900/60 px-3 py-2 text-xs text-slate-400">
        Top 3 Variações do Mês ({compareLabel}): nenhuma anomalia &gt; 20% no período.
      </div>
    );
  }
  return (
    <Card className="border-amber-500/25 bg-amber-500/5">
      <CardHeader className="pb-2 pt-3 px-4">
        <CardTitle className="text-sm text-amber-100 flex items-center gap-2">
          <AlertTriangle size={14} className="text-amber-300" />
          Top 3 Variações do Mês · vs {compareLabel}
        </CardTitle>
        <CardDescription className="text-[11px]">
          Contas/grupos com |Δ%| &gt; 20% — leitura imediata para o diretor
        </CardDescription>
      </CardHeader>
      <CardContent className="px-4 pb-3 flex flex-wrap gap-2">
        {alerts.map((a) => (
          <Badge
            key={a.key}
            className={cn(
              "text-[11px] font-medium px-2.5 py-1",
              a.direction === "up"
                ? "bg-amber-500/15 text-amber-100 border-amber-500/30"
                : "bg-rose-500/15 text-rose-100 border-rose-500/30"
            )}
          >
            {a.badge}
          </Badge>
        ))}
      </CardContent>
    </Card>
  );
}

function DeltaChip({
  delta,
  compareLabel,
  formatBRL,
  invert,
}: {
  delta: DeltaBlock;
  compareLabel: string;
  formatBRL: (v: number) => string;
  invert?: boolean;
}) {
  const bad =
    delta.deltaPct != null &&
    (invert ? delta.deltaPct > 0 : delta.deltaPct < 0);
  return (
    <span
      className={cn(
        "inline-flex flex-col items-end gap-0.5 text-[10px] font-mono",
        delta.anomaly
          ? bad
            ? "text-rose-300"
            : "text-amber-200"
          : bad
            ? "text-rose-300/80"
            : "text-emerald-300/80"
      )}
      title={`vs ${compareLabel}`}
    >
      <span>
        {formatDeltaRs(delta.deltaRs, formatBRL)} · {formatDeltaPct(delta.deltaPct)}
      </span>
      <span className="text-[9px] text-slate-500 uppercase tracking-wider">vs {compareLabel}</span>
    </span>
  );
}

function ProjectionExplainCard({
  mode,
  hasD30,
}: {
  mode: MonthProjectionResult["mode"];
  hasD30: boolean;
}) {
  const method =
    mode === "d30_moving_avg"
      ? "Média móvel ponderada dos últimos 30 dias (D-30) + sazonalidade de dia da semana"
      : mode === "month_blend"
        ? "Blend D-30 + run-rate do mês corrente + sazonalidade de dia da semana"
        : "Run-rate do mês corrente com ajuste de sazonalidade de dia da semana";
  const confidenceBase = hasD30
    ? "Base auditável: janela D-30 + período realizado até D-1"
    : "Base auditável: período realizado (D-30 indisponível — projeção conservadora)";
  return (
    <Card className="border-violet-500/25 bg-violet-500/5">
      <CardContent className="py-3 px-4 flex flex-col sm:flex-row sm:items-center gap-3 justify-between">
        <div className="space-y-1">
          <p className="text-[10px] uppercase tracking-widest text-violet-300 font-bold">
            Explicabilidade da projeção
          </p>
          <p className="text-xs text-slate-200">
            <span className="text-slate-400">Método utilizado:</span> {method}
          </p>
        </div>
        <Badge className="bg-emerald-500/15 text-emerald-200 border-emerald-500/30 text-[10px] whitespace-nowrap">
          Confiança · {confidenceBase}
        </Badge>
      </CardContent>
    </Card>
  );
}

function MonthRunRateCard({
  projection,
  formatBRL,
}: {
  projection: MonthProjectionResult;
  formatBRL: (v: number) => string;
}) {
  return (
    <Card className="border-slate-800 bg-slate-900/90">
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <TrendingUp size={16} className="text-sky-300" />
          Projeção de Fechamento do Mês
        </CardTitle>
        <CardDescription>
          {projection.mode === "d30_moving_avg"
            ? `Média móvel D-30 × ${projection.daysInMonth} dias`
            : projection.mode === "month_blend"
              ? `Híbrido D-30 + mês corrente × ${projection.daysInMonth} dias`
              : `Run-rate do mês × ${projection.daysInMonth} dias`}
          {" • "}
          {projection.elapsed} dia(s) apurado(s)
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {projection.warning ? (
          <p className="text-[11px] text-amber-200/90 border border-amber-500/25 bg-amber-500/5 rounded-md px-3 py-2">
            {projection.warning}
          </p>
        ) : null}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
            <p className="text-[10px] uppercase tracking-wider text-slate-300 font-bold">
              Faturamento projetado
            </p>
            <p className="text-xl font-mono font-bold text-emerald-400 mt-1">
              {formatBRL(projection.fatProj)}
            </p>
            <p className="text-[11px] text-slate-300 mt-1">
              Período filtrado: {formatBRL(projection.fatMtd)}
            </p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
            <p className="text-[10px] uppercase tracking-wider text-slate-300 font-bold">
              Despesas projetadas
            </p>
            <p className="text-xl font-mono font-bold text-amber-300 mt-1">
              {formatBRL(projection.despProj)}
            </p>
            <p className="text-[11px] text-slate-300 mt-1">
              Período filtrado: {formatBRL(projection.despMtd)}
            </p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
            <p className="text-[10px] uppercase tracking-wider text-slate-300 font-bold">
              Resultado líquido estimado
            </p>
            <p
              className={cn(
                "text-xl font-mono font-bold mt-1",
                projection.resProj < 0 ? "text-rose-400" : "text-sky-300"
              )}
            >
              {formatBRL(projection.resProj)}
            </p>
            <p className="text-[11px] text-slate-300 mt-1">
              Resultado do período:{" "}
              <span
                className={cn(
                  "font-semibold",
                  projection.resMtd < 0 ? "text-rose-400" : "text-white"
                )}
              >
                {formatBRL(projection.resMtd)}
              </span>
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function Kpi({
  label,
  value,
  icon,
  highlight,
  badges,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  highlight?: boolean;
  badges?: React.ReactNode;
}) {
  return (
    <Card className="border-slate-800 bg-slate-900/90 p-4">
      <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-slate-300 font-bold">
        {icon}
        {label}
      </div>
      <p
        className={cn(
          "text-xl font-bold font-mono mt-2",
          highlight ? "text-red-400" : "text-white"
        )}
      >
        {value}
      </p>
      {badges ? <div className="mt-2 flex flex-wrap gap-1.5">{badges}</div> : null}
    </Card>
  );
}

function TabButton({
  active,
  onClick,
  icon,
  label,
  badge,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  badge?: number;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-all",
        active
          ? "bg-blue-600 text-white shadow-lg shadow-blue-900/20"
          : "text-slate-400 hover:text-white hover:bg-white/5"
      )}
    >
      {icon}
      {label}
      {badge !== undefined && badge > 0 ? (
        <span
          className={cn(
            "ml-1 px-1.5 py-0.5 text-[10px] rounded-full font-bold",
            active ? "bg-white/20 text-white" : "bg-slate-800 text-slate-400"
          )}
        >
          {badge}
        </span>
      ) : null}
    </button>
  );
}

function EmptyChart() {
  return (
    <div className="h-full grid place-items-center text-sm text-slate-300">
      Sem dados de vendas no período.
    </div>
  );
}
