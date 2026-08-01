"use client";

import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { Droplet, Thermometer, RefreshCcw, AlertTriangle } from "lucide-react";
import {
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart,
  Line,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { GlobalFilterHeader } from "@/components/executive/global-filter-header";
import { useGlobalFilter } from "@/contexts/global-filter-context";
import { apiService, TankData } from "@/lib/api";
import { cn } from "@/lib/utils";
import { InventoryPredictionPanel } from "@/components/operational/inventory-prediction-panel";

interface FetchState {
  tanks: TankData[];
  loading: boolean;
  error: string | null;
}

export default function OperationalTanksPage() {
  const [state, setState] = useState<FetchState>({
    tanks: [],
    loading: true,
    error: null,
  });
  const mountedRef = useRef(true);

  const { selectedFilial, isConsolidated, periodDates, filialLabel } = useGlobalFilter();

  const fetchTanks = useCallback(async () => {
    console.log("[Tanks] Iniciando fetch...", { start: periodDates.start, end: periodDates.end, filial: selectedFilial });
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const response = await apiService.getOperationalTanks(
        periodDates.start,
        periodDates.end,
        isConsolidated ? undefined : selectedFilial
      );
      console.log("[Tanks] Resposta recebida:", response);
      if (mountedRef.current) {
        setState({ tanks: response.tanks || [], loading: false, error: null });
      }
    } catch (err) {
      console.error("[Tanks] Erro no fetch:", err);
      if (mountedRef.current) {
        setState({
          tanks: [],
          loading: false,
          error: err instanceof Error ? err.message : "Erro ao carregar dados",
        });
      }
    }
  }, [periodDates.start, periodDates.end, isConsolidated, selectedFilial]);

  useEffect(() => {
    mountedRef.current = true;
    fetchTanks();
    return () => {
      mountedRef.current = false;
    };
  }, [fetchTanks]);

  const { tanks, loading, error } = state;

  const filteredTanks = useMemo(() => {
    if (isConsolidated) return tanks;
    return tanks.filter((t) => t.empresa_codigo === selectedFilial);
  }, [tanks, selectedFilial, isConsolidated]);

  const summary = useMemo(() => {
    const criticos = filteredTanks.filter((t) => t.status === "CRITICO").length;
    const suspeitos = filteredTanks.filter((t) => t.status === "DESVIO_SUSPEITO").length;
    const totalDesvio = filteredTanks.reduce((sum, t) => sum + t.physical_var, 0);
    const totalTermico = filteredTanks.reduce((sum, t) => sum + t.thermal_var, 0);
    return { criticos, suspeitos, totalDesvio, totalTermico };
  }, [filteredTanks]);

  const renderSkeleton = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-40 bg-slate-900" />
        ))}
      </div>
      <Skeleton className="h-[400px] bg-slate-900" />
    </div>
  );

  const renderEmptyState = () => (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="grid size-16 place-items-center rounded-full bg-slate-800 mb-4">
        <AlertTriangle size={32} className="text-slate-500" />
      </div>
      <h3 className="text-lg font-medium text-white mb-2">Sem Registro no Período</h3>
      <p className="text-sm text-slate-400 max-w-md">
        Não há dados de tanques disponíveis para <strong>{filialLabel}</strong> no período
        selecionado. Verifique se existem medições registradas na API do WebPosto.
      </p>
    </div>
  );

  return (
    <div className="p-4 lg:p-8 max-w-[1400px] mx-auto space-y-6">
      <header className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Monitoramento de Tanques
          </h1>
          <p className="text-slate-500 text-sm">
            Variação térmica (Física) vs Desvios Reais na Pista — Dados Reais WebPosto
          </p>
        </div>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={fetchTanks} 
          disabled={loading}
          className="bg-cyan-500/10 border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20 hover:text-cyan-200"
        >
          <RefreshCcw size={14} className={cn("mr-2 text-cyan-400", loading && "animate-spin")} />
          Atualizar
        </Button>
      </header>

      <GlobalFilterHeader />

      {/* Modulo de Previsao de Compras */}
      {!isConsolidated && selectedFilial && (
        <InventoryPredictionPanel
          empresaCodigo={selectedFilial}
          empresaNome={filialLabel}
        />
      )}

      {isConsolidated && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {[5555, 11495, 74014].map((codigo) => (
            <InventoryPredictionPanel
              key={codigo}
              empresaCodigo={codigo}
            />
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-4 text-red-200">
          {error}
        </div>
      )}

      {loading ? (
        renderSkeleton()
      ) : filteredTanks.length === 0 ? (
        renderEmptyState()
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {filteredTanks.map((tank, idx) => (
              <TankMiniCard key={`tank-${tank.id}-${tank.empresa_codigo}-${idx}`} tank={tank} />
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="lg:col-span-2 border-white/5 bg-slate-900/40">
              <CardHeader>
                <CardTitle className="text-lg text-white">
                  Análise de Perdas Reais vs Térmicas
                </CardTitle>
                <CardDescription>
                  Diferença entre o que a física explica e o que de fato sumiu (L)
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[400px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={filteredTanks}>
                      <CartesianGrid
                        strokeDasharray="3 3"
                        vertical={false}
                        strokeOpacity={0.1}
                      />
                      <XAxis
                        dataKey="name"
                        fontSize={11}
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#94a3b8" }}
                      />
                      <YAxis
                        fontSize={11}
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#94a3b8" }}
                      />
                      <Tooltip
                        contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b" }}
                        itemStyle={{ fontSize: "12px" }}
                      />
                      <Legend />
                      <Bar
                        dataKey="thermal_var"
                        name="Variação Térmica (Física)"
                        fill="#3b82f6"
                        radius={[4, 4, 0, 0]}
                      />
                      <Bar
                        dataKey="physical_var"
                        name="Desvio Total (L)"
                        fill="#f43f5e"
                        radius={[4, 4, 0, 0]}
                      />
                      <Line
                        type="monotone"
                        dataKey="temp"
                        name="Temp. Méd (ºC)"
                        stroke="#fbbf24"
                        strokeWidth={2}
                        dot={{ r: 4 }}
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
                <div className="mt-4 p-4 rounded-lg bg-slate-900 border border-white/5">
                  <p className="text-xs text-slate-400 leading-relaxed">
                    <span className="font-bold text-blue-500">Nota ANP:</span> A variação térmica é
                    calculada com base no coeficiente de dilatação do combustível a 20ºC. Desvios
                    que excedem a linha térmica e a margem de 0.6% de tolerância são marcados como{" "}
                    <span className="text-red-500 font-bold uppercase">Desvios Suspeitos</span>.
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="lg:col-span-1 border-white/5 bg-slate-900/40">
              <CardHeader>
                <CardTitle className="text-lg text-white">Status de Integridade</CardTitle>
                <CardDescription>
                  {summary.criticos} críticos • {summary.suspeitos} suspeitos
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {filteredTanks
                  .sort((a, b) => Math.abs(b.physical_var) - Math.abs(a.physical_var))
                  .map((tank, idx) => (
                    <div
                      key={`status-${tank.id}-${tank.empresa_codigo}-${idx}`}
                      className="flex items-center justify-between p-3 rounded-lg border border-white/5 bg-slate-50/5 dark:bg-slate-900/50"
                    >
                      <div className="space-y-1">
                        <p className="text-sm font-bold text-white">{tank.name}</p>
                        <p className="text-[10px] text-slate-500">{tank.fuel}</p>
                      </div>
                      <div className="text-right">
                        <p
                          className={cn(
                            "text-sm font-mono font-bold",
                            tank.physical_var < 0 ? "text-red-500" : "text-green-500"
                          )}
                        >
                          {tank.physical_var > 0 ? "+" : ""}
                          {tank.physical_var} L
                        </p>
                        <Badge
                          variant={
                            tank.status === "NORMAL"
                              ? "default"
                              : tank.status === "CRITICO"
                                ? "destructive"
                                : "secondary"
                          }
                          className="text-[9px] h-4"
                        >
                          {tank.status === "SEM_REGISTRO" ? "SEM REGISTRO" : tank.status}
                        </Badge>
                      </div>
                    </div>
                  ))}
                <Button className="w-full" variant="outline">
                  Ver Histórico LMC
                </Button>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

function TankMiniCard({ tank }: { tank: TankData }) {
  const percent = tank.capacity > 0 ? (tank.current / tank.capacity) * 100 : 0;
  const autonomia = tank.autonomia_dias;
  const alerta = tank.alerta_autonomia || "OK";
  const label =
    tank.alerta_label ||
    (alerta === "COMPRA_URGENTE"
      ? "Risco de Ruptura - Pedir Carreta"
      : alerta === "ATENCAO"
        ? "Atenção"
        : "Saudável");

  return (
    <Card className="border-slate-800 bg-slate-900/90">
      <CardContent className="pt-6">
        <div className="flex items-center justify-between mb-3">
          <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
            <Droplet size={20} />
          </div>
          <div className="flex items-center gap-1 text-slate-300">
            <Thermometer size={14} />
            <span className="text-xs font-medium">
              {tank.temp > 0 ? `${tank.temp}ºC` : "N/D"}
            </span>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex justify-between items-end gap-2">
            <p className="text-sm font-bold truncate text-white">{tank.name}</p>
            <p className="text-[10px] text-slate-300 shrink-0">
              {tank.current > 0
                ? `${tank.current.toLocaleString("pt-BR")}L / ${tank.capacity.toLocaleString("pt-BR")}L`
                : "SEM REGISTRO"}
            </p>
          </div>

          {tank.fuel ? (
            <p className="text-[10px] text-slate-300 truncate">{tank.fuel}</p>
          ) : null}

          <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
            <div
              className={cn(
                "h-full transition-all",
                percent < 15 ? "bg-rose-500" : percent < 30 ? "bg-amber-500" : "bg-emerald-500"
              )}
              style={{ width: `${Math.min(100, Math.max(0, percent))}%` }}
            />
          </div>

          <div className="rounded-md border border-slate-800 bg-slate-950/50 px-2 py-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-300">
                Autonomia
              </span>
              <span
                className={cn(
                  "text-sm font-mono font-bold",
                  autonomia != null && autonomia < 1.5
                    ? "text-rose-400"
                    : autonomia != null && autonomia < 3
                      ? "text-amber-400"
                      : "text-emerald-400"
                )}
              >
                {autonomia != null && autonomia < 900
                  ? `${autonomia.toFixed(1)} dias`
                  : "—"}
              </span>
            </div>
            {tank.consumo_medio_diario ? (
              <p className="text-[10px] text-slate-300 mt-0.5">
                Média 7d: {tank.consumo_medio_diario.toLocaleString("pt-BR")} L/dia
              </p>
            ) : null}
            <Badge
              variant="outline"
              className={cn(
                "mt-1.5 text-[9px] h-auto py-0.5 whitespace-normal text-left",
                alerta === "COMPRA_URGENTE" &&
                  "border-rose-500/40 bg-rose-500/10 text-rose-300",
                alerta === "ATENCAO" &&
                  "border-amber-500/40 bg-amber-500/10 text-amber-300",
                alerta === "OK" &&
                  "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
              )}
            >
              {alerta === "COMPRA_URGENTE"
                ? "🔴 "
                : alerta === "ATENCAO"
                  ? "🟡 "
                  : "🟢 "}
              {label}
            </Badge>
          </div>

          <div className="rounded-md border border-slate-800 bg-slate-950/40 px-2 py-1.5 space-y-1">
            <p className="text-[10px] uppercase font-bold tracking-wider text-slate-300">
              Auditoria Físico × Contábil
            </p>
            <div className="flex justify-between text-[10px] text-slate-300">
              <span>Físico</span>
              <span className="font-mono text-white">
                {(tank.estoque_fisico ?? tank.current).toLocaleString("pt-BR")} L
              </span>
            </div>
            <div className="flex justify-between text-[10px] text-slate-300">
              <span>Contábil</span>
              <span className="font-mono text-white">
                {(tank.estoque_contabil ?? 0).toLocaleString("pt-BR")} L
              </span>
            </div>
            <div className="flex justify-between text-[10px]">
              <span className="text-slate-300">Divergência</span>
              <span
                className={cn(
                  "font-mono font-bold",
                  tank.alerta_variancia ? "text-rose-400" : "text-emerald-400"
                )}
              >
                {(tank.divergencia_litros ?? tank.physical_var ?? 0) > 0 ? "+" : ""}
                {(tank.divergencia_litros ?? tank.physical_var ?? 0).toLocaleString("pt-BR")} L
                {tank.divergencia_pct != null
                  ? ` (${tank.divergencia_pct.toFixed(2)}%)`
                  : ""}
              </span>
            </div>
            {tank.alerta_variancia ? (
              <Badge
                variant="outline"
                className="text-[9px] h-auto py-0.5 whitespace-normal text-left border-rose-500/40 bg-rose-500/10 text-rose-300"
              >
                {tank.alerta_variancia_label ||
                  "Alerta de Auditoria de Variância (Possível Variação Térmica ou Fuga)"}
              </Badge>
            ) : (
              <p className="text-[10px] text-emerald-400">Dentro da tolerância ±0,6%</p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
