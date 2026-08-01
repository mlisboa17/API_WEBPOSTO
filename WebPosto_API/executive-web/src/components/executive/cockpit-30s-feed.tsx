"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Fuel, RefreshCcw, Clock, AlertTriangle, Wifi, WifiOff, Activity, User } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import {
  fetchFeedVivoPista,
  fetchKpisResumo,
  formatLitros,
  horaFromDataHora,
  hojeLocalIso,
  segundosDesdeSync,
  type AbastecimentoRestV1,
  type ResumoDiaPista,
  type TotaisDiaPista,
} from "@/services/webposto/pista";
import { PresidentTopKpis } from "@/components/executive/president-top-kpis";
import { apiService } from "@/lib/api";

interface FilialSummary {
  empresa_codigo: number;
  empresa_nome: string;
  total_litros: number;
  total_valor: number;
  total_transacoes: number;
  total_pendentes: number;
  status: "PISTA_ATIVA" | "AGUARDANDO";
}

const POLL_INTERVAL_MS = 30000;
const FEED_DISPLAY_LIMIT = 60;

const FILIAIS_META = [
  { empresa_codigo: 5555, empresa_nome: "AP CASA CAIADA" },
  { empresa_codigo: 11495, empresa_nome: "POSTO VIP" },
  { empresa_codigo: 74014, empresa_nome: "POSTO REAL / DOZE" },
] as const;

const FILIAL_COLORS: Record<number, { bg: string; border: string; text: string }> = {
  5555: { bg: "bg-blue-500/10", border: "border-blue-500/30", text: "text-blue-400" },
  11495: { bg: "bg-purple-500/10", border: "border-purple-500/30", text: "text-purple-400" },
  74014: { bg: "bg-emerald-500/10", border: "border-emerald-500/30", text: "text-emerald-400" },
};

type FeedFilter = "TODOS" | "PENDENTES" | "EMITIDOS";

function isPendente(a: AbastecimentoRestV1) {
  return a.status === "PENDENTE";
}

/** KPIs a partir do resumoDia (universo completo) — nunca do subset do feed. */
function buildFiliaisFromResumo(resumo: ResumoDiaPista | null): FilialSummary[] {
  const byEmp = new Map((resumo?.porFilial || []).map((f) => [f.idEmpresa, f]));
  return FILIAIS_META.map((base) => {
    const row = byEmp.get(base.empresa_codigo);
    const totalTx = row?.totalAbastecimentos ?? 0;
    return {
      empresa_codigo: base.empresa_codigo,
      empresa_nome: row?.nomeEmpresa || base.empresa_nome,
      total_litros: row?.totalLitros ?? 0,
      total_valor: row?.totalValor ?? 0,
      total_transacoes: totalTx,
      total_pendentes: row?.totalPendentes ?? 0,
      status: totalTx > 0 ? "PISTA_ATIVA" : "AGUARDANDO",
    };
  });
}

export function Cockpit30sFeed() {
  const [items, setItems] = useState<AbastecimentoRestV1[]>([]);
  const [resumoDia, setResumoDia] = useState<ResumoDiaPista | null>(null);
  const [totaisDia, setTotaisDia] = useState<TotaisDiaPista | null>(null);
  const [alertasCriticos, setAlertasCriticos] = useState(0);
  const [totalDia, setTotalDia] = useState(0);
  const [fonte, setFonte] = useState("REST_v1_Abastecimentos");
  const [ultimaSyncIso, setUltimaSyncIso] = useState<string | null>(null);
  const [fromCache, setFromCache] = useState(false);
  const [syncAgeSec, setSyncAgeSec] = useState<number | null>(null);
  const [observacoes, setObservacoes] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [connectionStatus, setConnectionStatus] = useState<"connected" | "polling" | "error">("polling");
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [countdown, setCountdown] = useState(30);
  const [feedFilter, setFeedFilter] = useState<FeedFilter>("TODOS");
  const [postoFilter, setPostoFilter] = useState<number | "TODAS">("TODAS");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const ultimaSyncIsoRef = useRef<string | null>(null);

  const fetchData = useCallback(async () => {
    const hoje = hojeLocalIso();
    console.log("[Cockpit30s] Fetch cache RAM + KPIs + card-fraud...", { data: hoje });
    try {
      const [result, kpis, fraud] = await Promise.all([
        fetchFeedVivoPista({
          dataInicio: hoje,
          dataFim: hoje,
          limiteBaixados: 100,
        }),
        fetchKpisResumo(),
        apiService.getCardFraudAudit(hoje, hoje, undefined, null),
      ]);
      console.log("[Cockpit30s] Resposta:", {
        fonte: result.fonte,
        feed: result.items.length,
        totalDia: result.totalDia,
        fat: kpis.totaisDia?.faturamentoTotal,
        cartoes: kpis.totaisDia?.valorCartoesDia,
        criticos: fraud?.resumo?.totalCriticos,
        fromCache: result.fromCache || kpis.fromCache,
      });
      setItems(Array.isArray(result.items) ? result.items : []);
      setResumoDia(result.resumoDia ?? kpis.resumoDia ?? null);
      const totaisMerged: TotaisDiaPista = {
        ...(result.totaisDia || {}),
        ...(kpis.totaisDia || {}),
        faturamentoTotal:
          kpis.totaisDia?.faturamentoTotal ||
          result.totaisDia?.faturamentoTotal ||
          result.resumoDia?.totalValor ||
          0,
        volumetriaTotalLitros:
          kpis.totaisDia?.volumetriaTotalLitros ||
          result.totaisDia?.volumetriaTotalLitros ||
          result.resumoDia?.totalLitros ||
          0,
        qtdTotalAbastecimentos:
          kpis.totaisDia?.qtdTotalAbastecimentos ||
          result.totaisDia?.qtdTotalAbastecimentos ||
          result.totalDia ||
          0,
      };
      setTotaisDia(totaisMerged);
      setAlertasCriticos(
        Number(fraud?.resumo?.totalCriticos ?? 0) ||
          Number(kpis.fraude?.alertasCriticos ?? 0) ||
          Number(totaisMerged.alertasCriticosRetencao ?? 0) ||
          0
      );
      setTotalDia(totaisMerged.qtdTotalAbastecimentos || result.totalDia || 0);
      setFonte(kpis.fonte || result.fonte || "RAM_CACHE");
      ultimaSyncIsoRef.current =
        kpis.ultimaSincronizacaoIso || result.ultimaSincronizacaoIso;
      setUltimaSyncIso(kpis.ultimaSincronizacaoIso || result.ultimaSincronizacaoIso);
      setFromCache(Boolean(result.fromCache || kpis.fromCache));
      setSyncAgeSec(
        segundosDesdeSync(kpis.ultimaSincronizacaoIso || result.ultimaSincronizacaoIso)
      );
      setObservacoes(result.observacoes || []);
      setError(result.error || kpis.error || null);
      setConnectionStatus(
        result.error && !result.items.length && !totaisMerged.faturamentoTotal
          ? "error"
          : "connected"
      );
      setLastRefresh(new Date());
      setCountdown(30);
    } catch (err) {
      console.error("[Cockpit30s] Erro no fetch:", err);
      setConnectionStatus("error");
      setError(err instanceof Error ? err.message : "Falha de conexao");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    intervalRef.current = setInterval(fetchData, POLL_INTERVAL_MS);
    countdownRef.current = setInterval(() => {
      setCountdown((prev) => (prev > 0 ? prev - 1 : 30));
      setSyncAgeSec(segundosDesdeSync(ultimaSyncIsoRef.current));
    }, 1000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (countdownRef.current) clearInterval(countdownRef.current);
    };
  }, [fetchData]);

  const formatBRL = (val: number) =>
    new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(val);

  const formatTime = (date: Date) =>
    date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });

  const filiais = buildFiliaisFromResumo(resumoDia);
  const grupoValor = resumoDia?.totalValor ?? 0;
  const grupoLitros = resumoDia?.totalLitros ?? 0;
  const grupoTx = resumoDia?.totalAbastecimentos ?? totalDia;
  const grupoPend = resumoDia?.totalPendentes ?? 0;

  const porPosto =
    postoFilter === "TODAS" ? items : items.filter((a) => a.idEmpresa === postoFilter);
  const pendentesTotal = porPosto.filter(isPendente).length;
  const emitidosTotal = porPosto.filter((a) => !isPendente(a)).length;
  const feedFiltrado = porPosto.filter((a) => {
    if (feedFilter === "PENDENTES") return isPendente(a);
    if (feedFilter === "EMITIDOS") return !isPendente(a);
    return true;
  });
  const feedExibidos = Math.min(feedFiltrado.length, FEED_DISPLAY_LIMIT);
  const totalDiaEscopo =
    postoFilter === "TODAS"
      ? totalDia || grupoTx
      : filiais.find((f) => f.empresa_codigo === postoFilter)?.total_transacoes ?? 0;

  const postoLabel =
    postoFilter === "TODAS"
      ? "Todas as unidades"
      : filiais.find((f) => f.empresa_codigo === postoFilter)?.empresa_nome ||
        `Posto ${postoFilter}`;

  return (
    <div className="p-4 lg:p-8 max-w-[1600px] mx-auto space-y-6">
      <header className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className="bg-green-500/10 text-green-400 border-green-500/20">
              LIVE
            </Badge>
            <span className="text-[10px] text-slate-300 uppercase tracking-widest font-bold">
              Operacional
            </span>
            <Badge className="bg-emerald-500/15 text-emerald-300 border-emerald-500/30 text-[10px]">
              {fonte} · real
            </Badge>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Cockpit 30s — Pista Multi-Filial
          </h1>
          <p className="text-slate-300 text-sm">
            Cache RAM + worker 30s · KPIs = total real do dia · resposta instantânea
            {fromCache ? " · fromCache" : ""}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs text-slate-300">
            {connectionStatus === "connected" ? (
              <Wifi size={14} className="text-green-500" />
            ) : connectionStatus === "error" ? (
              <WifiOff size={14} className="text-red-500" />
            ) : (
              <Wifi size={14} className="text-amber-500 animate-pulse" />
            )}
            <span>
              {connectionStatus === "connected"
                ? "Conectado"
                : connectionStatus === "error"
                  ? "Reconectando..."
                  : "Polling HTTP"}
            </span>
          </div>
          <Badge
            variant="outline"
            className="text-xs bg-cyan-500/20 border-cyan-500/30 text-cyan-300 font-mono font-bold"
          >
            <Clock size={12} className="mr-1" />
            {countdown}s
          </Badge>
          <Button
            size="sm"
            variant="outline"
            onClick={() => void fetchData()}
            className="border-white/10 text-slate-200"
          >
            <RefreshCcw size={14} className="mr-1" />
            Atualizar
          </Button>
        </div>
      </header>

      {lastRefresh && (
        <p className="text-[11px] text-slate-300">
          Última atualização: {formatTime(lastRefresh)}
          {error ? ` · ${error}` : ""}
          {totalDia > 0 ? ` · Total do dia: ${totalDia} abast.` : ""}
        </p>
      )}

      <PresidentTopKpis
        totais={totaisDia}
        alertasCriticos={alertasCriticos}
        loading={loading}
        fromCache={fromCache}
      />

      {loading && !totaisDia?.faturamentoTotal ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-36 bg-slate-800" />
          ))}
        </div>
      ) : (
        <div className="space-y-6">
          {grupoPend > 0 && (
            <div className="rounded-lg border border-amber-500/40 bg-amber-950/40 px-4 py-3 flex items-start gap-3 animate-pulse">
              <AlertTriangle className="text-amber-400 shrink-0 mt-0.5" size={18} />
              <p className="text-sm text-amber-200 font-semibold">
                {grupoPend} abastecimento(s) PENDENTE(S) aguardando baixa
              </p>
            </div>
          )}

          {/* KPIs: Grupo + Filiais — totais reais do dia (resumoDia) */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            <Card className="border border-cyan-500/30 bg-slate-900/90">
              <CardContent className="pt-4 space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-bold text-cyan-300">GRUPO (Rede)</p>
                  <Badge
                    variant="outline"
                    className="text-[10px] text-emerald-400 border-emerald-500/30"
                  >
                    <Activity size={10} className="mr-1" />
                    DIA COMPLETO
                  </Badge>
                </div>
                <p className="text-2xl font-bold text-white font-mono">{formatBRL(grupoValor)}</p>
                <p className="text-xs text-slate-200">
                  {formatLitros(grupoLitros)} · {grupoTx} abast.
                </p>
                <p className="text-[10px] text-slate-300">
                  KPI do dia (não limitado ao feed)
                </p>
              </CardContent>
            </Card>

            {filiais.map((filial) => {
              const colors = FILIAL_COLORS[filial.empresa_codigo] || FILIAL_COLORS[5555];
              return (
                <Card
                  key={filial.empresa_codigo}
                  className={cn("border bg-slate-900/90", colors.border)}
                >
                  <CardContent className="pt-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <p className={cn("text-sm font-bold", colors.text)}>{filial.empresa_nome}</p>
                      <Badge
                        variant="outline"
                        className={cn(
                          "text-[10px]",
                          filial.status === "PISTA_ATIVA"
                            ? "text-emerald-400 border-emerald-500/30"
                            : "text-slate-300 border-slate-600"
                        )}
                      >
                        <Activity size={10} className="mr-1" />
                        {filial.status === "PISTA_ATIVA" ? "ATIVA" : "AGUARDANDO"}
                      </Badge>
                    </div>
                    <p className="text-2xl font-bold text-white font-mono">
                      {formatBRL(filial.total_valor)}
                    </p>
                    <p className="text-xs text-slate-200">
                      {formatLitros(filial.total_litros)} · {filial.total_transacoes} abast.
                    </p>
                    {(filial.total_pendentes ?? 0) > 0 && (
                      <p className="text-xs text-amber-400 font-semibold">
                        🟡 {filial.total_pendentes} pendente(s) aguardando pagamento
                      </p>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>

          <Card className="border-white/5 bg-slate-900/90">
            <CardHeader className="space-y-3">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
                <CardTitle className="text-lg flex items-center gap-2 text-white">
                  <Fuel size={18} className="text-blue-500" />
                  Feed Vivo da Pista (REST v1)
                </CardTitle>
                <div className="flex items-center gap-1.5 flex-wrap">
                  {(
                    [
                      { id: "TODOS" as const, label: "Todos", count: porPosto.length },
                      { id: "PENDENTES" as const, label: "Pendentes", count: pendentesTotal },
                      { id: "EMITIDOS" as const, label: "Emitidos", count: emitidosTotal },
                    ] as const
                  ).map((opt) => (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => setFeedFilter(opt.id)}
                      className={cn(
                        "px-3 py-1.5 rounded-md text-xs font-semibold border transition-colors",
                        feedFilter === opt.id
                          ? opt.id === "PENDENTES"
                            ? "bg-amber-500/20 border-amber-500/50 text-amber-300"
                            : opt.id === "EMITIDOS"
                              ? "bg-emerald-500/20 border-emerald-500/50 text-emerald-300"
                              : "bg-cyan-500/20 border-cyan-500/50 text-cyan-300"
                          : "bg-slate-900/60 border-white/10 text-slate-300 hover:text-slate-200 hover:border-white/20"
                      )}
                    >
                      {opt.label}
                      <span className="ml-1.5 font-mono tabular-nums opacity-80">{opt.count}</span>
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-[10px] uppercase tracking-widest text-slate-300 font-bold mr-1">
                  Posto
                </span>
                <button
                  type="button"
                  onClick={() => setPostoFilter("TODAS")}
                  className={cn(
                    "px-3 py-1.5 rounded-md text-xs font-semibold border transition-colors",
                    postoFilter === "TODAS"
                      ? "bg-white/10 border-white/30 text-white"
                      : "bg-slate-900/60 border-white/10 text-slate-300 hover:text-slate-200"
                  )}
                >
                  Todas
                  <span className="ml-1.5 font-mono tabular-nums opacity-80">{items.length}</span>
                </button>
                {filiais.map((f) => {
                  const colors = FILIAL_COLORS[f.empresa_codigo] || FILIAL_COLORS[5555];
                  const qtd = items.filter((a) => a.idEmpresa === f.empresa_codigo).length;
                  const active = postoFilter === f.empresa_codigo;
                  return (
                    <button
                      key={f.empresa_codigo}
                      type="button"
                      onClick={() => setPostoFilter(f.empresa_codigo)}
                      className={cn(
                        "px-3 py-1.5 rounded-md text-xs font-semibold border transition-colors",
                        active
                          ? cn(colors.bg, colors.border, colors.text)
                          : "bg-slate-900/60 border-white/10 text-slate-300 hover:text-slate-200"
                      )}
                    >
                      {f.empresa_nome.replace(/^POSTO\s+/i, "").replace(/^AP\s+/i, "")}
                      <span className="ml-1.5 font-mono tabular-nums opacity-80">{qtd}</span>
                    </button>
                  );
                })}
              </div>
              <p className="text-[11px] text-slate-200 font-medium">
                Exibindo os últimos {feedExibidos} abastecimentos de {totalDiaEscopo} do dia
                {syncAgeSec != null
                  ? ` • 🟢 Sincronizado há ${syncAgeSec} seg`
                  : " • 🟡 Aguardando 1ª sincronização"}
                {" · "}
                {postoLabel}
                {feedFilter === "PENDENTES" ? " · Pendentes" : ""}
                {feedFilter === "EMITIDOS" ? " · Emitidos" : ""}
              </p>
              {pendentesTotal === 0 && observacoes.length > 0 && (
                <div className="rounded-md border border-amber-500/30 bg-amber-950/30 px-3 py-2 text-[11px] text-amber-200/90 leading-relaxed">
                  ⚠️ {observacoes[0]}
                </div>
              )}
            </CardHeader>
            <CardContent>
              {feedFiltrado.length === 0 ? (
                <div className="py-10 text-center text-sm text-slate-300">
                  Nenhum abastecimento para{" "}
                  <span className="text-slate-200 font-medium">{postoLabel}</span>
                  {" · "}
                  <span className="text-slate-200 font-medium">{feedFilter}</span> neste momento.
                </div>
              ) : (
                <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
                  {feedFiltrado.slice(0, FEED_DISPLAY_LIMIT).map((a, idx) => {
                    const colors = FILIAL_COLORS[a.idEmpresa] || FILIAL_COLORS[5555];
                    const pendente = isPendente(a);
                    return (
                      <div
                        key={`${a.idAbastecimento}-${a.idEmpresa}-${idx}`}
                        className={cn(
                          "rounded-lg border px-3 py-2.5 transition-colors",
                          pendente
                            ? "bg-amber-950/40 border-amber-500/50 animate-pulse"
                            : "bg-slate-900/80 border-emerald-500/20 hover:bg-slate-800/60"
                        )}
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span
                              className={cn(
                                "font-mono text-sm font-bold",
                                pendente ? "text-amber-400" : "text-emerald-400"
                              )}
                            >
                              ⏱️ {horaFromDataHora(a.dataHora)}
                            </span>
                            <Badge
                              variant="outline"
                              className={cn("text-[9px]", colors.text, colors.border)}
                            >
                              {a.nomeEmpresa || `Filial ${a.idEmpresa}`}
                            </Badge>
                            <Badge
                              variant="outline"
                              className={cn(
                                "text-[9px] font-bold",
                                pendente
                                  ? "bg-amber-500/20 text-amber-400 border-amber-500/40"
                                  : "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                              )}
                            >
                              {pendente ? "🟡 PENDENTE" : "🟢 PAGO"}
                            </Badge>
                            {pendente && (
                              <Badge
                                variant="outline"
                                className="text-[9px] border-amber-500/30 text-amber-300/80"
                              >
                                {a.reservado ? "Reservado" : "Disponível"}
                              </Badge>
                            )}
                          </div>
                          <span
                            className={cn(
                              "font-mono text-sm font-bold",
                              pendente ? "text-amber-400" : "text-emerald-400"
                            )}
                          >
                            {formatBRL(a.valorTotal)}
                          </span>
                        </div>
                        <p className="text-xs text-slate-200 mt-1.5">
                          ⛽ Bico {String(a.bico).padStart(2, "0")} • {a.descricaoProduto} •{" "}
                          {formatLitros(a.litros)} • {formatBRL(a.valorTotal ?? 0)}
                        </p>
                        <p className="text-xs text-slate-300 mt-1 flex items-center gap-1">
                          <User size={11} />
                          Frentista: {a.nomeFrentista || "N/I"}
                        </p>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
