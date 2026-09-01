"use client";

import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { RefreshCcw, AlertTriangle } from "lucide-react";
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
import {
  TankMonitorCard,
  isGnvProduct,
} from "@/components/operational/tank-monitor-card";
import { empresaNomeOperacional } from "@/utils/filial_normalizer";

const POLL_INTERVAL_MS = 10 * 60 * 1000; // 10 minutos

interface FetchState {
  tanks: TankData[];
  loading: boolean;
  error: string | null;
  lastFetchedAt: Date | null;
}

function formatClock(d: Date | null): string {
  if (!d) return "--:--";
  return d.toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "America/Recife",
  });
}

export default function OperationalTanksPage() {
  const [state, setState] = useState<FetchState>({
    tanks: [],
    loading: true,
    error: null,
    lastFetchedAt: null,
  });
  const [refreshing, setRefreshing] = useState(false);
  const mountedRef = useRef(true);
  const hasDataRef = useRef(false);

  const { selectedFilial, isConsolidated, periodDates, filialLabel } = useGlobalFilter();

  const fetchTanks = useCallback(async (opts?: { silent?: boolean }) => {
    const silent = Boolean(opts?.silent && hasDataRef.current);
    console.log("[Tanks] Iniciando fetch...", {
      start: periodDates.start,
      end: periodDates.end,
      filial: selectedFilial,
      silent,
    });
    if (silent) {
      setRefreshing(true);
    } else {
      setState((prev) => ({ ...prev, loading: true, error: null }));
    }
    try {
      const response = await apiService.getOperationalTanks(
        periodDates.start,
        periodDates.end,
        isConsolidated ? undefined : selectedFilial
      );
      console.log("[Tanks] Resposta recebida:", response);
      if (mountedRef.current) {
        const tanks = response.tanks || [];
        hasDataRef.current = tanks.length > 0 || hasDataRef.current;
        setState((prev) => ({
          tanks,
          loading: false,
          error: null,
          lastFetchedAt: new Date(),
        }));
      }
    } catch (err) {
      console.error("[Tanks] Erro no fetch:", err);
      if (mountedRef.current) {
        setState((prev) => ({
          tanks: silent ? prev.tanks : [],
          loading: false,
          error: err instanceof Error ? err.message : "Erro ao carregar dados",
          lastFetchedAt: silent ? prev.lastFetchedAt : prev.lastFetchedAt,
        }));
      }
    } finally {
      if (mountedRef.current) setRefreshing(false);
    }
  }, [periodDates.start, periodDates.end, isConsolidated, selectedFilial]);

  useEffect(() => {
    mountedRef.current = true;
    hasDataRef.current = false;
    void fetchTanks({ silent: false });
    return () => {
      mountedRef.current = false;
    };
  }, [fetchTanks]);

  // Polling silencioso a cada 10 minutos — sem skeleton / sem reset de scroll
  useEffect(() => {
    const id = window.setInterval(() => {
      void fetchTanks({ silent: true });
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(id);
  }, [fetchTanks]);

  const { tanks, loading, error, lastFetchedAt } = state;

  const filteredTanks = useMemo(() => {
    const base = isConsolidated
      ? tanks
      : tanks.filter((t) => t.empresa_codigo === selectedFilial);
    // Dedupe defensivo (empresa + tanque) — evita cards repetidos
    const seen = new Set<string>();
    const unique: TankData[] = [];
    for (const t of base) {
      const key = `${t.empresa_codigo}:${t.id}`;
      if (seen.has(key)) continue;
      seen.add(key);
      unique.push(t);
    }
    return unique;
  }, [tanks, selectedFilial, isConsolidated]);

  const tanksByFilial = useMemo(() => {
    const order = [5555, 11495, 74014];
    const map = new Map<number, TankData[]>();
    for (const t of filteredTanks) {
      const code = Number(t.empresa_codigo) || 0;
      if (!map.has(code)) map.set(code, []);
      map.get(code)!.push(t);
    }
    const codes = [
      ...order.filter((c) => map.has(c)),
      ...[...map.keys()].filter((c) => !order.includes(c)).sort((a, b) => a - b),
    ];
    return codes.map((code) => ({
      code,
      nome: empresaNomeOperacional(code),
      tanks: map.get(code) || [],
    }));
  }, [filteredTanks]);

  const chartData = useMemo(
    () =>
      filteredTanks.map((t) => ({
        ...t,
        chartLabel: isConsolidated
          ? `${empresaNomeOperacional(t.empresa_codigo).split(" ").slice(-1)[0]} · ${t.name}`
          : t.name,
      })),
    [filteredTanks, isConsolidated]
  );

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
        <div className="space-y-2">
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Monitoramento de Tanques
          </h1>
          <p className="text-slate-500 text-sm">
            Variação térmica (Física) vs Desvios Reais na Pista — Dados Reais WebPosto
          </p>
          <div
            className="inline-flex items-center gap-2 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-3 py-1 text-[11px] text-emerald-200/90"
            title="Rebusca automática da API a cada 10 minutos, sem recarregar a tela"
          >
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
            </span>
            <span>
              Atualização automática (10m) · Última leitura: {formatClock(lastFetchedAt)}
              {refreshing ? " · sync…" : ""}
            </span>
          </div>
        </div>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={() => void fetchTanks({ silent: hasDataRef.current })} 
          disabled={loading || refreshing}
          className="bg-cyan-500/10 border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20 hover:text-cyan-200"
        >
          <RefreshCcw size={14} className={cn("mr-2 text-cyan-400", (loading || refreshing) && "animate-spin")} />
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
          {isConsolidated ? (
            <div className="space-y-8">
              {tanksByFilial.map((grupo) => (
                <section key={grupo.code} className="space-y-3">
                  <div className="flex items-center gap-2 border-b border-white/10 pb-2">
                    <h2 className="text-base font-bold text-white">{grupo.nome}</h2>
                    <Badge variant="outline" className="text-[10px] border-slate-700 text-slate-400">
                      {grupo.tanks.length} tanque(s)
                    </Badge>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                    {grupo.tanks.map((tank) => (
                      <TankLevelCard
                        key={`tank-${tank.empresa_codigo}-${tank.id}`}
                        tank={tank}
                      />
                    ))}
                  </div>
                </section>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {filteredTanks.map((tank) => (
                <TankLevelCard
                  key={`tank-${tank.empresa_codigo}-${tank.id}`}
                  tank={tank}
                />
              ))}
            </div>
          )}

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
                    <ComposedChart data={chartData}>
                      <CartesianGrid
                        strokeDasharray="3 3"
                        vertical={false}
                        strokeOpacity={0.1}
                      />
                      <XAxis
                        dataKey="chartLabel"
                        fontSize={10}
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#94a3b8" }}
                        interval={0}
                        angle={isConsolidated ? -25 : 0}
                        textAnchor={isConsolidated ? "end" : "middle"}
                        height={isConsolidated ? 70 : 30}
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
                {[...filteredTanks]
                  .sort((a, b) => Math.abs(b.physical_var) - Math.abs(a.physical_var))
                  .map((tank) => (
                    <div
                      key={`status-${tank.empresa_codigo}-${tank.id}`}
                      className="flex items-center justify-between p-3 rounded-lg border border-white/5 bg-slate-50/5 dark:bg-slate-900/50"
                    >
                      <div className="space-y-1 min-w-0">
                        <p className="text-sm font-bold text-white truncate">{tank.name}</p>
                        <p className="text-[10px] text-slate-500 truncate">
                          {isConsolidated
                            ? `${empresaNomeOperacional(tank.empresa_codigo)} · ${tank.fuel}`
                            : tank.fuel}
                        </p>
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

function TankLevelCard({ tank }: { tank: TankData }) {
  const gnv = isGnvProduct(tank.fuel) || isGnvProduct(tank.name);
  const tankNum = String(tank.id).padStart(2, "0");
  const fuel = (tank.fuel || tank.name || "COMBUSTÍVEL").toUpperCase();
  const title = `Tanque ${tankNum} - ${fuel}`;
  const filialNome = empresaNomeOperacional(tank.empresa_codigo);
  const alerta = gnv ? "OK" : tank.alerta_autonomia || "OK";
  const label = gnv
    ? "GNV canalizado — sem carreta"
    : tank.alerta_label ||
      (alerta === "COMPRA_URGENTE"
        ? "Pedir Carreta"
        : alerta === "ATENCAO"
          ? "Atenção"
          : "Saudável");

  const divergencia = tank.divergencia_litros ?? tank.physical_var ?? 0;

  return (
    <TankMonitorCard
      title={title}
      fuelLabel={`${filialNome}${tank.temp > 0 ? ` · ${tank.temp}ºC` : ""}`}
      currentLiters={tank.current}
      capacityLiters={tank.capacity}
      autonomiaDias={gnv ? null : tank.autonomia_dias}
      consumoMedioDiario={gnv ? null : tank.consumo_medio_diario}
      alertLevel={alerta}
      alertLabel={label}
      isGnv={gnv}
      tankId={tank.id}
      empresaCodigo={tank.empresa_codigo}
      measuredAt={tank.data_hora_medidor}
      footer={
        <>
          <p className="text-[10px] uppercase font-bold tracking-wider text-slate-500">
            Auditoria Físico × Contábil
          </p>
          <div className="flex justify-between gap-2">
            <span>Físico</span>
            <span className="font-mono text-slate-200">
              {(tank.estoque_fisico ?? tank.current).toLocaleString("pt-BR")} L
            </span>
          </div>
          <div className="flex justify-between gap-2">
            <span>Contábil</span>
            <span className="font-mono text-slate-200">
              {(tank.estoque_contabil ?? 0).toLocaleString("pt-BR")} L
            </span>
          </div>
          <div className="flex justify-between gap-2">
            <span>Divergência</span>
            <span
              className={cn(
                "font-mono font-bold",
                tank.alerta_variancia ? "text-rose-400" : "text-emerald-400"
              )}
            >
              {divergencia > 0 ? "+" : ""}
              {divergencia.toLocaleString("pt-BR")} L
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
                "Alerta de variância (térmica ou fuga)"}
            </Badge>
          ) : (
            <p className="text-[10px] text-emerald-400">
              Dentro da tolerância ±0,6%
            </p>
          )}
        </>
      }
    />
  );
}
