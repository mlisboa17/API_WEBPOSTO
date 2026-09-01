"use client";

import React, { useEffect, useState, useMemo, useCallback } from "react";
import {
  TrendingUp,
  RefreshCcw,
  ShoppingCart,
  Droplet,
  AlertTriangle,
  Fuel,
  Wrench,
  Store,
  Percent,
} from "lucide-react";
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  BarChart,
  Bar,
  Legend,
  PieChart,
  Pie,
  ComposedChart,
  Line,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { GlobalFilterHeader } from "@/components/executive/global-filter-header";
import { PriceElasticitySimulator } from "@/components/executive/price-elasticity-simulator";
import { DailyAvgBadge, TrendBadge } from "@/components/executive/trend-badge";
import { InfoTooltip } from "@/components/ui/info-tooltip";
import { useGlobalFilter } from "@/contexts/global-filter-context";
import {
  isConvenienciaEmMigracao,
  isFoodServiceAffinity,
} from "@/config/filiais_config";
import { apiService } from "@/lib/api";
import { percentChange, previousPeriod } from "@/lib/period";
import { cn } from "@/lib/utils";
import type { SalesCompositionResponse } from "@/types/api";

interface HourlyVolume {
  hora: number;
  litros: number;
  ticket_medio: number;
}

interface ElasticityPoint {
  data: string;
  preco_bomba_rs: number;
  volume_litros: number;
  margem_bruta_rs: number;
}

interface AffinityCombo {
  produtos: string[];
  frequencia_conjunta_pct: number;
  ticket_medio_combo: number;
  margem_contribuicao_total_rs: number;
  lift: number;
}

interface CompositionItem {
  categoria: string;
  litros: number;
  faturamento_rs: number;
  margem_rs: number;
  participacao_pct: number;
}

interface SectorShare {
  setor: string;
  faturamento_rs: number;
  participacao_pct: number;
}

interface SalesComposition {
  combustiveis: CompositionItem[];
  produtos_pista: CompositionItem[];
  conveniencia: CompositionItem[];
  participacao_setores: SectorShare[];
  penetracao_cross_selling_pct: number;
  faturamento_total_rs: number;
  empresa_codigo?: number | null;
}

interface BicoPerf {
  bico: number;
  bomba: string;
  produto: string;
  litros: number;
  abastecimentos: number;
  faturamento: number;
  empresa_codigo?: number | null;
}

interface SalesAnalyticsData {
  heatmap: { data: Record<string, HourlyVolume[]> };
  elasticidade: ElasticityPoint[];
  coeficiente_elasticidade: number;
  cesta_afinidade: AffinityCombo[];
  taxa_conversao_pista_loja_pct: number;
  volume_medio_diario_litros?: number;
  composicao?: SalesComposition;
  performance_bicos?: BicoPerf[];
}

const WEEK_DAYS = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
const HOURS = Array.from({ length: 24 }, (_, i) => i);
const FUEL_COLORS = ["#3b82f6", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444", "#06b6d4", "#94a3b8"];
const PISTA_COLORS = ["#f97316", "#eab308", "#84cc16", "#14b8a6", "#a855f7"];
const CONV_COLORS = ["#38bdf8", "#fb7185", "#c084fc", "#34d399", "#fbbf24"];
const SECTOR_COLORS = ["#3b82f6", "#f97316", "#22c55e"];

export default function SalesAnalyticsPage() {
  const [data, setData] = useState<SalesAnalyticsData | null>(null);
  const [composition, setComposition] = useState<SalesCompositionResponse | null>(null);
  const [prevComposition, setPrevComposition] = useState<SalesCompositionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { selectedFilial, isConsolidated, periodDates, periodLabel, filialShortLabel } =
    useGlobalFilter();

  const empresaCodigo = isConsolidated ? undefined : selectedFilial;

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setData(null);
      setComposition(null);
      setError(null);
      const prev = previousPeriod(periodDates.start, periodDates.end);
      const [analyticsResult, compositionResult, prevComp] = await Promise.all([
        apiService.getSalesAnalytics(
          periodDates.start,
          periodDates.end,
          empresaCodigo
        ) as Promise<SalesAnalyticsData>,
        apiService.getSalesComposition(
          periodDates.start,
          periodDates.end,
          empresaCodigo
        ),
        apiService.getSalesComposition(prev.start, prev.end, empresaCodigo).catch(() => null),
      ]);
      setData(analyticsResult);
      setComposition(compositionResult);
      setPrevComposition(prevComp);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erro ao carregar analytics";
      setError(message);
      setData(null);
      setComposition(null);
      setPrevComposition(null);
    } finally {
      setLoading(false);
    }
  }, [periodDates.start, periodDates.end, empresaCodigo]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  const heatmapData = useMemo(() => {
    if (!data?.heatmap?.data) return [];
    return Object.entries(data.heatmap.data).flatMap(([day, hours]) =>
      (hours || []).map((h) => ({ ...h, day: Number(day) }))
    );
  }, [data]);

  const maxVolume = useMemo(() => {
    if (heatmapData.length === 0) return 0;
    return Math.max(...heatmapData.map((d) => d.litros || 0));
  }, [heatmapData]);

  const elasticityData = useMemo(() => {
    if (!data?.elasticidade?.length) return [];
    const sorted = [...data.elasticidade].sort((a, b) =>
      String(a.data).localeCompare(String(b.data))
    );
    return sorted.map((point, idx) => {
      const prev = idx > 0 ? sorted[idx - 1] : null;
      const vol = point.volume_litros || 0;
      const prevVol = prev?.volume_litros || 0;
      const variacaoPct =
        prev && prevVol > 0 ? ((vol - prevVol) / prevVol) * 100 : null;
      const label = String(point.data || "").slice(5); // MM-DD
      return {
        ...point,
        label: label || point.data,
        volume: vol,
        preco: point.preco_bomba_rs || 0,
        margem: point.margem_bruta_rs || 0,
        variacaoPct,
      };
    });
  }, [data]);

  const emMigracaoConveniencia = isConvenienciaEmMigracao(empresaCodigo);

  const affinity = useMemo(() => {
    const raw = data?.cesta_afinidade || [];
    if (!emMigracaoConveniencia) return raw;
    // Loja legada: ocultar cestas Food Service até a virada do ERP.
    return raw.filter((combo) => !isFoodServiceAffinity(combo.produtos));
  }, [data?.cesta_afinidade, emMigracaoConveniencia]);

  const summary = composition?.summary;
  const funnel = composition?.crossSellingFunnel;
  const penetracaoPista =
    summary?.penetracaoProdutosPistaPercentual ??
    funnel?.penetracaoProdutosPistaPercentual ??
    0;
  /** Em migração: score de cross-selling foca em Combustível + Produtos de Pista. */
  const conversionRate = emMigracaoConveniencia
    ? penetracaoPista
    : summary?.penetracaoCrossSellingPercentual ??
      funnel?.penetracaoTotalPercentual ??
      data?.composicao?.penetracao_cross_selling_pct ??
      data?.taxa_conversao_pista_loja_pct ??
      0;
  const legacyComposition = data?.composicao;

  const diasNoPeriodo = useMemo(() => {
    const start = new Date(`${periodDates.start}T12:00:00`);
    const end = new Date(`${periodDates.end}T12:00:00`);
    const ms = Math.abs(end.getTime() - start.getTime());
    return Math.max(1, Math.floor(ms / 86_400_000) + 1);
  }, [periodDates.start, periodDates.end]);

  const volumeTotalPeriodo = useMemo(() => {
    const fromSummary = Number(summary?.litrosVendidos || 0);
    if (fromSummary > 0) return fromSummary;
    if (heatmapData.length > 0) {
      return heatmapData.reduce((sum, d) => sum + (d.litros || 0), 0);
    }
    return 0;
  }, [summary?.litrosVendidos, heatmapData]);

  const volumeMedioDiario = useMemo(() => {
    if (volumeTotalPeriodo > 0) {
      return volumeTotalPeriodo / diasNoPeriodo;
    }
    return Number(data?.volume_medio_diario_litros || 0);
  }, [volumeTotalPeriodo, diasNoPeriodo, data?.volume_medio_diario_litros]);

  const faturamentoCombustivel = Number(
    summary?.faturamentoCombustivel || summary?.faturamentoTotal || 0
  );

  const trendVolume = percentChange(
    volumeTotalPeriodo,
    Number(prevComposition?.summary?.litrosVendidos || 0)
  );
  const trendFat = percentChange(
    faturamentoCombustivel,
    Number(
      prevComposition?.summary?.faturamentoCombustivel ||
        prevComposition?.summary?.faturamentoTotal ||
        0
    )
  );

  const formatVolume = (litros: number) => {
    if (litros >= 1000) return `${(litros / 1000).toFixed(1)}k L`;
    return `${litros.toFixed(0)} L`;
  };

  /** Exibição exata do volume total (ex: 5.562 L), sem abreviar para k. */
  const formatVolumeExact = (litros: number) =>
    `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(litros || 0)} L`;

  const formatBRL = (val: number) =>
    new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(val || 0);

  const hasData =
    heatmapData.some((d) => d.litros > 0) ||
    elasticityData.length > 0 ||
    affinity.length > 0 ||
    (summary?.faturamentoTotal ?? 0) > 0 ||
    (legacyComposition?.faturamento_total_rs || 0) > 0;

  const getHeatColor = (volume: number) => {
    const intensity = maxVolume > 0 ? volume / maxVolume : 0;
    if (intensity > 0.8) return "bg-blue-500";
    if (intensity > 0.6) return "bg-blue-500/70";
    if (intensity > 0.4) return "bg-blue-400/50";
    if (intensity > 0.2) return "bg-blue-300/30";
    return "bg-blue-200/10";
  };

  const fuelChartData = (
    composition?.combustiveis?.length
      ? composition.combustiveis
      : (legacyComposition?.combustiveis || []).map((i) => ({
          categoria: i.categoria,
          litros: i.litros,
          faturamento: i.faturamento_rs,
          participacao: i.participacao_pct,
        }))
  ).map((i) => ({
    name: i.categoria,
    litros: i.litros ?? 0,
    faturamento: i.faturamento ?? 0,
  }));

  const pistaChartData = (
    composition?.produtosPista?.length
      ? composition.produtosPista
      : (legacyComposition?.produtos_pista || []).map((i) => ({
          categoria: i.categoria,
          faturamento: i.faturamento_rs,
          participacao: i.participacao_pct,
          litros: 0,
        }))
  ).map((i) => ({
    name: i.categoria,
    faturamento: i.faturamento ?? 0,
    margem: (i.faturamento ?? 0) * 0.35,
  }));

  const convChartData = emMigracaoConveniencia
    ? []
    : (
        composition?.conveniencia?.length
          ? composition.conveniencia
          : (legacyComposition?.conveniencia || []).map((i) => ({
              categoria: i.categoria,
              faturamento: i.faturamento_rs,
              participacao: i.participacao_pct,
            }))
      ).map((i) => ({
        name: i.categoria,
        value: i.faturamento ?? 0,
        margem: (i.faturamento ?? 0) * 0.28,
      }));

  const sectorSharesRaw =
    composition?.compositionBySector?.map((s) => ({
      setor: s.setor,
      faturamento_rs: s.faturamento ?? 0,
      participacao_pct: s.participacao ?? 0,
    })) ||
    legacyComposition?.participacao_setores ||
    [];

  /** Em migração: participação só sobre Combustíveis + Produtos de Pista. */
  const sectorShares = emMigracaoConveniencia
    ? (() => {
        const pistaOnly = sectorSharesRaw.filter(
          (s) => !/conveni/i.test(String(s.setor || ""))
        );
        const total = pistaOnly.reduce((acc, s) => acc + (s.faturamento_rs || 0), 0);
        return pistaOnly.map((s) => ({
          ...s,
          participacao_pct:
            total > 0 ? ((s.faturamento_rs || 0) / total) * 100 : 0,
        }));
      })()
    : sectorSharesRaw;

  return (
    <div className="p-4 lg:p-8 max-w-[1600px] mx-auto space-y-6">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className="bg-blue-500/10 text-blue-400 border-blue-500/20">
              S54
            </Badge>
            <span className="text-[10px] text-slate-300 uppercase tracking-widest font-bold">
              Analytics
            </span>
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Vendas & Elasticidade</h1>
          <p className="text-slate-400 text-sm">
            Composição setorial, heatmap e elasticidade • {filialShortLabel} • {periodLabel}
          </p>
        </div>
        <Button
          size="sm"
          onClick={() => void fetchData()}
          disabled={loading}
          className="bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20 hover:text-cyan-200"
        >
          <RefreshCcw size={14} className={cn("mr-2 text-cyan-400", loading && "animate-spin")} />{" "}
          Atualizar
        </Button>
      </header>

      <GlobalFilterHeader />

      {loading ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-32 w-full" />
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-[280px] w-full" />
            ))}
          </div>
          <Skeleton className="h-[400px] w-full" />
        </div>
      ) : error ? (
        <div className="p-8 text-center">
          <h2 className="text-xl text-red-500 font-bold mb-2">{error}</h2>
          <Button
            onClick={() => void fetchData()}
            className="bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20"
          >
            Tentar Novamente
          </Button>
        </div>
      ) : (
        <div
          key={`sales-${empresaCodigo ?? "all"}-${periodDates.start}-${periodDates.end}`}
          className="space-y-6 animate-in fade-in duration-500"
        >
          {!hasData && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="grid size-16 place-items-center rounded-full bg-slate-800 mb-4">
                <AlertTriangle size={32} className="text-slate-300" />
              </div>
              <h3 className="text-lg font-medium text-white mb-2">Sem Registro no Período</h3>
              <p className="text-sm text-slate-400 max-w-md">
                Não há dados de vendas disponíveis para {filialShortLabel} no período selecionado.
              </p>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4">
            <KpiCard
              icon={<Droplet className="text-emerald-400" />}
              title="Volume Total Vendido"
              value={volumeTotalPeriodo > 0 ? formatVolumeExact(volumeTotalPeriodo) : "0 L"}
              subValue={`${formatBRL(faturamentoCombustivel)} • ${filialShortLabel}`}
              tooltip="Acumulado de litros e faturamento de combustível no período filtrado (empresaCodigo + datas)."
              emphasize
              badges={
                <>
                  <DailyAvgBadge
                    value={volumeMedioDiario}
                    format={(n) => `${formatVolumeExact(n).replace(" L", "")} L/dia`}
                  />
                  <TrendBadge value={trendVolume} />
                </>
              }
            />
            <KpiCard
              icon={<Fuel className="text-blue-400" />}
              title="Faturamento Combustível"
              value={formatBRL(faturamentoCombustivel)}
              subValue={`Média diária ${formatBRL(faturamentoCombustivel / diasNoPeriodo)}`}
              tooltip="Faturamento de combustível no período filtrado."
              badges={
                <>
                  <DailyAvgBadge
                    value={faturamentoCombustivel / diasNoPeriodo}
                    format={(n) => formatBRL(n)}
                  />
                  <TrendBadge value={trendFat} />
                </>
              }
            />
            <KpiCard
              icon={<Fuel className="text-cyan-400" />}
              title="Abastecimentos (Pista)"
              value={summary?.quantidadeAbastecimentos ?? 0}
              subValue={`Ticket médio ${formatBRL(summary?.ticketMedioAbastecimento ?? 0)}`}
              tooltip="COUNT DISTINCT de abastecimentoCodigo via /INTEGRACAO/ABASTECIMENTO — não usa notas fiscais."
            />
            <KpiCard
              icon={<TrendingUp className="text-green-500" />}
              title="Coeficiente de Elasticidade"
              value={data?.coeficiente_elasticidade ?? 0}
              subValue="Impacto preço x volume"
              tooltip="Sensibilidade das vendas às variações de preço na bomba."
            />
            <KpiCard
              icon={<ShoppingCart className="text-orange-500" />}
              title={emMigracaoConveniencia ? "Cross-Selling Pista" : "Cross-Selling Total"}
              value={conversionRate > 0 ? `${Number(conversionRate).toFixed(1)}%` : "0,00%"}
              subValue={
                emMigracaoConveniencia
                  ? `Combustível + Produtos de Pista • Loja em migração`
                  : `Pista ${(funnel?.penetracaoProdutosPistaPercentual ?? 0).toFixed(1)}% • Loja ${(funnel?.penetracaoConvenienciaPercentual ?? 0).toFixed(1)}%`
              }
              tooltip={
                emMigracaoConveniencia
                  ? "Score focado em Combustíveis + Produtos de Pista (Água Retornável, Lubrificantes, ARLA 32, Fluídos). Dados da loja estão no ERP legado."
                  : "Penetração = (abastecimentos com produto de pista ou conveniência) / total de abastecimentos × 100."
              }
            />
          </div>

          <Card className="border-slate-800 bg-slate-900/90">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Percent size={18} className="text-cyan-400" />
                Participação Setorial & Funil de Cross-Selling
              </CardTitle>
              <CardDescription>
                Base operacional: {summary?.quantidadeAbastecimentos ?? 0} abastecimentos
                {composition?.fonteAbastecimentos
                  ? ` • fonte ${composition.fonteAbastecimentos}`
                  : ""}
                {composition?.fallback ? " • fallback ativo" : ""}
                {emMigracaoConveniencia
                  ? " • score de loja suspenso (migração ERP)"
                  : ""}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {emMigracaoConveniencia && <ConvenienciaMigracaoBanner />}
              <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
                {sectorShares.map((s, idx) => (
                  <div
                    key={s.setor}
                    className="rounded-lg border border-slate-800 bg-white/5 p-4"
                  >
                    <p className="text-[10px] uppercase tracking-widest text-slate-300 font-bold">
                      {s.setor}
                    </p>
                    <p className="text-2xl font-bold text-white mt-1">
                      {(s.participacao_pct ?? 0).toFixed(1)}%
                    </p>
                    <p className="text-xs text-slate-400 mt-1">{formatBRL(s.faturamento_rs || 0)}</p>
                    <div className="mt-3 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${Math.min(s.participacao_pct || 0, 100)}%`,
                          backgroundColor: SECTOR_COLORS[idx % SECTOR_COLORS.length],
                        }}
                      />
                    </div>
                  </div>
                ))}
                <div className="rounded-lg border border-cyan-500/20 bg-cyan-500/5 p-4">
                  <p className="text-[10px] uppercase tracking-widest text-cyan-400 font-bold">
                    {emMigracaoConveniencia
                      ? "Penetração Cross-Selling (Pista)"
                      : "Penetração Cross-Selling"}
                  </p>
                  <p className="text-2xl font-bold text-cyan-300 mt-1">
                    {Number(conversionRate).toFixed(1)}%
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    {emMigracaoConveniencia ? (
                      <>
                        Pista {penetracaoPista.toFixed(1)}% · Loja{" "}
                        <span className="text-amber-400/90">em migração</span>
                      </>
                    ) : (
                      <>
                        Pista {(summary?.penetracaoProdutosPistaPercentual ?? 0).toFixed(1)}% · Loja{" "}
                        {(summary?.penetracaoConvenienciaPercentual ?? 0).toFixed(1)}%
                      </>
                    )}
                  </p>
                  <p className="text-[11px] text-slate-300 mt-3">
                    {emMigracaoConveniencia
                      ? `Faturamento pista: ${formatBRL(
                          (summary?.faturamentoCombustivel ?? 0) +
                            (summary?.faturamentoProdutosPista ?? 0)
                        )}`
                      : `Total unidade: ${formatBRL(summary?.faturamentoTotal ?? 0)}`}
                  </p>
                </div>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-[11px]">
                <FunnelStat
                  label="Abastecimentos"
                  value={String(funnel?.totalAbastecimentos ?? summary?.quantidadeAbastecimentos ?? 0)}
                />
                <FunnelStat
                  label="Clientes Loja"
                  value={
                    emMigracaoConveniencia
                      ? "—"
                      : String(funnel?.clientesLoja ?? summary?.clientesLoja ?? 0)
                  }
                />
                <FunnelStat
                  label="Combustível + Pista"
                  value={String(funnel?.transacoesCombustivelProdutoPista ?? 0)}
                />
                <FunnelStat
                  label="Combustível + Conveniência"
                  value={
                    emMigracaoConveniencia
                      ? "Migração"
                      : String(funnel?.transacoesCombustivelConveniencia ?? 0)
                  }
                />
              </div>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Card className="border-slate-800 bg-slate-900/90">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Fuel size={16} className="text-blue-400" />
                  Vendas de Combustíveis
                </CardTitle>
                <CardDescription>Volume (L) e faturamento (R$) por tipo</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[260px] w-full">
                  {fuelChartData.length === 0 ? (
                    <EmptyChart />
                  ) : (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={fuelChartData} margin={{ top: 8, right: 8, left: 0, bottom: 40 }}>
                        <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.1} />
                        <XAxis
                          dataKey="name"
                          tick={{ fill: "#94a3b8", fontSize: 10 }}
                          interval={0}
                          angle={-25}
                          textAnchor="end"
                          height={50}
                        />
                        <YAxis yAxisId="l" tick={{ fill: "#94a3b8", fontSize: 10 }} />
                        <YAxis
                          yAxisId="r"
                          orientation="right"
                          tick={{ fill: "#94a3b8", fontSize: 10 }}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#0f172a",
                            border: "1px solid rgba(255,255,255,0.1)",
                            borderRadius: 8,
                          }}
                          formatter={(value, name) => {
                            const n = String(name);
                            const v = Number(value || 0);
                            if (n === "litros") return [`${v.toFixed(0)} L`, "Volume"];
                            return [formatBRL(v), "Faturamento"];
                          }}
                        />
                        <Legend />
                        <Bar yAxisId="l" dataKey="litros" name="Litros" radius={[4, 4, 0, 0]}>
                          {fuelChartData.map((_, i) => (
                            <Cell key={`fuel-l-${i}`} fill={FUEL_COLORS[i % FUEL_COLORS.length]} />
                          ))}
                        </Bar>
                        <Bar
                          yAxisId="r"
                          dataKey="faturamento"
                          name="R$"
                          fill="#64748b"
                          radius={[4, 4, 0, 0]}
                          opacity={0.7}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-800 bg-slate-900/90">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Wrench size={16} className="text-orange-400" />
                  Produtos de Pista (Não Combustível)
                </CardTitle>
                <CardDescription>Aditivos, lubrificantes, fluídos e afins</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[260px] w-full">
                  {pistaChartData.length === 0 ? (
                    <EmptyChart />
                  ) : (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={pistaChartData} margin={{ top: 8, right: 8, left: 0, bottom: 40 }}>
                        <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.1} />
                        <XAxis
                          dataKey="name"
                          tick={{ fill: "#94a3b8", fontSize: 10 }}
                          interval={0}
                          angle={-20}
                          textAnchor="end"
                          height={50}
                        />
                        <YAxis tick={{ fill: "#94a3b8", fontSize: 10 }} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#0f172a",
                            border: "1px solid rgba(255,255,255,0.1)",
                            borderRadius: 8,
                          }}
                          formatter={(value, name) => [
                            formatBRL(Number(value || 0)),
                            String(name) === "margem" ? "Margem" : "Faturamento",
                          ]}
                        />
                        <Legend />
                        <Bar dataKey="faturamento" name="Faturamento" radius={[4, 4, 0, 0]}>
                          {pistaChartData.map((_, i) => (
                            <Cell key={`pista-${i}`} fill={PISTA_COLORS[i % PISTA_COLORS.length]} />
                          ))}
                        </Bar>
                        <Bar dataKey="margem" name="Margem" fill="#22c55e" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-800 bg-slate-900/90">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Store size={16} className="text-emerald-400" />
                  Loja de Conveniência
                </CardTitle>
                <CardDescription>
                  {emMigracaoConveniencia
                    ? "Integração ERP em migração — dados no sistema local"
                    : "Participação por categoria de loja"}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {emMigracaoConveniencia && <ConvenienciaMigracaoBanner />}
                <div className="h-[260px] w-full">
                  {emMigracaoConveniencia ? (
                    <div className="h-full flex flex-col items-center justify-center text-center px-4 gap-2">
                      <Store size={28} className="text-amber-400/70" />
                      <p className="text-sm text-slate-300">
                        Métricas de loja suspensas até a virada do webPosto.
                      </p>
                      <p className="text-xs text-slate-500 max-w-xs">
                        Performance do posto continua baseada em Combustíveis e Produtos de Pista.
                      </p>
                    </div>
                  ) : convChartData.length === 0 ? (
                    <EmptyChart />
                  ) : (
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={convChartData}
                          dataKey="value"
                          nameKey="name"
                          cx="50%"
                          cy="45%"
                          innerRadius={48}
                          outerRadius={78}
                          paddingAngle={2}
                        >
                          {convChartData.map((_, i) => (
                            <Cell key={`conv-${i}`} fill={CONV_COLORS[i % CONV_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#0f172a",
                            border: "1px solid rgba(255,255,255,0.1)",
                            borderRadius: 8,
                          }}
                          formatter={(value, name) => [formatBRL(Number(value || 0)), String(name)]}
                        />
                        <Legend />
                      </PieChart>
                    </ResponsiveContainer>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          <Card className="border-slate-800 bg-slate-900/90">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Droplet size={18} className="text-blue-500" />
                Heatmap de Galonagem
              </CardTitle>
              <CardDescription>
                Volume de litros por dia da semana e horário ({filialShortLabel}).
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <div className="min-w-[700px]">
                  <div className="grid grid-cols-[60px_repeat(24,_1fr)] gap-0.5">
                    <div className="text-[10px] font-bold text-slate-300 uppercase"></div>
                    {HOURS.map((h) => (
                      <div key={h} className="text-[9px] text-center text-slate-300 font-mono">
                        {h}h
                      </div>
                    ))}
                    {WEEK_DAYS.map((day, dayIndex) => (
                      <React.Fragment key={day}>
                        <div className="text-[11px] font-bold text-slate-400 flex items-center justify-center h-8">
                          {day}
                        </div>
                        {HOURS.map((h) => {
                          const point = heatmapData.find((d) => d.day === dayIndex && d.hora === h);
                          const volume = point?.litros || 0;
                          const ticket = point?.ticket_medio || 0;
                          const isPeak = maxVolume > 0 && volume / maxVolume > 0.6;
                          return (
                            <div
                              key={`${day}-${h}`}
                              className={cn(
                                "h-8 rounded-[2px] cursor-pointer transition-all hover:ring-1 hover:ring-white/50 relative group",
                                getHeatColor(volume)
                              )}
                            >
                              <HeatmapPopover
                                day={day}
                                dayIndex={dayIndex}
                                hour={h}
                                volume={volume}
                                ticket={ticket}
                                isPeak={isPeak}
                                formatBRL={formatBRL}
                              />
                            </div>
                          );
                        })}
                      </React.Fragment>
                    ))}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-800 bg-slate-900/90">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Fuel size={18} className="text-sky-400" />
                Performance por Bico / Bomba
              </CardTitle>
              <CardDescription>
                Ranking do período • produto, volume (L) e quantidade de abastecimentos
              </CardDescription>
            </CardHeader>
            <CardContent>
              {(data?.performance_bicos || []).length === 0 ? (
                <p className="text-sm text-slate-300 text-center py-8">
                  Sem identificação de bico nos abastecimentos do período.
                </p>
              ) : (
                <div className="overflow-x-auto rounded-md border border-slate-800">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-[10px] uppercase tracking-wider text-slate-300 border-b border-slate-800 bg-slate-950/50">
                        <th className="text-left py-2 px-3">#</th>
                        <th className="text-left py-2 px-3">Bico</th>
                        <th className="text-left py-2 px-3">Bomba</th>
                        <th className="text-left py-2 px-3">Produto</th>
                        <th className="text-right py-2 px-3">Volume (L)</th>
                        <th className="text-right py-2 px-3">Abastecimentos</th>
                        <th className="text-right py-2 px-3">Faturamento</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(data?.performance_bicos || []).slice(0, 12).map((b, i) => (
                        <tr
                          key={`${b.bico}-${b.produto}-${i}`}
                          className="border-b border-slate-800/80 hover:bg-white/[0.02]"
                        >
                          <td className="py-2 px-3 text-slate-400">{i + 1}</td>
                          <td className="py-2 px-3 font-mono font-bold text-sky-300">
                            {b.bico || "—"}
                          </td>
                          <td className="py-2 px-3 text-slate-200">{b.bomba || "—"}</td>
                          <td className="py-2 px-3 text-white truncate max-w-[180px]">
                            {b.produto}
                          </td>
                          <td className="py-2 px-3 text-right font-mono text-emerald-400">
                            {Number(b.litros).toLocaleString("pt-BR", {
                              maximumFractionDigits: 0,
                            })}
                          </td>
                          <td className="py-2 px-3 text-right font-mono text-white">
                            {b.abastecimentos}
                          </td>
                          <td className="py-2 px-3 text-right font-mono text-amber-300">
                            {formatBRL(b.faturamento)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>

          <PriceElasticitySimulator
            empresaCodigo={empresaCodigo}
            filialLabel={filialShortLabel}
          />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="border-slate-800 bg-slate-900/90">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <TrendingUp size={18} className="text-amber-400" />
                  Elasticidade: Volume × Preço × Margem
                </CardTitle>
                <CardDescription>
                  Barras verdes = volume (L) · Linha dourada = preço (R$/L) · Linha roxa = margem bruta (R$)
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[350px] w-full">
                  {elasticityData.length === 0 ? (
                    <EmptyChart />
                  ) : (
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart
                        data={elasticityData}
                        margin={{ top: 16, right: 12, bottom: 8, left: 0 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" strokeOpacity={0.5} />
                        <XAxis
                          dataKey="label"
                          fontSize={11}
                          tick={{ fill: "#cbd5e1" }}
                          axisLine={false}
                          tickLine={false}
                        />
                        <YAxis
                          yAxisId="vol"
                          fontSize={11}
                          tick={{ fill: "#86efac" }}
                          axisLine={false}
                          tickLine={false}
                          width={56}
                          tickFormatter={(v) =>
                            Number(v) >= 1000
                              ? `${(Number(v) / 1000).toFixed(1)}k`
                              : String(v)
                          }
                        />
                        <YAxis
                          yAxisId="preco"
                          orientation="right"
                          fontSize={11}
                          tick={{ fill: "#fde68a" }}
                          axisLine={false}
                          tickLine={false}
                          width={48}
                          tickFormatter={(v) => Number(v).toFixed(2)}
                        />
                        {/* Escala própria (oculta) para margem em R$ absolutos */}
                        <YAxis yAxisId="margem" orientation="right" hide />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#0f172a",
                            border: "1px solid #334155",
                            borderRadius: "8px",
                            color: "#f1f5f9",
                          }}
                          labelStyle={{ color: "#f8fafc", fontWeight: 700 }}
                          // eslint-disable-next-line @typescript-eslint/no-explicit-any
                          content={({ active, payload }: any) => {
                            if (!active || !payload?.length) return null;
                            const row = payload[0]?.payload;
                            if (!row) return null;
                            const varTxt =
                              row.variacaoPct == null
                                ? "—"
                                : `${row.variacaoPct >= 0 ? "+" : ""}${row.variacaoPct.toFixed(1)}% vs. dia anterior`;
                            return (
                              <div className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs space-y-1 shadow-xl">
                                <p className="font-bold text-white">Data: {row.data}</p>
                                <p className="text-amber-300">
                                  Preço praticado: R$ {Number(row.preco).toFixed(3)}/L
                                </p>
                                <p className="text-emerald-400">
                                  Volume do dia:{" "}
                                  {Number(row.volume).toLocaleString("pt-BR", {
                                    maximumFractionDigits: 0,
                                  })}{" "}
                                  L
                                </p>
                                <p className="text-cyan-300">
                                  Margem gerada: {formatBRL(Number(row.margem))}
                                </p>
                                <p
                                  className={
                                    row.variacaoPct == null
                                      ? "text-slate-300"
                                      : row.variacaoPct >= 0
                                        ? "text-emerald-400"
                                        : "text-rose-400"
                                  }
                                >
                                  Variação volume: {varTxt}
                                </p>
                              </div>
                            );
                          }}
                        />
                        <Legend wrapperStyle={{ fontSize: "11px", color: "#e2e8f0" }} />
                        <Bar
                          yAxisId="vol"
                          dataKey="volume"
                          name="Volume (L)"
                          fill="#22c55e"
                          radius={[3, 3, 0, 0]}
                          barSize={18}
                        />
                        <Line
                          yAxisId="preco"
                          type="monotone"
                          dataKey="preco"
                          name="Preço (R$/L)"
                          stroke="#fbbf24"
                          strokeWidth={2.5}
                          dot={{ r: 3, fill: "#fbbf24" }}
                        />
                        <Line
                          yAxisId="margem"
                          type="monotone"
                          dataKey="margem"
                          name="Margem Bruta (R$)"
                          stroke="#a78bfa"
                          strokeWidth={2}
                          dot={{ r: 2.5, fill: "#a78bfa" }}
                        />
                      </ComposedChart>
                    </ResponsiveContainer>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-800 bg-slate-900/90">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <ShoppingCart size={18} className="text-orange-500" />
                  Contribuições Mais Lucrativas
                </CardTitle>
                <CardDescription>
                  Cestas de afinidade recalculadas para {filialShortLabel}.
                  {emMigracaoConveniencia
                    ? " Food Service oculto até a migração da loja."
                    : ""}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 max-h-[350px] overflow-y-auto pr-2">
                  {affinity.length === 0 ? (
                    <p className="text-sm text-slate-300 text-center py-10">
                      Nenhuma cesta identificada.
                    </p>
                  ) : (
                    affinity.map((combo, idx) => (
                      <div
                        key={`${filialShortLabel}-${idx}-${combo.produtos.join("-")}`}
                        className="p-3 rounded-lg border border-slate-800 bg-white/5 hover:bg-white/10 transition-colors"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex flex-wrap gap-1">
                            {(combo.produtos || []).map((p, i) => (
                              <span
                                key={i}
                                className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 font-medium"
                              >
                                {p}
                              </span>
                            ))}
                          </div>
                          <Badge
                            variant="outline"
                            className="text-green-500 border-green-500/20 text-[10px]"
                          >
                            +{(combo.lift || 1).toFixed(1)}x Lift
                          </Badge>
                        </div>
                        <div className="grid grid-cols-3 gap-2 text-[11px]">
                          <div className="text-slate-400">
                            <span className="block text-[9px] uppercase tracking-wider">
                              Frequência
                            </span>
                            <span className="font-bold text-white">
                              {(combo.frequencia_conjunta_pct || 0).toFixed(1)}%
                            </span>
                          </div>
                          <div className="text-slate-400">
                            <span className="block text-[9px] uppercase tracking-wider">
                              Ticket Combo
                            </span>
                            <span className="font-bold text-white">
                              {formatBRL(combo.ticket_medio_combo || 0)}
                            </span>
                          </div>
                          <div className="text-slate-400 text-right">
                            <span className="block text-[9px] uppercase tracking-wider">
                              Margem Total
                            </span>
                            <span className="font-bold text-green-500">
                              {formatBRL(combo.margem_contribuicao_total_rs || 0)}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}

function EmptyChart() {
  return (
    <div className="h-full flex items-center justify-center text-sm text-slate-300">
      Sem dados para a filial/período
    </div>
  );
}

function ConvenienciaMigracaoBanner() {
  return (
    <div
      role="status"
      className="rounded-md border border-amber-500/25 bg-amber-500/[0.07] px-3 py-2 text-[11px] leading-snug text-amber-100/90"
    >
      ⏳ Integração ERP Conveniência em Migração • Dados mantidos no sistema local da loja
    </div>
  );
}

function FunnelStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-800 bg-white/[0.03] px-3 py-2">
      <p className="text-[9px] uppercase tracking-wider text-slate-300">{label}</p>
      <p className="text-sm font-bold text-white mt-0.5">{value}</p>
    </div>
  );
}

function KpiCard({
  icon,
  title,
  value,
  subValue,
  tooltip,
  emphasize,
  badges,
}: {
  icon: React.ReactNode;
  title: string;
  value: string | number;
  subValue: string;
  tooltip?: string;
  emphasize?: boolean;
  badges?: React.ReactNode;
}) {
  return (
    <Card
      className={cn(
        "border-slate-800 bg-slate-900/90 p-4",
        emphasize && "border-emerald-500/30 bg-emerald-500/[0.06] md:col-span-1 xl:col-span-1"
      )}
    >
      <div className="flex items-start gap-4">
        <div
          className={cn(
            "p-2.5 rounded-lg bg-white/5",
            emphasize && "bg-emerald-500/15"
          )}
        >
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <p
              className={cn(
                "text-[10px] font-bold uppercase tracking-widest text-slate-300",
                emphasize && "text-emerald-400/90"
              )}
            >
              {title}
            </p>
            {tooltip && <InfoTooltip content={tooltip} />}
          </div>
          <p
            className={cn(
              "text-2xl font-bold font-mono mt-1 text-white",
              emphasize && "text-3xl text-emerald-100"
            )}
          >
            {value}
          </p>
          <p className="text-[11px] text-slate-400 mt-0.5 truncate">{subValue}</p>
          {badges ? <div className="mt-2 flex flex-wrap gap-1.5">{badges}</div> : null}
        </div>
      </div>
    </Card>
  );
}

interface HeatmapPopoverProps {
  day: string;
  dayIndex: number;
  hour: number;
  volume: number;
  ticket: number;
  isPeak: boolean;
  formatBRL: (val: number) => string;
}

function HeatmapPopover({
  day,
  dayIndex,
  hour,
  volume,
  ticket,
  isPeak,
  formatBRL,
}: HeatmapPopoverProps) {
  const openToBottom = dayIndex <= 2;
  const isLeftEdge = hour <= 4;
  const isRightEdge = hour >= 19;

  const getPositionClasses = () => {
    const base = "absolute hidden group-hover:block z-[100] min-w-[180px] max-w-[220px]";
    const verticalPos = openToBottom ? "top-full mt-3" : "bottom-full mb-3";
    let horizontalPos = "left-1/2 -translate-x-1/2";
    if (isLeftEdge) horizontalPos = "left-0";
    else if (isRightEdge) horizontalPos = "right-0";
    return cn(base, verticalPos, horizontalPos);
  };

  return (
    <div className={getPositionClasses()}>
      <div className="bg-slate-900 border border-white/10 rounded-lg shadow-2xl p-3 space-y-2 relative">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
          <span className="text-xs font-bold text-white">
            {day} {hour}h
          </span>
          {isPeak && (
            <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-blue-500/20 text-blue-300 font-bold">
              PICO
            </span>
          )}
        </div>
        <div className="grid grid-cols-2 gap-2 text-[10px]">
          <div>
            <span className="text-slate-300 block">Volume</span>
            <span className="text-white font-bold">{volume.toFixed(0)} L</span>
          </div>
          <div>
            <span className="text-slate-300 block">Ticket Médio</span>
            <span className="text-white font-bold">{formatBRL(ticket)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
