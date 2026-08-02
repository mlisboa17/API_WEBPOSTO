"use client";

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  ArrowDownUp,
  Building2,
  Droplets,
  FileDown,
  FileSpreadsheet,
  Fuel,
  Lightbulb,
  RefreshCcw,
  Search,
  TrendingUp,
  Wallet,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { GlobalFilterHeader } from "@/components/executive/global-filter-header";
import { useGlobalFilter } from "@/contexts/global-filter-context";
import { apiService } from "@/lib/api";
import {
  exportUnitsPerformanceExcel,
  exportUnitsPerformancePdf,
} from "@/lib/export-executive-report";
import { RushHeatmapPanel } from "@/components/executive/rush-heatmap-panel";
import { ForecourtConfigPanel } from "@/components/executive/forecourt-config-panel";
import { ForecourtPlantPanel } from "@/components/executive/forecourt-plant-panel";
import type { UnitsPerformanceResponse, UnitsPerformanceUnidade } from "@/types/api";
import { cn } from "@/lib/utils";

type PageTab = "financeiro" | "rush" | "forecourt" | "planta";

type SortKey =
  | "nome_unidade"
  | "galonagem_litros"
  | "faturamento_total_rs"
  | "despesas_totais_rs"
  | "resultado_operacional_rs"
  | "margem_operacional_pct"
  | "status_operacional";

function brl(n: number) {
  return (n ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function litros(n: number) {
  return `${(n ?? 0).toLocaleString("pt-BR", { maximumFractionDigits: 0 })} L`;
}

function statusTone(s: string) {
  if (s === "EXCELENTE")
    return "bg-emerald-500/15 text-emerald-300 border-emerald-500/40";
  if (s === "ATENCAO") return "bg-amber-500/15 text-amber-300 border-amber-500/40";
  return "bg-rose-500/15 text-rose-300 border-rose-500/40";
}

export default function UnitsConsolidatedPage() {
  const router = useRouter();
  const { periodDates, periodLabel, selectedFilial, isConsolidated } = useGlobalFilter();
  const empresaCodigo = isConsolidated ? undefined : selectedFilial;
  const [tab, setTab] = useState<PageTab>("financeiro");
  const [data, setData] = useState<UnitsPerformanceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busca, setBusca] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("resultado_operacional_rs");
  const [sortAsc, setSortAsc] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiService.getUnitsPerformance(
        periodDates.start,
        periodDates.end
      );
      setData(res);
      if (!res.unidades?.length && res.mensagem) setError(res.mensagem);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar unidades");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [periodDates.start, periodDates.end]);

  useEffect(() => {
    if (tab !== "financeiro") return;
    void fetchData();
  }, [fetchData, tab]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc((v) => !v);
    else {
      setSortKey(key);
      setSortAsc(key === "nome_unidade");
    }
  };

  const rows = useMemo(() => {
    let list = [...(data?.unidades || [])];
    const q = busca.trim().toLowerCase();
    if (q) {
      list = list.filter(
        (u) =>
          u.nome_unidade.toLowerCase().includes(q) ||
          String(u.unidade_id).includes(q)
      );
    }
    list.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (typeof av === "string" && typeof bv === "string") {
        return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
      }
      const an = Number(av ?? 0);
      const bn = Number(bv ?? 0);
      return sortAsc ? an - bn : bn - an;
    });
    return list;
  }, [data?.unidades, busca, sortKey, sortAsc]);

  const chartData = useMemo(
    () =>
      (data?.grafico_barras || data?.unidades || []).map((u) => ({
        nome:
          "nome" in u
            ? (u as { nome: string }).nome.replace("Posto ", "").replace("AP ", "")
            : u.nome_unidade.replace("Posto ", "").replace("AP ", ""),
        id: "unidade_id" in u ? u.unidade_id : (u as UnitsPerformanceUnidade).unidade_id,
        Faturamento: "faturamento" in u ? (u as { faturamento: number }).faturamento : u.faturamento_total_rs,
        Despesas: "despesas" in u ? (u as { despesas: number }).despesas : u.despesas_totais_rs,
        Resultado: "resultado" in u ? (u as { resultado: number }).resultado : u.resultado_operacional_rs,
      })),
    [data]
  );

  const openUnit = (id: number) => {
    router.push(
      `/executive/units-consolidated/${id}?start=${periodDates.start}&end=${periodDates.end}`
    );
  };

  const rede = data?.rede;

  return (
    <div className="p-4 lg:p-8 max-w-[1600px] mx-auto space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-100 flex items-center gap-2">
            <Building2 className="text-sky-400" size={22} />
            Análise Financeira Consolidada
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Margem operacional · Galonagem · Comparativo de unidades · {periodLabel}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="outline"
            className="border-slate-600"
            disabled={!data}
            onClick={() =>
              data &&
              exportUnitsPerformancePdf(data, { periodLabel })
            }
          >
            <FileDown size={14} className="mr-1.5" /> PDF
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="border-slate-600"
            disabled={!data}
            onClick={() => data && exportUnitsPerformanceExcel(data)}
          >
            <FileSpreadsheet size={14} className="mr-1.5" /> Excel
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="border-slate-600"
            onClick={() => void fetchData()}
          >
            <RefreshCcw size={14} className={cn("mr-1.5", loading && "animate-spin")} />
            Atualizar
          </Button>
        </div>
      </header>

      <GlobalFilterHeader />

      <div className="flex gap-1 border-b border-slate-800">
        <button
          type="button"
          onClick={() => setTab("financeiro")}
          className={cn(
            "px-4 py-2 text-sm font-medium rounded-t-md border-b-2 transition-colors",
            tab === "financeiro"
              ? "border-sky-400 text-sky-300 bg-sky-500/5"
              : "border-transparent text-slate-400 hover:text-slate-200"
          )}
        >
          Financeiro consolidado
        </button>
        <button
          type="button"
          onClick={() => setTab("rush")}
          className={cn(
            "px-4 py-2 text-sm font-medium rounded-t-md border-b-2 transition-colors",
            tab === "rush"
              ? "border-orange-400 text-orange-300 bg-orange-500/5"
              : "border-transparent text-slate-400 hover:text-slate-200"
          )}
        >
          🔥 Rush / Mapa de Calor
        </button>
        <button
          type="button"
          onClick={() => setTab("forecourt")}
          className={cn(
            "px-4 py-2 text-sm font-medium rounded-t-md border-b-2 transition-colors",
            tab === "forecourt"
              ? "border-emerald-400 text-emerald-300 bg-emerald-500/5"
              : "border-transparent text-slate-400 hover:text-slate-200"
          )}
        >
          Configuração da Pista
        </button>
        <button
          type="button"
          onClick={() => setTab("planta")}
          className={cn(
            "px-4 py-2 text-sm font-medium rounded-t-md border-b-2 transition-colors",
            tab === "planta"
              ? "border-cyan-400 text-cyan-300 bg-cyan-500/5"
              : "border-transparent text-slate-400 hover:text-slate-200"
          )}
        >
          Planta da Pista
        </button>
      </div>

      {tab === "rush" ? (
        <RushHeatmapPanel empresaCodigo={empresaCodigo} />
      ) : tab === "forecourt" ? (
        <ForecourtConfigPanel empresaCodigo={empresaCodigo} />
      ) : tab === "planta" ? (
        <ForecourtPlantPanel empresaCodigo={empresaCodigo} />
      ) : loading && !data ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-24 bg-slate-900" />
            ))}
          </div>
          <Skeleton className="h-72 bg-slate-900" />
        </div>
      ) : error && !data?.unidades?.length ? (
        <Card className="border-red-500/30 bg-red-500/5 p-8 text-center">
          <AlertTriangle className="mx-auto text-red-400 mb-2" />
          <p className="text-red-300">{error}</p>
          <Button className="mt-4" variant="outline" onClick={() => void fetchData()}>
            Tentar novamente
          </Button>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <Kpi
              icon={<Fuel size={16} />}
              label="Faturamento Rede"
              value={brl(rede?.faturamento_total_rs || 0)}
              sub={litros(rede?.galonagem_total_litros || 0)}
            />
            <Kpi
              icon={<Wallet size={16} />}
              label="Despesas Totais"
              value={brl(rede?.despesas_totais_rs || 0)}
              tone="rose"
            />
            <Kpi
              icon={<TrendingUp size={16} />}
              label="Resultado Operacional"
              value={brl(rede?.resultado_operacional_rs || 0)}
              tone={(rede?.resultado_operacional_rs || 0) >= 0 ? "emerald" : "rose"}
            />
            <Kpi
              icon={<Droplets size={16} />}
              label="Margem Operacional"
              value={`${(rede?.margem_media_pct || 0).toFixed(1)}%`}
              sub={`Meta ${(data?.parametros?.meta_margem_pct ?? 15).toFixed(0)}%`}
              tone={
                (rede?.status_operacional || "") === "EXCELENTE"
                  ? "emerald"
                  : (rede?.status_operacional || "") === "ATENCAO"
                    ? "amber"
                    : "rose"
              }
            />
          </div>

          {(data?.insights?.length || 0) > 0 && (
            <Card className="border-sky-500/20 bg-sky-950/20">
              <CardHeader className="py-3 px-4">
                <CardTitle className="text-sm text-sky-200 flex items-center gap-2">
                  <Lightbulb size={14} /> Insights automáticos
                </CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-4 space-y-1.5">
                {data?.insights?.map((t, i) => (
                  <p key={i} className="text-sm text-slate-300 leading-snug">
                    • {t}
                  </p>
                ))}
              </CardContent>
            </Card>
          )}

          <div className="grid lg:grid-cols-3 gap-4">
            <Card className="lg:col-span-2 border-slate-800 bg-slate-950/50">
              <CardHeader className="py-3 px-4">
                <CardTitle className="text-sm text-slate-200">
                  Comparativo Fat × Despesas × Resultado
                </CardTitle>
              </CardHeader>
              <CardContent className="h-72 px-2 pb-4">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={chartData}
                    onClick={(state) => {
                      const id = (state as { activePayload?: Array<{ payload?: { id?: number } }> })
                        ?.activePayload?.[0]?.payload?.id;
                      if (id) openUnit(id);
                    }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="nome" stroke="#64748b" fontSize={11} />
                    <YAxis
                      stroke="#64748b"
                      fontSize={10}
                      tickFormatter={(v) =>
                        v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)
                      }
                    />
                    <Tooltip
                      contentStyle={{
                        background: "#0f172a",
                        border: "1px solid #334155",
                        borderRadius: 8,
                      }}
                      formatter={(v) => brl(Number(v))}
                    />
                    <Legend />
                    <Bar dataKey="Faturamento" fill="#3b82f6" radius={[4, 4, 0, 0]} cursor="pointer" />
                    <Bar dataKey="Despesas" fill="#ef4444" radius={[4, 4, 0, 0]} cursor="pointer" />
                    <Bar dataKey="Resultado" fill="#22c55e" radius={[4, 4, 0, 0]} cursor="pointer" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <div className="space-y-3">
              <Card className="border-slate-800 bg-slate-950/50">
                <CardHeader className="py-3 px-4">
                  <CardTitle className="text-xs uppercase tracking-wider text-emerald-400">
                    Top lucrativas
                  </CardTitle>
                </CardHeader>
                <CardContent className="px-4 pb-4 space-y-2">
                  {(data?.ranking_mais_lucrativas || []).map((u, i) => (
                    <button
                      key={u.unidade_id}
                      type="button"
                      onClick={() => openUnit(u.unidade_id)}
                      className="w-full flex justify-between text-left text-sm hover:bg-slate-900/80 rounded px-2 py-1.5"
                    >
                      <span className="text-slate-300">
                        {i + 1}. {u.nome_unidade}
                      </span>
                      <span className="text-emerald-300 tabular-nums">
                        {brl(u.resultado_operacional_rs)}
                      </span>
                    </button>
                  ))}
                </CardContent>
              </Card>
              <Card className="border-slate-800 bg-slate-950/50">
                <CardHeader className="py-3 px-4">
                  <CardTitle className="text-xs uppercase tracking-wider text-rose-400">
                    Maior risco / menor margem
                  </CardTitle>
                </CardHeader>
                <CardContent className="px-4 pb-4 space-y-2">
                  {(data?.ranking_maior_risco || []).map((u, i) => (
                    <button
                      key={u.unidade_id}
                      type="button"
                      onClick={() => openUnit(u.unidade_id)}
                      className="w-full flex justify-between text-left text-sm hover:bg-slate-900/80 rounded px-2 py-1.5"
                    >
                      <span className="text-slate-300">
                        {i + 1}. {u.nome_unidade}
                      </span>
                      <Badge className={cn("text-[10px] border", statusTone(u.status_operacional))}>
                        {u.margem_operacional_pct.toFixed(1)}%
                      </Badge>
                    </button>
                  ))}
                </CardContent>
              </Card>
            </div>
          </div>

          <Card className="border-slate-800 bg-slate-950/50">
            <CardHeader className="py-3 px-4 flex flex-row items-center justify-between gap-3">
              <CardTitle className="text-sm text-slate-200">Tabela comparativa</CardTitle>
              <div className="relative">
                <Search
                  size={14}
                  className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500"
                />
                <input
                  value={busca}
                  onChange={(e) => setBusca(e.target.value)}
                  placeholder="Buscar unidade…"
                  className="h-8 w-48 rounded-md border border-slate-700 bg-slate-900 pl-8 pr-2 text-xs text-slate-200"
                />
              </div>
            </CardHeader>
            <CardContent className="px-0 pb-2 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-y border-slate-800 text-[10px] uppercase tracking-wider text-slate-500">
                    {(
                      [
                        ["nome_unidade", "Unidade"],
                        ["galonagem_litros", "Galonagem"],
                        ["faturamento_total_rs", "Faturamento"],
                        ["despesas_totais_rs", "Despesas"],
                        ["resultado_operacional_rs", "Diferença (R$)"],
                        ["margem_operacional_pct", "Margem %"],
                        ["status_operacional", "Status"],
                      ] as [SortKey, string][]
                    ).map(([key, label]) => (
                      <th key={key} className="px-3 py-2 text-left font-medium">
                        <button
                          type="button"
                          className="inline-flex items-center gap-1 hover:text-slate-200"
                          onClick={() => toggleSort(key)}
                        >
                          {label}
                          <ArrowDownUp size={10} className={sortKey === key ? "text-sky-400" : ""} />
                        </button>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((u) => (
                    <tr
                      key={u.unidade_id}
                      className="border-b border-slate-800/80 hover:bg-slate-900/60 cursor-pointer"
                      onClick={() => openUnit(u.unidade_id)}
                    >
                      <td className="px-3 py-2.5 text-slate-100 font-medium">
                        {u.nome_unidade}
                        <span className="block text-[10px] text-slate-500">
                          {u.unidade_id}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 tabular-nums text-cyan-200">
                        {litros(u.galonagem_litros)}
                      </td>
                      <td className="px-3 py-2.5 tabular-nums text-slate-200">
                        {brl(u.faturamento_total_rs)}
                      </td>
                      <td className="px-3 py-2.5 tabular-nums text-rose-200/90">
                        {brl(u.despesas_totais_rs)}
                      </td>
                      <td
                        className={cn(
                          "px-3 py-2.5 tabular-nums font-medium",
                          u.resultado_operacional_rs >= 0
                            ? "text-emerald-300"
                            : "text-rose-300"
                        )}
                      >
                        {brl(u.resultado_operacional_rs)}
                      </td>
                      <td className="px-3 py-2.5 tabular-nums text-slate-200">
                        {(u.margem_operacional_pct ?? u.margem_percentual).toFixed(1)}%
                      </td>
                      <td className="px-3 py-2.5">
                        <Badge className={cn("text-[10px] border", statusTone(u.status_operacional))}>
                          {u.status_operacional}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function Kpi({
  icon,
  label,
  value,
  sub,
  tone = "sky",
}: {
  icon: ReactNode;
  label: string;
  value: string;
  sub?: string;
  tone?: "sky" | "rose" | "emerald" | "amber";
}) {
  const tones = {
    sky: "text-sky-300",
    rose: "text-rose-300",
    emerald: "text-emerald-300",
    amber: "text-amber-300",
  };
  return (
    <Card className="border-slate-800 bg-slate-950/60">
      <CardContent className="p-4">
        <p className="text-[10px] uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
          {icon}
          {label}
        </p>
        <p className={cn("text-xl font-semibold mt-1 tabular-nums", tones[tone])}>{value}</p>
        {sub ? <p className="text-[11px] text-slate-500 mt-0.5">{sub}</p> : null}
      </CardContent>
    </Card>
  );
}
