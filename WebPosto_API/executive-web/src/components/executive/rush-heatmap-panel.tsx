"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CalendarClock,
  Flame,
  Loader2,
  RefreshCcw,
  ShieldAlert,
  Target,
  Timer,
  Trophy,
  Users,
  Zap,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { InfoTooltip } from "@/components/ui/info-tooltip";
import { apiService } from "@/lib/api";
import type {
  RushHeatmapCard,
  RushHeatmapPost,
  RushHeatmapResponse,
} from "@/types/api";
import { cn } from "@/lib/utils";

type DrillLevel = "posto" | "ilha" | "frentista" | "periodo" | "recorrencia";

const SEV_ORDER = ["RED_HOT", "RED", "ORANGE", "YELLOW"] as const;

const COL_HELP = {
  abastH: "Taxa horária normalizada pelo tempo efetivo de pista.",
  lh: "Volume em Litros (0.000 L) injetados por hora ativa.",
  minAtivos:
    "Tempo em minutos que o frentista esteve operando no bico durante a janela de rush.",
  tma: "Tempo Médio de Atendimento (Ciclo do bico ao caixa).",
  proxies:
    "Cálculo derivado da pressão dos bicos e tempo de baixa do caixa. Isento de sensores físicos.",
} as const;

function sevIcon(sev: string) {
  if (sev === "RED_HOT") return "🔥";
  if (sev === "RED") return "🔴";
  if (sev === "ORANGE") return "🟠";
  if (sev === "YELLOW") return "🟡";
  return "";
}

function sevTone(sev: string) {
  if (sev === "RED_HOT")
    return "border-rose-400/70 bg-rose-950/50 shadow-[0_0_20px_rgba(244,63,94,0.35)]";
  if (sev === "RED") return "border-rose-500/40 bg-rose-950/30";
  if (sev === "ORANGE") return "border-orange-500/40 bg-orange-950/25";
  return "border-amber-500/30 bg-amber-950/20";
}

function imbalanceTone(pct: number) {
  if (pct < 30)
    return "bg-emerald-500/15 text-[#10B981] border-emerald-500/30";
  if (pct <= 50)
    return "bg-amber-500/15 text-[#F59E0B] border-amber-500/30";
  return "bg-rose-500/15 text-[#EF4444] border-rose-500/30";
}

/** Formata "28 × 9" com × em tom neutro. */
function AbsoluteCompare({ value }: { value: string }) {
  const parts = String(value).split(/\s*[×xX]\s*/);
  if (parts.length !== 2) {
    return (
      <span className="font-bold text-[#F8FAFC] font-mono tabular-nums">{value}</span>
    );
  }
  return (
    <span className="inline-flex items-baseline gap-1.5 font-mono tabular-nums">
      <span className="font-bold text-[#F8FAFC] text-lg leading-none">{parts[0]}</span>
      <span className="text-slate-400 font-semibold text-sm">×</span>
      <span className="font-bold text-[#F8FAFC] text-lg leading-none">{parts[1]}</span>
    </span>
  );
}

function ThHelp({ label, help }: { label: string; help: string }) {
  return (
    <th className="px-3 py-2.5 text-right font-medium">
      <span className="inline-flex items-center justify-end gap-1">
        {label}
        <InfoTooltip content={help} />
      </span>
    </th>
  );
}

function pad2(n: number) {
  return String(n).padStart(2, "0");
}

/** Valor para input datetime-local (YYYY-MM-DDTHH:mm) no fuso local. */
function toLocalInput(d: Date): string {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}T${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

function shortcutUltimas2h() {
  const end = new Date();
  const start = new Date(end.getTime() - 2 * 3_600_000);
  return { inicio: toLocalInput(start), fim: toLocalInput(end) };
}

function shortcutRushHoje() {
  const d = new Date();
  const day = `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
  return { inicio: `${day}T17:00`, fim: `${day}T20:00` };
}

/** Turno: 06–14 · 14–22 · 22–06(+1). */
function shortcutTurnoAtual() {
  const now = new Date();
  const h = now.getHours();
  const day = `${now.getFullYear()}-${pad2(now.getMonth() + 1)}-${pad2(now.getDate())}`;
  if (h >= 6 && h < 14) return { inicio: `${day}T06:00`, fim: `${day}T14:00` };
  if (h >= 14 && h < 22) return { inicio: `${day}T14:00`, fim: `${day}T22:00` };
  if (h >= 22) {
    const next = new Date(now);
    next.setDate(next.getDate() + 1);
    const nextDay = `${next.getFullYear()}-${pad2(next.getMonth() + 1)}-${pad2(next.getDate())}`;
    return { inicio: `${day}T22:00`, fim: `${nextDay}T06:00` };
  }
  // 00–06 → turno noturno iniciado ontem
  const prev = new Date(now);
  prev.setDate(prev.getDate() - 1);
  const prevDay = `${prev.getFullYear()}-${pad2(prev.getMonth() + 1)}-${pad2(prev.getDate())}`;
  return { inicio: `${prevDay}T22:00`, fim: `${day}T06:00` };
}

function formatPeriodoLabel(inicio: string, fim: string): string {
  const parse = (raw: string) => {
    const d = new Date(raw.includes("T") ? raw : `${raw}T00:00`);
    if (Number.isNaN(d.getTime())) return raw;
    return {
      date: d.toLocaleDateString("pt-BR"),
      time: d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }),
    };
  };
  const a = parse(inicio);
  const b = parse(fim);
  if (typeof a === "string" || typeof b === "string") return `${inicio} → ${fim}`;
  const sameDay = a.date === b.date;
  return sameDay
    ? `${a.date} das ${a.time} às ${b.time}`
    : `${a.date} ${a.time} → ${b.date} ${b.time}`;
}

export function RushHeatmapPanel({ empresaCodigo }: { empresaCodigo?: number }) {
  const initialWin = useMemo(() => shortcutUltimas2h(), []);
  const [inicio, setInicio] = useState(initialWin.inicio);
  const [fim, setFim] = useState(initialWin.fim);
  const [data, setData] = useState<RushHeatmapResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPost, setSelectedPost] = useState<number | null>(null);
  const [drill, setDrill] = useState<DrillLevel>("posto");
  const [busyInt, setBusyInt] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiService.getPistaRushHeatmap(empresaCodigo, {
        inicio,
        fim,
      });
      setData(res);
      setSelectedPost((prev) => {
        if (prev != null && res.posts?.some((p) => p.unidade_id === prev)) return prev;
        return res.posts?.[0]?.unidade_id ?? null;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro no mapa de calor");
    } finally {
      setLoading(false);
    }
  }, [empresaCodigo, inicio, fim]);

  // Refetch imediato ao mudar data/hora/filial
  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  const applyShortcut = (win: { inicio: string; fim: string }) => {
    setInicio(win.inicio);
    setFim(win.fim);
  };

  const cards = useMemo(() => {
    const list = [...(data?.intelligence_cards || [])].filter(
      (c) => c.severity !== "GREEN" && (c.heat_score ?? 0) >= 20
    );
    list.sort(
      (a, b) =>
        SEV_ORDER.indexOf(a.severity as (typeof SEV_ORDER)[number]) -
          SEV_ORDER.indexOf(b.severity as (typeof SEV_ORDER)[number]) ||
        (b.heat_score ?? 0) - (a.heat_score ?? 0)
    );
    return list;
  }, [data?.intelligence_cards]);

  const post: RushHeatmapPost | undefined = useMemo(
    () => data?.posts?.find((p) => p.unidade_id === selectedPost) || data?.posts?.[0],
    [data?.posts, selectedPost]
  );

  const imbalancePct = Math.round((post?.forecourt_imbalance_score ?? 0) * 100);
  const ramMs =
    data?.latency_ms != null
      ? Number(data.latency_ms).toLocaleString("pt-BR", {
          minimumFractionDigits: 0,
          maximumFractionDigits: 3,
        })
      : "—";

  const periodoLabel =
    data?.periodo_analise?.label || formatPeriodoLabel(inicio, fim);

  const registerIntervention = async (card: RushHeatmapCard) => {
    setBusyInt(true);
    try {
      await apiService.postPistaIntervention({
        empresa_codigo: post?.unidade_id,
        tipo: card.type,
        suspeita_type: card.type,
        subject_id: card.subject_id,
        acao: card.recommendation,
        operador: "diretor",
        metrics_baseline: {
          heat_score: card.heat_score,
          evidence: card.evidence,
        },
      });
      await fetchData();
    } finally {
      setBusyInt(false);
    }
  };

  if (loading && !data) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-24 bg-slate-900" />
        <Skeleton className="h-64 bg-slate-900" />
      </div>
    );
  }

  if (error && !data) {
    return (
      <Card className="border-red-500/30 bg-red-500/5 p-6 text-center">
        <AlertTriangle className="mx-auto text-red-400 mb-2" />
        <p className="text-red-300 text-sm">{error}</p>
        <Button className="mt-3" variant="outline" onClick={() => void fetchData()}>
          Tentar novamente
        </Button>
      </Card>
    );
  }

  return (
    <div className="space-y-5 relative">
      {loading && data ? (
        <div className="absolute inset-0 z-20 rounded-lg bg-slate-950/55 backdrop-blur-[1px] flex items-start justify-center pt-24 pointer-events-none">
          <div className="inline-flex items-center gap-2 rounded-full border border-sky-500/30 bg-slate-900/95 px-4 py-2 text-xs text-sky-200 shadow-lg">
            <Loader2 size={14} className="animate-spin text-sky-400" />
            Recomputando janela em RAM…
          </div>
        </div>
      ) : null}

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1.5">
          <h2 className="text-lg font-semibold text-[#F8FAFC] flex items-center gap-2">
            <Flame className="text-orange-400" size={18} />
            Rush Intelligence — Mapa de Calor Operacional V3
          </h2>
          <p className="text-sm text-slate-200 flex items-center gap-2 flex-wrap">
            <CalendarClock size={14} className="text-sky-400 shrink-0" />
            <span>
              📅 Analisando Período:{" "}
              <strong className="text-[#F8FAFC] font-mono">{periodoLabel}</strong>
              <span className="text-slate-500 font-normal"> (Rush Alvo)</span>
            </span>
          </p>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="inline-flex items-center gap-1.5 rounded-md border border-emerald-500/25 bg-emerald-950/30 px-2 py-1">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_#34d399]" />
              <span className="text-emerald-400 font-mono text-xs tracking-tight">
                RAM {ramMs} ms
              </span>
            </span>
            <span className="inline-flex items-center gap-1 text-slate-500">
              Proxies: pressão / TMA / ocupação bicos
              <InfoTooltip content={COL_HELP.proxies} />
            </span>
          </div>
        </div>
        <Button size="sm" variant="outline" onClick={() => void fetchData()}>
          <RefreshCcw size={14} className={cn("mr-1.5", loading && "animate-spin")} />
          Atualizar
        </Button>
      </div>

      {/* Filtros data/hora + atalhos */}
      <Card className="border-slate-800 bg-slate-950/60">
        <CardContent className="p-4 space-y-3">
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 items-end">
            <label className="block space-y-1.5">
              <span className="text-[10px] uppercase tracking-wider text-slate-500">
                Data/Hora Início
              </span>
              <input
                type="datetime-local"
                value={inicio}
                onChange={(e) => setInicio(e.target.value)}
                className="w-full h-9 rounded-md border border-slate-700 bg-slate-900 px-2 text-sm font-mono text-[#F8FAFC] focus:outline-none focus:ring-1 focus:ring-sky-500/50"
              />
            </label>
            <label className="block space-y-1.5">
              <span className="text-[10px] uppercase tracking-wider text-slate-500">
                Data/Hora Fim
              </span>
              <input
                type="datetime-local"
                value={fim}
                onChange={(e) => setFim(e.target.value)}
                className="w-full h-9 rounded-md border border-slate-700 bg-slate-900 px-2 text-sm font-mono text-[#F8FAFC] focus:outline-none focus:ring-1 focus:ring-sky-500/50"
              />
            </label>
            <div className="sm:col-span-2 flex flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="border-orange-500/40 text-orange-200 hover:bg-orange-950/40"
                onClick={() => applyShortcut(shortcutRushHoje())}
              >
                <Zap size={13} className="mr-1.5" />
                Rush Hoje (17h–20h)
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="border-sky-500/40 text-sky-200 hover:bg-sky-950/40"
                onClick={() => applyShortcut(shortcutUltimas2h())}
              >
                <Timer size={13} className="mr-1.5" />
                Últimas 2 Horas
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="border-violet-500/40 text-violet-200 hover:bg-violet-950/40"
                onClick={() => applyShortcut(shortcutTurnoAtual())}
              >
                <CalendarClock size={13} className="mr-1.5" />
                Turno Atual
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex flex-wrap gap-2">
        {(data?.posts || []).map((p) => (
          <button
            key={p.unidade_id}
            type="button"
            onClick={() => {
              setSelectedPost(p.unidade_id);
              setDrill("posto");
            }}
            className={cn(
              "rounded-md border px-3 py-1.5 text-xs transition-colors",
              selectedPost === p.unidade_id || (!selectedPost && p === data?.posts?.[0])
                ? "border-sky-500/50 bg-sky-950/40 text-sky-200"
                : "border-slate-700 text-slate-400 hover:text-slate-200"
            )}
          >
            {p.nome_unidade}{" "}
            {p.heat_score >= 20 ? (
              <span className="ml-1">{sevIcon(p.heat_color)}</span>
            ) : null}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap gap-1 text-[11px]">
        {(
          [
            ["posto", "POSTO"],
            ["ilha", "ILHA"],
            ["frentista", "FRENTISTA"],
            ["periodo", "PERÍODO"],
            ["recorrencia", "RECORRÊNCIA"],
          ] as [DrillLevel, string][]
        ).map(([k, label]) => (
          <button
            key={k}
            type="button"
            onClick={() => setDrill(k)}
            className={cn(
              "rounded px-2 py-1 border",
              drill === k
                ? "border-cyan-500/40 bg-cyan-950/30 text-cyan-200"
                : "border-slate-800 text-slate-500"
            )}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        <h3 className="text-xs uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
          <ShieldAlert size={12} /> Cards operacionais (🔥→🔴→🟠→🟡)
        </h3>
        {cards.length === 0 ? (
          <div className="rounded-lg border border-emerald-500/35 bg-gradient-to-r from-emerald-950/50 to-slate-950/40 px-4 py-3.5">
            <p className="text-sm font-medium text-emerald-300 leading-relaxed">
              🟢 OPERAÇÃO FLUIDA · Nenhuma suspeita de posicionamento, direcionamento ou
              baixa produtividade no rush atual.
            </p>
          </div>
        ) : (
          cards.map((c, i) => (
            <Card
              key={`${c.type}-${c.subject_id}-${i}`}
              className={cn("border", sevTone(c.severity))}
            >
              <CardHeader className="py-3 px-4 flex flex-row items-start justify-between gap-3">
                <div>
                  <CardTitle className="text-sm text-[#F8FAFC]">
                    {sevIcon(c.severity)} {c.type.replaceAll("_", " ")}
                  </CardTitle>
                  <p className="text-xs text-slate-400 mt-1">
                    {c.subject_type}: {c.subject_name} · Heat{" "}
                    <span className="font-mono font-bold text-[#F8FAFC]">
                      {c.heat_score}
                    </span>
                    {c.recurrence ? ` · Recorrência ${c.recurrence}` : ""}
                  </p>
                </div>
                <Badge className="text-[10px] border border-slate-600">{c.severity}</Badge>
              </CardHeader>
              <CardContent className="px-4 pb-4 space-y-2">
                {c.evidence?.comparativo_absoluto ? (
                  <div className="flex items-baseline gap-2">
                    <span className="text-[10px] uppercase tracking-wider text-slate-500">
                      Absoluto
                    </span>
                    <AbsoluteCompare value={String(c.evidence.comparativo_absoluto)} />
                  </div>
                ) : null}
                <p className="text-sm text-slate-300">{c.recommendation}</p>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-xs"
                  disabled={busyInt}
                  onClick={() => void registerIntervention(c)}
                >
                  <Target size={12} className="mr-1" />
                  Registrar intervenção (janela 30 min)
                </Button>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {post ? (
        <div className="grid lg:grid-cols-2 gap-4">
          <Card className="border-slate-800 bg-slate-950/50">
            <CardHeader className="py-3 px-4 space-y-2">
              <CardTitle className="text-sm text-[#F8FAFC] flex items-center gap-2">
                <Users size={14} /> Ranking absoluto
              </CardTitle>
              <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
                <span>Rush {post.rush_status?.label}</span>
                <span
                  className={cn(
                    "inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold font-mono",
                    imbalanceTone(imbalancePct)
                  )}
                  title="Índice de desequilíbrio da pista (máx − mín utilização das ilhas)"
                >
                  Imbalance {imbalancePct}%
                </span>
              </div>
            </CardHeader>
            <CardContent className="px-0 pb-2">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-[10px] uppercase tracking-wider text-slate-500 border-y border-slate-800">
                    <th className="px-3 py-2.5 text-left font-medium">#</th>
                    <th className="px-3 py-2.5 text-left font-medium">Frentista</th>
                    <th className="px-3 py-2.5 text-right font-medium">Abast.</th>
                    <th className="px-3 py-2.5 text-right font-medium">vs líder</th>
                  </tr>
                </thead>
                <tbody>
                  {(post.ranking_absoluto || []).map((r) => {
                    const isLeader = r.pos === 1;
                    return (
                      <tr
                        key={`${r.frentista_nome}-${r.pos}`}
                        className={cn(
                          "border-b border-slate-800/70",
                          isLeader &&
                            "bg-amber-500/[0.06] border-l-2 border-l-amber-400/70"
                        )}
                      >
                        <td className="px-3 py-2.5">
                          {isLeader ? (
                            <span className="inline-flex items-center gap-1 rounded-full border border-amber-400/40 bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-bold text-amber-200">
                              <Trophy size={10} className="text-amber-300" />
                              #1
                            </span>
                          ) : (
                            <span className="text-slate-500 font-mono">{r.pos}</span>
                          )}
                        </td>
                        <td
                          className={cn(
                            "px-3 py-2.5",
                            isLeader
                              ? "font-bold text-[#F8FAFC] tracking-wide"
                              : "text-slate-200"
                          )}
                        >
                          {isLeader ? (
                            <span className="uppercase text-[13px]">
                              {r.frentista_nome}
                            </span>
                          ) : (
                            r.frentista_nome
                          )}
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono font-bold text-[#F8FAFC] tabular-nums text-base">
                          {r.abastecimentos}
                        </td>
                        <td className="px-3 py-2.5 text-right">
                          <AbsoluteCompare value={r.comparativo} />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </CardContent>
          </Card>

          <Card className="border-slate-800 bg-slate-950/50">
            <CardHeader className="py-3 px-4">
              <CardTitle className="text-sm text-[#F8FAFC]">
                Ranking relativo (produtividade / hora ativa)
              </CardTitle>
            </CardHeader>
            <CardContent className="px-0 pb-2 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-[10px] uppercase tracking-wider text-slate-500 border-y border-slate-800">
                    <th className="px-3 py-2.5 text-left font-medium">Frentista</th>
                    <ThHelp label="Abast/h" help={COL_HELP.abastH} />
                    <ThHelp label="L/h" help={COL_HELP.lh} />
                    <ThHelp label="Min ativos" help={COL_HELP.minAtivos} />
                    <ThHelp label="TMA" help={COL_HELP.tma} />
                  </tr>
                </thead>
                <tbody>
                  {(post.ranking_relativo || []).map((r) => {
                    const isLeader = r.pos === 1;
                    return (
                      <tr
                        key={`rel-${r.frentista_nome}-${r.pos}`}
                        className={cn(
                          "border-b border-slate-800/70",
                          isLeader &&
                            "bg-amber-500/[0.06] border-l-2 border-l-amber-400/70"
                        )}
                      >
                        <td
                          className={cn(
                            "px-3 py-2.5",
                            isLeader
                              ? "font-bold text-[#F8FAFC]"
                              : "text-slate-200"
                          )}
                        >
                          {isLeader ? (
                            <span className="inline-flex items-center gap-1.5">
                              <Trophy size={12} className="text-amber-300 shrink-0" />
                              <span className="uppercase text-[12px] tracking-wide">
                                {r.frentista_nome}
                              </span>
                            </span>
                          ) : (
                            r.frentista_nome
                          )}
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono font-bold text-[#F8FAFC] tabular-nums">
                          {Number(r.abastecimentos_hora).toFixed(1)}
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono font-bold text-[#F8FAFC] tabular-nums">
                          {Number(r.litros_hora).toLocaleString("pt-BR", {
                            minimumFractionDigits: 1,
                            maximumFractionDigits: 1,
                          })}
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono font-bold text-[#F8FAFC] tabular-nums">
                          {Number(r.minutos_ativos).toFixed(1)}
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono font-bold text-[#F8FAFC] tabular-nums">
                          {Number(r.tma_minutos).toFixed(1)}
                          <span className="text-slate-500 font-normal text-[10px] ml-0.5">
                            m
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </CardContent>
          </Card>
        </div>
      ) : null}

      {post && drill === "ilha" ? (
        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-sm text-[#F8FAFC]">Pressão por ilha</CardTitle>
          </CardHeader>
          <CardContent className="grid sm:grid-cols-3 gap-2 px-4 pb-4">
            {(post.island_pressure || []).map((il) => (
              <div
                key={il.ilha}
                className={cn(
                  "rounded-lg border p-3",
                  il.utilizacao >= 0.85
                    ? "border-rose-500/40 bg-rose-950/20"
                    : il.utilizacao <= 0.4
                      ? "border-emerald-500/30 bg-emerald-950/15"
                      : "border-slate-700"
                )}
              >
                <p className="text-xs text-slate-400">Ilha {il.ilha}</p>
                <p className="text-xl font-bold font-mono text-[#F8FAFC] tabular-nums">
                  {(il.utilizacao * 100).toFixed(0)}%
                </p>
                <p className="text-[11px] text-slate-500">
                  {il.abastecimentos_janela} abast ·{" "}
                  {il.frentistas?.join(", ") || "sem frentista"}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}

      {post && drill === "recorrencia" ? (
        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-sm text-[#F8FAFC]">
              Histórico de recorrência (últimos rushes)
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4 space-y-1">
            {Object.entries(post.drilldown?.historico_recorrencia || {}).map(
              ([nome, hits]) => (
                <div
                  key={nome}
                  className="flex justify-between text-sm border-b border-slate-800/60 py-1.5"
                >
                  <span className="text-slate-300">{nome}</span>
                  <span
                    className={cn(
                      "font-mono font-bold tabular-nums",
                      hits >= 3 ? "text-[#EF4444]" : "text-[#F8FAFC]"
                    )}
                  >
                    {hits}
                    <span className="text-slate-500 font-normal">/5</span>
                  </span>
                </div>
              )
            )}
          </CardContent>
        </Card>
      ) : null}

      {post && drill === "periodo" ? (
        <Card className="border-slate-800 bg-slate-950/40 p-4 text-sm text-slate-300">
          Período do rush:{" "}
          <strong className="text-[#F8FAFC] font-mono">{post.rush_status?.label}</strong>
          <br />
          <span className="font-mono text-xs text-slate-400">
            {post.rush_status?.start} → {post.rush_status?.end}
          </span>
          <br />
          Abastecimentos na janela:{" "}
          <span className="font-mono font-bold text-[#F8FAFC]">
            {post.rush_status?.abastecimentos}
          </span>
        </Card>
      ) : null}

      {post && drill === "frentista" ? (
        <Card className="border-slate-800 bg-slate-950/40 p-4">
          <ul className="text-sm text-slate-300 space-y-1">
            {(post.drilldown?.frentistas || []).map((f, idx) => (
              <li
                key={f}
                className={cn(
                  "flex items-center gap-2",
                  idx === 0 && "font-bold text-[#F8FAFC]"
                )}
              >
                {idx === 0 ? (
                  <Trophy size={12} className="text-amber-300" />
                ) : (
                  <span className="text-slate-600">•</span>
                )}
                {f}
              </li>
            ))}
          </ul>
        </Card>
      ) : null}
    </div>
  );
}
