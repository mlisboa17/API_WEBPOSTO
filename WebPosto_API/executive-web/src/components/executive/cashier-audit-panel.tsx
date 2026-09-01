"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Lock,
  Pencil,
  RefreshCcw,
  Wallet,
  ArrowDownCircle,
  ArrowUpCircle,
  Scale,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { apiService } from "@/lib/api";
import type {
  CashierAuditFechamento,
  CashierAuditQuebraForma,
  CashierAuditResponse,
  CashierAuditResumo,
} from "@/types/api";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 20;

const EMPTY_RESUMO: CashierAuditResumo = {
  totalEsperado: 0,
  totalDeclarado: 0,
  divergenciaTotal: 0,
  sobras: 0,
  faltas: 0,
};

async function fetchCashierAudit(
  empresaCodigo: number | undefined,
  pagina: number,
  limite: number,
  attempt = 1
): Promise<CashierAuditResponse> {
  const params = new URLSearchParams({
    pagina: String(pagina),
    limite: String(limite),
  });
  if (empresaCodigo) params.set("empresaCodigo", String(empresaCodigo));

  try {
    const res = await fetch(`/api/proxy/executive/audit/cashier?${params}`, {
      cache: "no-store",
      headers: { Accept: "application/json" },
      signal: AbortSignal.timeout(15000),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const envelope = (await res.json()) as {
      success?: boolean;
      data?: CashierAuditResponse;
      error?: string;
    } & CashierAuditResponse;

    if (envelope?.data?.resumoDia) return envelope.data;
    if (envelope?.resumoDia) return envelope;
    throw new Error(envelope?.error || "Resposta inválida da auditoria de caixas");
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    const network = /Failed to fetch|NetworkError|Load failed|fetch failed|TimeoutError|aborted/i.test(
      msg
    );
    if (network && attempt < 2) {
      await new Promise((r) => setTimeout(r, 400));
      return fetchCashierAudit(empresaCodigo, pagina, limite, attempt + 1);
    }
    if (network) {
      throw new Error(
        "Falha de rede ao carregar auditoria de caixas. Confirme API :8040 e Next :3000."
      );
    }
    throw err instanceof Error ? err : new Error(String(err));
  }
}

type Props = {
  empresaCodigo?: number;
  ready?: boolean;
};

export function CashierAuditPanel({ empresaCodigo, ready = true }: Props) {
  const [resumo, setResumo] = useState<CashierAuditResumo>(EMPTY_RESUMO);
  const [quebras, setQuebras] = useState<CashierAuditQuebraForma[]>([]);
  const [items, setItems] = useState<CashierAuditFechamento[]>([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [total, setTotal] = useState(0);
  const [meta, setMeta] = useState<{ dataRef?: string; latencyMs?: number; geradoEm?: string }>({});
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [bootMs, setBootMs] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [savingId, setSavingId] = useState<string | null>(null);
  const [adjustError, setAdjustError] = useState<string | null>(null);
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const reqSeq = useRef(0);
  const empresaRef = useRef(empresaCodigo);
  empresaRef.current = empresaCodigo;

  const formatBRL = (v: number) =>
    new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(v || 0);

  const openEdit = (f: CashierAuditFechamento) => {
    setAdjustError(null);
    setEditingId(f.id);
    setDraft({
      dinheiro_declarado: String(f.dinheiro_declarado ?? 0),
      pix_declarado: String(f.pix_declarado ?? 0),
      cartao_debito_declarado: String(f.cartao_debito_declarado ?? 0),
      cartao_credito_declarado: String(f.cartao_credito_declarado ?? 0),
      convenio_declarado: String(f.convenio_declarado ?? 0),
      observacao_auditoria: f.observacao_auditoria || "",
    });
  };

  const saveAdjust = async (id: string) => {
    setSavingId(id);
    setAdjustError(null);
    try {
      const updated = await apiService.adjustCashierAudit(id, {
        dinheiro_declarado: Number(draft.dinheiro_declarado || 0),
        pix_declarado: Number(draft.pix_declarado || 0),
        cartao_debito_declarado: Number(draft.cartao_debito_declarado || 0),
        cartao_credito_declarado: Number(draft.cartao_credito_declarado || 0),
        convenio_declarado: Number(draft.convenio_declarado || 0),
        observacao_auditoria: draft.observacao_auditoria || null,
      });
      setItems((prev) => prev.map((x) => (x.id === id ? { ...x, ...updated } : x)));
      setEditingId(null);
      // Recarrega resumo/quebras (Δ rede)
      void reload();
    } catch (err) {
      setAdjustError(err instanceof Error ? err.message : "Falha ao salvar ajuste");
    } finally {
      setSavingId(null);
    }
  };

  useEffect(() => {
    if (!ready) return;

    let cancelled = false;
    const seq = ++reqSeq.current;
    const t0 = performance.now();

    setLoading(true);
    setError(null);
    setItems([]);
    setPage(1);

    (async () => {
      try {
        console.info("[Auditoria de Caixas] fetch start", { empresaCodigo, seq });
        const data = await fetchCashierAudit(empresaCodigo, 1, PAGE_SIZE);
        if (cancelled || seq !== reqSeq.current) return;

        setResumo(data.resumoDia || EMPTY_RESUMO);
        setQuebras(data.quebrasPorFormaPagamento || []);
        setHasMore(Boolean(data.hasMore));
        setTotal(data.totalFechamentos || 0);
        setMeta({
          dataRef: data.dataRef,
          latencyMs: data.latencyMs,
          geradoEm: data.geradoEm,
        });
        setItems(data.fechamentosPorTurno || []);
        setPage(1);
        const ms = Math.round(performance.now() - t0);
        setBootMs(ms);
        console.info(
          `[Auditoria de Caixas] carregou em ${ms}ms (API ${data.latencyMs ?? "?"}ms)`
        );
      } catch (err) {
        if (cancelled || seq !== reqSeq.current) return;
        console.error("[Auditoria de Caixas] fetch erro", err);
        setError(err instanceof Error ? err.message : "Erro ao carregar auditoria de caixas");
        setItems([]);
        setResumo(EMPTY_RESUMO);
      } finally {
        if (!cancelled && seq === reqSeq.current) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [ready, empresaCodigo]);

  async function loadMore() {
    if (!hasMore || loadingMore || loading) return;
    const seq = ++reqSeq.current;
    const next = page + 1;
    setLoadingMore(true);
    try {
      const data = await fetchCashierAudit(empresaRef.current, next, PAGE_SIZE);
      if (seq !== reqSeq.current) return;
      setHasMore(Boolean(data.hasMore));
      setTotal(data.totalFechamentos || 0);
      setItems((prev) => [...prev, ...(data.fechamentosPorTurno || [])]);
      setPage(next);
    } catch (err) {
      if (seq !== reqSeq.current) return;
      setError(err instanceof Error ? err.message : "Erro ao carregar mais turnos");
    } finally {
      if (seq === reqSeq.current) setLoadingMore(false);
    }
  }

  async function reload() {
    reqSeq.current += 1;
    const seq = reqSeq.current;
    const t0 = performance.now();
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCashierAudit(empresaRef.current, 1, PAGE_SIZE);
      if (seq !== reqSeq.current) return;
      setResumo(data.resumoDia || EMPTY_RESUMO);
      setQuebras(data.quebrasPorFormaPagamento || []);
      setHasMore(Boolean(data.hasMore));
      setTotal(data.totalFechamentos || 0);
      setMeta({
        dataRef: data.dataRef,
        latencyMs: data.latencyMs,
        geradoEm: data.geradoEm,
      });
      setItems(data.fechamentosPorTurno || []);
      setPage(1);
      setBootMs(Math.round(performance.now() - t0));
    } catch (err) {
      if (seq !== reqSeq.current) return;
      setError(err instanceof Error ? err.message : "Erro ao carregar auditoria de caixas");
    } finally {
      if (seq === reqSeq.current) setLoading(false);
    }
  }

  useEffect(() => {
    if (!hasMore || loading || loadingMore) return;
    const el = sentinelRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) void loadMore();
      },
      { rootMargin: "240px" }
    );
    obs.observe(el);
    return () => obs.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasMore, loading, loadingMore, page]);

  const r = resumo || EMPTY_RESUMO;

  return (
    <div className="space-y-5 animate-in fade-in duration-300">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-xs text-slate-400">
          Cache RAM · dataRef {meta.dataRef || "—"}
          {meta.latencyMs != null ? ` · API ${meta.latencyMs.toFixed(1)}ms` : ""}
          {bootMs != null ? ` · UI ${bootMs}ms` : loading ? " · carregando…" : ""}
          {meta.geradoEm ? ` · sync ${new Date(meta.geradoEm).toLocaleTimeString("pt-BR")}` : ""}
        </div>
        <Button
          size="sm"
          variant="outline"
          className="border-slate-600 text-slate-200"
          disabled={loading}
          onClick={() => void reload()}
        >
          <RefreshCcw size={14} className={cn("mr-2", loading && "animate-spin")} />
          Atualizar
        </Button>
      </div>

      {error && (
        <Card className="border-rose-500/30 bg-rose-950/20">
          <CardContent className="pt-4 flex items-center justify-between gap-3">
            <p className="text-sm text-rose-200">{error}</p>
            <Button size="sm" variant="outline" onClick={() => void reload()}>
              Tentar novamente
            </Button>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Kpi
          icon={<Scale className="text-cyan-400" size={18} />}
          label="Total Esperado (Bico)"
          value={formatBRL(r.totalEsperado)}
          dimmed={loading && !meta.dataRef}
        />
        <Kpi
          icon={<Wallet className="text-violet-400" size={18} />}
          label="Total Declarado"
          value={formatBRL(r.totalDeclarado)}
          dimmed={loading && !meta.dataRef}
        />
        <Kpi
          icon={<AlertTriangle className="text-amber-400" size={18} />}
          label="Divergência Total"
          value={formatBRL(r.divergenciaTotal)}
          tone={Math.abs(r.divergenciaTotal) < 0.01 ? "ok" : "warn"}
          dimmed={loading && !meta.dataRef}
        />
        <Kpi
          icon={<ArrowUpCircle className="text-emerald-400" size={18} />}
          label="Sobras"
          value={formatBRL(r.sobras)}
          tone="ok"
          dimmed={loading && !meta.dataRef}
        />
        <Kpi
          icon={<ArrowDownCircle className="text-rose-400" size={18} />}
          label="Faltas"
          value={formatBRL(r.faltas)}
          tone={r.faltas > 0 ? "bad" : "neutral"}
          dimmed={loading && !meta.dataRef}
        />
      </div>

      {quebras.length > 0 && (
        <Card className="border-slate-800 bg-slate-900/80">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base text-white">
              Quebras por Forma de Pagamento
              <Badge
                variant="outline"
                className="border-slate-600 text-[10px] text-slate-400 font-normal"
              >
                <Lock size={10} className="mr-1" />
                Sistêmico somente leitura
              </Badge>
            </CardTitle>
            <CardDescription>
              Sistêmico (bico/PDV — imutável) × informado/declarado (auditável)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {quebras.map((q) => (
                <div
                  key={q.forma}
                  className="rounded-md border border-slate-800 bg-white/[0.03] px-3 py-2 text-xs"
                >
                  <p className="font-semibold text-slate-200">{q.label}</p>
                  <p className="text-slate-400 mt-1">
                    <span className="text-slate-500">Sistêmico</span>{" "}
                    {formatBRL(q.valorSistemico)} ·{" "}
                    <span className="text-violet-300/80">Declarado</span>{" "}
                    {formatBRL(q.valorInformado)}
                  </p>
                  <p
                    className={cn(
                      "font-mono mt-0.5",
                      Math.abs(q.diferenca) < 0.01 ? "text-emerald-400" : "text-amber-300"
                    )}
                  >
                    Δ {formatBRL(q.diferenca)}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {adjustError ? (
        <p className="rounded-md border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
          {adjustError}
        </p>
      ) : null}

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white">
            Fechamentos por Turno{" "}
            <span className="text-slate-500 font-normal">({total})</span>
          </h3>
        </div>

        {items.length === 0 ? (
          <Card className="border-slate-800 bg-slate-900/60">
            <CardContent className="py-10 text-center text-sm text-slate-400">
              {loading
                ? "Carregando fechamentos do cache RAM…"
                : "Nenhum fechamento no cache RAM ainda — aguarde o worker (30s) ou clique em Atualizar."}
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {items.map((f) => {
              const zerado = Math.abs(f.saldo) < 0.01;
              return (
                <Card
                  key={f.id}
                  className={cn(
                    "border transition-colors",
                    zerado
                      ? "border-emerald-500/35 bg-emerald-500/[0.07]"
                      : "border-rose-500/40 bg-rose-500/[0.08]"
                  )}
                >
                  <CardContent className="pt-4 space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="text-sm font-bold text-white">{f.operadorNome}</p>
                        <p className="text-[11px] text-slate-400">
                          {f.postoNome} · {f.turno}
                          {f.dataRef ? ` · ${f.dataRef}` : ""}
                        </p>
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-[10px]",
                            f.status === "AUDITADO"
                              ? "border-emerald-500/40 text-emerald-300"
                              : "border-amber-500/30 text-amber-300"
                          )}
                        >
                          {f.status === "AUDITADO"
                            ? "🟢 AUDITADO / APROVADO"
                            : "Pendente"}
                        </Badge>
                        {zerado ? (
                          <span className="inline-flex items-center gap-1 text-[11px] text-emerald-300 font-medium">
                            <CheckCircle2 size={12} />
                            Δ R$ 0,00
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[11px] text-rose-300 font-medium">
                            <AlertTriangle size={12} />
                            Δ {formatBRL(f.saldo)}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-[11px]">
                      <Meta
                        label="Esperado (Bico) 🔒"
                        value={formatBRL(f.faturamentoBico)}
                        className="text-slate-300"
                      />
                      <Meta label="Declarado" value={formatBRL(f.faturamentoCaixa)} />
                      <Meta
                        label="Δ (Sobra/Falta)"
                        value={formatBRL(f.saldo)}
                        className={zerado ? "text-emerald-300" : "text-rose-300"}
                      />
                    </div>
                    <div className="rounded-md border border-slate-800 bg-slate-950/50 px-2 py-1.5 text-[10px] text-slate-500">
                      <p className="mb-1 flex items-center gap-1 font-semibold uppercase tracking-wide text-slate-400">
                        <Lock size={10} /> Sistêmico (somente leitura)
                      </p>
                      <p>
                        Din {formatBRL(f.dinheiro_sistemico ?? 0)} · PIX{" "}
                        {formatBRL(f.pix_sistemico ?? 0)} · Déb{" "}
                        {formatBRL(f.cartao_debito_sistemico ?? 0)} · Créd{" "}
                        {formatBRL(f.cartao_credito_sistemico ?? 0)} · Conv{" "}
                        {formatBRL(f.convenio_sistemico ?? 0)}
                      </p>
                    </div>
                    {editingId === f.id ? (
                      <div className="space-y-2 rounded-md border border-violet-500/30 bg-violet-500/5 p-2">
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-violet-200">
                          Ajustar valores declarados
                        </p>
                        <div className="grid grid-cols-2 gap-2">
                          {(
                            [
                              ["dinheiro_declarado", "Dinheiro"],
                              ["pix_declarado", "PIX"],
                              ["cartao_debito_declarado", "Débito"],
                              ["cartao_credito_declarado", "Crédito"],
                              ["convenio_declarado", "Convênio"],
                            ] as const
                          ).map(([key, label]) => (
                            <label key={key} className="text-[10px] text-slate-400">
                              {label}
                              <input
                                type="number"
                                step="0.01"
                                min="0"
                                className="mt-0.5 w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 font-mono text-xs text-white"
                                value={draft[key] ?? "0"}
                                onChange={(e) =>
                                  setDraft((d) => ({ ...d, [key]: e.target.value }))
                                }
                              />
                            </label>
                          ))}
                        </div>
                        <label className="block text-[10px] text-slate-400">
                          Observação auditoria
                          <input
                            className="mt-0.5 w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-white"
                            value={draft.observacao_auditoria ?? ""}
                            onChange={(e) =>
                              setDraft((d) => ({
                                ...d,
                                observacao_auditoria: e.target.value,
                              }))
                            }
                          />
                        </label>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            className="bg-violet-600 text-white hover:bg-violet-500"
                            disabled={savingId === f.id}
                            onClick={() => void saveAdjust(f.id)}
                          >
                            {savingId === f.id ? "Salvando…" : "Salvar & recalcular Δ"}
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-slate-600"
                            onClick={() => setEditingId(null)}
                          >
                            Cancelar
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-[10px] text-slate-500">
                          {f.qtdAbastecimentos} abastecimentos
                          {f.ajustadoManualmente ? " · ajuste manual" : ""}
                        </p>
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-7 border-violet-500/30 text-violet-200"
                          onClick={() => openEdit(f)}
                        >
                          <Pencil size={12} className="mr-1" />
                          Ajustar declarado
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        <div ref={sentinelRef} className="h-8 flex items-center justify-center">
          {loadingMore && <span className="text-xs text-slate-500">Carregando mais…</span>}
          {!hasMore && items.length > 0 && (
            <span className="text-xs text-slate-600">Fim da lista</span>
          )}
        </div>
      </div>
    </div>
  );
}

function Kpi({
  icon,
  label,
  value,
  tone = "neutral",
  dimmed = false,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  tone?: "neutral" | "ok" | "warn" | "bad";
  dimmed?: boolean;
}) {
  return (
    <Card
      className={cn(
        "border-slate-800 bg-slate-900/80",
        tone === "ok" && "border-emerald-500/25",
        tone === "warn" && "border-amber-500/25",
        tone === "bad" && "border-rose-500/25",
        dimmed && "opacity-60"
      )}
    >
      <CardContent className="p-3 flex items-start gap-2">
        <div className="mt-0.5">{icon}</div>
        <div className="min-w-0">
          <p className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">{label}</p>
          <p className="text-sm font-bold text-white truncate">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function Meta({
  label,
  value,
  className,
}: {
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <div>
      <p className="text-[9px] uppercase text-slate-500">{label}</p>
      <p className={cn("font-mono text-slate-200", className)}>{value}</p>
    </div>
  );
}
