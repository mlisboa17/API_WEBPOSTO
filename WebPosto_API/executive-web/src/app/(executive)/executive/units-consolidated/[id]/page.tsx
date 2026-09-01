"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import {
  AlertTriangle,
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  Lightbulb,
  RefreshCcw,
} from "lucide-react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ExpenseDetailModal } from "@/components/executive/expense-detail-modal";
import { apiService } from "@/lib/api";
import type {
  ExpenseDetailsResponse,
  UnitsPerformanceCategoria,
  UnitsPerformanceDetailResponse,
} from "@/types/api";
import { cn } from "@/lib/utils";

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

export default function UnitDetailPage() {
  return (
    <Suspense
      fallback={
        <div className="p-4 lg:p-8 max-w-[1400px] mx-auto space-y-4">
          <Skeleton className="h-10 w-64 bg-slate-900" />
          <Skeleton className="h-40 w-full bg-slate-900" />
        </div>
      }
    >
      <UnitDetailPageContent />
    </Suspense>
  );
}

function UnitDetailPageContent() {
  const params = useParams();
  const search = useSearchParams();
  const unidadeId = Number(params.id);
  const start =
    search.get("start") || new Date().toISOString().slice(0, 10);
  const end = search.get("end") || start;

  const [data, setData] = useState<UnitsPerformanceDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [lancamentos, setLancamentos] = useState<
    Record<string, ExpenseDetailsResponse | "loading" | "error">
  >({});
  const [modalCat, setModalCat] = useState<UnitsPerformanceCategoria | null>(null);

  const fetchData = useCallback(async () => {
    if (!Number.isFinite(unidadeId)) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiService.getUnitPerformanceDetail(unidadeId, start, end);
      setData(res);
      if (res.success === false && res.mensagem) setError(res.mensagem);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar unidade");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [unidadeId, start, end]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  const loadCategory = async (cat: UnitsPerformanceCategoria) => {
    const key = cat.categoriaKey || cat.categoria;
    if (expanded === key) {
      setExpanded(null);
      return;
    }
    setExpanded(key);
    if (lancamentos[key] && lancamentos[key] !== "error") return;
    setLancamentos((prev) => ({ ...prev, [key]: "loading" }));
    try {
      const details = await apiService.getExpenseDetails(
        start,
        end,
        key,
        unidadeId
      );
      setLancamentos((prev) => ({ ...prev, [key]: details }));
    } catch {
      setLancamentos((prev) => ({ ...prev, [key]: "error" }));
    }
  };

  const u = data?.unidade;
  const chart = useMemo(
    () =>
      (data?.evolucao_mensal || []).map((p) => ({
        label: p.label,
        Galonagem: p.galonagem_litros,
        Faturamento: p.faturamento_total_rs,
        Despesas: p.despesas_totais_rs ?? undefined,
        Margem: p.margem_operacional_pct ?? undefined,
      })),
    [data?.evolucao_mensal]
  );

  if (loading && !data) {
    return (
      <div className="p-4 lg:p-8 max-w-[1400px] mx-auto space-y-4">
        <Skeleton className="h-10 w-64 bg-slate-900" />
        <Skeleton className="h-40 w-full bg-slate-900" />
        <Skeleton className="h-64 w-full bg-slate-900" />
      </div>
    );
  }

  return (
    <div className="p-4 lg:p-8 max-w-[1400px] mx-auto space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link
            href={`/executive/units-consolidated`}
            className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-sky-300 mb-2"
          >
            <ArrowLeft size={12} /> Voltar ao consolidado
          </Link>
          <h1 className="text-2xl font-semibold text-slate-100">
            {u?.nome_unidade || `Unidade ${unidadeId}`}
          </h1>
          <p className="text-sm text-slate-500">
            {start} → {end} · ID {unidadeId}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {u ? (
            <Badge className={cn("border text-xs", statusTone(u.status_operacional))}>
              {u.status_operacional}
            </Badge>
          ) : null}
          <Button size="sm" variant="outline" onClick={() => void fetchData()}>
            <RefreshCcw size={14} className={cn("mr-1.5", loading && "animate-spin")} />
            Atualizar
          </Button>
        </div>
      </div>

      {error ? (
        <Card className="border-amber-500/30 bg-amber-500/5 p-4 text-amber-200 text-sm">
          <AlertTriangle className="inline mr-2" size={14} />
          {error}
        </Card>
      ) : null}

      {u ? (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          <Mini label="Galonagem" value={litros(u.galonagem_litros)} />
          <Mini label="Faturamento" value={brl(u.faturamento_total_rs)} />
          <Mini label="Despesas" value={brl(u.despesas_totais_rs)} tone="rose" />
          <Mini
            label="Resultado Op."
            value={brl(u.resultado_operacional_rs)}
            tone={u.resultado_operacional_rs >= 0 ? "emerald" : "rose"}
          />
          <Mini
            label="Margem Op."
            value={`${(u.margem_operacional_pct ?? u.margem_percentual).toFixed(1)}%`}
          />
        </div>
      ) : null}

      {(data?.insights?.length || 0) > 0 && (
        <Card className="border-sky-500/20 bg-sky-950/20">
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-sm text-sky-200 flex items-center gap-2">
              <Lightbulb size={14} /> Insights
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4 space-y-1">
            {data?.insights?.map((t, i) => (
              <p key={i} className="text-sm text-slate-300">
                • {t}
              </p>
            ))}
          </CardContent>
        </Card>
      )}

      {(data?.desvios?.length || 0) > 0 && (
        <Card className="border-rose-500/25 bg-rose-950/20">
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-sm text-rose-200">Análise de desvios</CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4 space-y-2">
            {data?.desvios?.map((d, i) => (
              <p key={i} className="text-sm text-rose-100/90">
                ⚠ {d.mensagem}{" "}
                <span className="text-slate-400">
                  ({brl(d.valor_rs)} vs média {brl(d.media_rede_rs)})
                </span>
              </p>
            ))}
          </CardContent>
        </Card>
      )}

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-sm text-slate-200">
            Evolução mensal (12 meses) — Galonagem & Faturamento
          </CardTitle>
          <p className="text-xs text-slate-500">
            Despesas/margem preenchidas no mês corrente do período selecionado.
          </p>
        </CardHeader>
        <CardContent className="h-72 px-2 pb-4">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chart}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="label" stroke="#64748b" fontSize={10} />
              <YAxis
                yAxisId="rs"
                stroke="#64748b"
                fontSize={10}
                tickFormatter={(v) =>
                  v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)
                }
              />
              <YAxis
                yAxisId="l"
                orientation="right"
                stroke="#06b6d4"
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
              />
              <Legend />
              <Line
                yAxisId="rs"
                type="monotone"
                dataKey="Faturamento"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={false}
              />
              <Line
                yAxisId="l"
                type="monotone"
                dataKey="Galonagem"
                stroke="#06b6d4"
                strokeWidth={2}
                dot={false}
              />
              <Line
                yAxisId="rs"
                type="monotone"
                dataKey="Despesas"
                stroke="#ef4444"
                strokeWidth={2}
                strokeDasharray="4 4"
                connectNulls={false}
                dot
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-sm text-slate-200">
            Despesas por categoria
          </CardTitle>
          <p className="text-xs text-slate-500">
            Clique para expandir lançamentos individuais.
          </p>
        </CardHeader>
        <CardContent className="px-0 pb-2">
          <ul className="divide-y divide-slate-800">
            {(data?.despesas_por_categoria || []).map((cat) => {
              const key = cat.categoriaKey || cat.categoria;
              const open = expanded === key;
              const payload = lancamentos[key];
              return (
                <li key={key}>
                  <button
                    type="button"
                    className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-900/70 text-left"
                    onClick={() => void loadCategory(cat)}
                  >
                    <span className="flex items-center gap-2 text-sm text-slate-200">
                      {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      {cat.categoria}
                      <span className="text-[10px] text-slate-500">
                        {cat.qtd_lancamentos} lanç.
                      </span>
                    </span>
                    <span className="tabular-nums text-rose-200 text-sm">
                      {brl(cat.valor)}
                    </span>
                  </button>
                  {open ? (
                    <div className="px-4 pb-3 bg-slate-950/80">
                      {payload === "loading" ? (
                        <p className="text-xs text-slate-500 py-2">Carregando…</p>
                      ) : payload === "error" ? (
                        <p className="text-xs text-rose-400 py-2">
                          Falha ao carregar lançamentos.
                        </p>
                      ) : payload && typeof payload === "object" ? (
                        <div className="space-y-2">
                          <div className="flex justify-end">
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-7 text-xs"
                              onClick={() => setModalCat(cat)}
                            >
                              Abrir modal completo
                            </Button>
                          </div>
                          <div className="max-h-56 overflow-y-auto space-y-1">
                            {(payload.itens || []).slice(0, 40).map((item, idx) => (
                              <div
                                key={item.id || idx}
                                className="flex justify-between gap-3 text-xs border-b border-slate-800/60 py-1.5"
                              >
                                <div className="min-w-0">
                                  <p className="text-slate-300 truncate">
                                    {item.historico || item.descricao || "—"}
                                  </p>
                                  <p className="text-slate-550 text-slate-500">
                                    {item.dataPagamento || "—"} ·{" "}
                                    {item.fornecedor || item.favorecido || "—"}
                                  </p>
                                </div>
                                <span className="tabular-nums text-slate-200 shrink-0">
                                  {brl(item.valor ?? 0)}
                                </span>
                              </div>
                            ))}
                            {(payload.itens || []).length === 0 ? (
                              <p className="text-xs text-slate-500 py-2">
                                Sem lançamentos detalhados nesta categoria.
                              </p>
                            ) : null}
                          </div>
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </li>
              );
            })}
            {(data?.despesas_por_categoria || []).length === 0 ? (
              <li className="px-4 py-6 text-sm text-slate-500 text-center">
                Nenhuma despesa categorizada no período.
              </li>
            ) : null}
          </ul>
        </CardContent>
      </Card>

      {modalCat && u ? (
        <ExpenseDetailModal
          isOpen
          onClose={() => setModalCat(null)}
          empresaCodigo={u.unidade_id}
          empresaNome={u.nome_unidade}
          categoria={modalCat.categoria}
          categoriaKey={modalCat.categoriaKey || modalCat.categoria}
          cardTotal={modalCat.valor}
          periodStart={start}
          periodEnd={end}
        />
      ) : null}
    </div>
  );
}

function Mini({
  label,
  value,
  tone = "sky",
}: {
  label: string;
  value: string;
  tone?: "sky" | "rose" | "emerald";
}) {
  const map = {
    sky: "text-sky-300",
    rose: "text-rose-300",
    emerald: "text-emerald-300",
  };
  return (
    <Card className="border-slate-800 bg-slate-950/60">
      <CardContent className="p-3">
        <p className="text-[10px] uppercase tracking-wider text-slate-500">{label}</p>
        <p className={cn("text-lg font-semibold tabular-nums mt-0.5", map[tone])}>
          {value}
        </p>
      </CardContent>
    </Card>
  );
}
