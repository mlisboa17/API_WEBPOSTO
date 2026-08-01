"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
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
import { ExpenseClassificationModal } from "@/components/executive/expense-classification-modal";
import { DailyAvgBadge, TrendBadge } from "@/components/executive/trend-badge";
import { ExecutiveBriefing } from "@/components/executive/executive-briefing";
import { useGlobalFilter } from "@/contexts/global-filter-context";
import { apiService } from "@/lib/api";
import { exportDataAuditExcel, exportDataAuditPdf } from "@/lib/export-executive-report";
import { inclusiveDays, percentChange, previousPeriod } from "@/lib/period";
import type {
  DataAuditExpenseCategory,
  DataAuditFilial,
  DataAuditResponse,
  DreLine,
  ReviewableFact,
  SalesCompositionResponse,
} from "@/types/api";
import { cn } from "@/lib/utils";

const FILIAL_ORDER = [5555, 11495, 74014];
const SECTOR_COLORS = ["#3b82f6", "#f97316", "#22c55e", "#a855f7"];
const FUEL_COLORS = ["#3b82f6", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444", "#06b6d4"];

type TabType = "overview" | "dre" | "reconciliation";

export default function ExecutiveFinancialPage() {
  const [tab, setTab] = useState<TabType>("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [audit, setAudit] = useState<DataAuditResponse | null>(null);
  const [prevAudit, setPrevAudit] = useState<DataAuditResponse | null>(null);
  const [composition, setComposition] = useState<SalesCompositionResponse | null>(null);
  const [dreLines, setDreLines] = useState<DreLine[]>([]);
  const [facts, setFacts] = useState<ReviewableFact[]>([]);
  const [classifyOpen, setClassifyOpen] = useState(false);
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
  const empresaCodigo = isConsolidated ? undefined : selectedFilial;

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const prev = previousPeriod(periodDates.start, periodDates.end);
      const [auditRes, prevAuditRes, compositionRes, dre, reviewable] = await Promise.all([
        apiService.getDataAudit(periodDates.start, periodDates.end, empresaCodigo),
        apiService.getDataAudit(prev.start, prev.end, empresaCodigo).catch(() => null),
        apiService.getSalesComposition(periodDates.start, periodDates.end, empresaCodigo),
        apiService
          .getCompleteDre(periodDates.start, periodDates.end, empresaCodigo)
          .catch(() => ({ lines: [] as DreLine[] })),
        apiService
          .getReviewableFacts(periodDates.start, periodDates.end)
          .catch(() => [] as ReviewableFact[]),
      ]);
      setAudit(auditRes);
      setPrevAudit(prevAuditRes);
      setComposition(compositionRes);
      setDreLines(dre?.lines || []);
      setFacts(Array.isArray(reviewable) ? reviewable : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar painel financeiro");
    } finally {
      setLoading(false);
    }
  }, [periodDates.start, periodDates.end, empresaCodigo]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

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
    const desp = Number(
      c.despesasTotal ??
        filiais.reduce((s, f) => s + (f.despesasTotal || 0), 0)
    );
    const resultado = Number(
      c.resultadoOperacionalDiario ??
        filiais.reduce((s, f) => s + (f.resultadoOperacionalDiario || 0), 0)
    );
    let cpv = 0;
    let pessoal = 0;
    let admin = 0;
    let outras = 0;
    for (const f of filiais) {
      for (const cat of f.despesasPorCategoria || []) {
        const key = (cat.categoriaKey || "").toUpperCase();
        const val = Number(cat.valor || 0);
        if (key === "CPV") cpv += val;
        else if (key === "PESSOAL") pessoal += val;
        else if (key === "ADMINISTRATIVA") admin += val;
        else outras += val;
      }
    }
    const margemBruta = fat - cpv;
    return { fat, desp, resultado, cpv, pessoal, admin, outras, margemBruta };
  }, [audit?.consolidado, filiais]);

  const dias = inclusiveDays(periodDates.start, periodDates.end);
  const prevCons = prevAudit?.consolidado || {};
  const trendFat = percentChange(kpis.fat, Number(prevCons.faturamentoTotal || 0));
  const trendDesp = percentChange(kpis.desp, Number(prevCons.despesasTotal || 0));
  const trendRes = percentChange(
    kpis.resultado,
    Number(prevCons.resultadoOperacionalDiario || 0)
  );

  const monthProjection = useMemo(() => {
    const today = new Date();
    const daysInMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0).getDate();
    // Run-rate: média diária do período filtrado (ex.: D-1) × dias do mês corrente
    const elapsed = Math.max(1, dias);
    const avgFat = kpis.fat / elapsed;
    const avgDesp = kpis.desp / elapsed;
    const avgRes = kpis.resultado / elapsed;
    return {
      daysInMonth,
      elapsed,
      fatMtd: kpis.fat,
      despMtd: kpis.desp,
      resMtd: kpis.resultado,
      fatProj: avgFat * daysInMonth,
      despProj: avgDesp * daysInMonth,
      resProj: avgRes * daysInMonth,
    };
  }, [dias, kpis.fat, kpis.desp, kpis.resultado]);

  const sectorChart = useMemo(() => {
    const sectors = composition?.compositionBySector || [];
    if (sectors.length) {
      return sectors.map((s) => ({
        name: s.setor || "Setor",
        value: Number(s.faturamento || 0),
      }));
    }
    const summary = composition?.summary;
    if (!summary) return [];
    return [
      { name: "Combustível", value: Number(summary.faturamentoCombustivel || 0) },
      { name: "Pista", value: Number(summary.faturamentoProdutosPista || 0) },
      { name: "Conveniência", value: Number(summary.faturamentoConveniencia || 0) },
    ].filter((x) => x.value > 0);
  }, [composition]);

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
        filiais: DataAuditFilial[];
        sampleFilial?: DataAuditFilial;
        sampleCat?: DataAuditExpenseCategory;
      }
    >();
    for (const f of filiais) {
      for (const cat of f.despesasPorCategoria || []) {
        const key = cat.categoriaKey || cat.categoria;
        const prev = map.get(key) || {
          key,
          label: cat.categoria,
          valor: 0,
          qtd: 0,
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
    return Array.from(map.values());
  }, [filiais]);

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
            onClick={() => void fetchData()}
            disabled={loading}
            className="bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20"
          >
            <RefreshCcw size={14} className={cn("mr-2", loading && "animate-spin")} />
            Atualizar
          </Button>
        </div>
      </header>

      <GlobalFilterHeader />

      <ExecutiveBriefing empresaCodigo={empresaCodigo} />

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
          active={tab === "reconciliation"}
          onClick={() => setTab("reconciliation")}
          icon={<CheckCircle2 size={16} />}
          label="Conciliação"
          badge={facts.length}
        />
      </div>

      {loading ? (
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
          <MonthRunRateCard projection={monthProjection} formatBRL={formatBRL} />

          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
            <Kpi
              label="Faturamento Total"
              value={formatBRL(kpis.fat)}
              icon={<Wallet className="text-emerald-400" size={16} />}
              badges={
                <>
                  <DailyAvgBadge value={kpis.fat / dias} format={formatBRL} />
                  <TrendBadge value={trendFat} />
                </>
              }
            />
            <Kpi
              label="Margem Bruta"
              value={formatBRL(kpis.margemBruta)}
              icon={<TrendingUp className="text-cyan-400" size={16} />}
              badges={<DailyAvgBadge value={kpis.margemBruta / dias} format={formatBRL} />}
            />
            <Kpi
              label="CPV"
              value={formatBRL(kpis.cpv)}
              icon={<Package className="text-violet-400" size={16} />}
            />
            <Kpi
              label="Total Despesas"
              value={formatBRL(kpis.desp)}
              icon={<Receipt className="text-amber-400" size={16} />}
              badges={<TrendBadge value={trendDesp} invert />}
            />
            <Kpi
              label="Resultado Líquido"
              value={formatBRL(kpis.resultado)}
              icon={<TrendingDown className="text-rose-400" size={16} />}
              highlight={kpis.resultado < 0}
              badges={<TrendBadge value={trendRes} />}
            />
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            <Card className="border-slate-800 bg-slate-900/90">
              <CardHeader className="pb-2">
                <CardTitle className="text-base text-white flex items-center gap-2">
                  <Fuel className="text-blue-400" size={18} />
                  Vendas por Setor
                </CardTitle>
                <CardDescription>Participação no faturamento do período</CardDescription>
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
                      <th className="text-right py-2 font-bold">Ação</th>
                    </tr>
                  </thead>
                  <tbody>
                    {planoRows.map((row) => {
                      const clickable = row.qtd > 0 && !!row.sampleCat && !!row.sampleFilial;
                      return (
                        <tr
                          key={row.key}
                          className="border-b border-slate-800 hover:bg-white/[0.02]"
                        >
                          <td className="py-3 pr-3 text-slate-200">{row.label}</td>
                          <td className="py-3 pr-3 text-right text-slate-400 font-mono">
                            {row.qtd}
                          </td>
                          <td className="py-3 pr-3 text-right font-semibold text-white font-mono">
                            {formatBRL(row.valor)}
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
                      <td colSpan={2} className="py-3 text-right text-slate-300 text-xs uppercase font-bold">
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
        </div>
      ) : tab === "dre" ? (
        <div className="space-y-4 animate-in fade-in duration-300">
          <MonthRunRateCard projection={monthProjection} formatBRL={formatBRL} />
          <Card className="border-slate-800 bg-slate-900/90">
            <CardHeader>
              <CardTitle>Demonstrativo de Resultados</CardTitle>
              <CardDescription>
                {filialShortLabel} • {periodLabel}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <DrePanel
                lines={dreLines}
                onInspectPending={() => setTab("reconciliation")}
                pendingCount={facts.length}
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
                      <Button size="sm" onClick={() => setClassifyOpen(true)}>
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

function MonthRunRateCard({
  projection,
  formatBRL,
}: {
  projection: {
    daysInMonth: number;
    elapsed: number;
    fatMtd: number;
    despMtd: number;
    resMtd: number;
    fatProj: number;
    despProj: number;
    resProj: number;
  };
  formatBRL: (v: number) => string;
}) {
  return (
    <Card className="border-slate-800 bg-slate-900/90">
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <TrendingUp size={16} className="text-sky-300" />
          Projeção de Fechamento do Mês (Run-Rate)
        </CardTitle>
        <CardDescription>
          Média diária do período × {projection.daysInMonth} dias do mês • base{" "}
          {projection.elapsed} dia(s) apurado(s) até ontem
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
            <p className="text-[10px] uppercase tracking-wider text-slate-300 font-bold">
              Faturamento projetado
            </p>
            <p className="text-xl font-mono font-bold text-emerald-400 mt-1">
              {formatBRL(projection.fatProj)}
            </p>
            <p className="text-[11px] text-slate-300 mt-1">
              Acumulado: {formatBRL(projection.fatMtd)}
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
              Acumulado: {formatBRL(projection.despMtd)}
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
              Resultado atual acumulado:{" "}
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
