"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, RefreshCcw, Search, X, AlertTriangle, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiService } from "@/lib/api";
import type { ExpenseDetailItem, ExpenseDetailsResponse } from "@/types/api";
import { cn } from "@/lib/utils";

export interface ExpenseDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  empresaCodigo: number;
  empresaNome: string;
  categoria: string;
  categoriaKey: string;
  cardTotal: number;
  periodStart: string;
  periodEnd: string;
  /** Itens já embutidos no payload do data-audit (fallback imediato). */
  seedItens?: ExpenseDetailItem[];
}

function formatBRL(v: number) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(v || 0);
}

function formatDateBR(iso: string | undefined) {
  if (!iso) return "—";
  const d = iso.slice(0, 10);
  const [y, m, day] = d.split("-");
  if (!y || !m || !day) return iso;
  return `${day}/${m}/${y}`;
}

function docLabel(item: ExpenseDetailItem) {
  const parts: string[] = [];
  if (item.numeroNF) parts.push(`NF ${item.numeroNF}`);
  if (item.numeroDocumento) parts.push(`Doc ${item.numeroDocumento}`);
  return parts.length ? parts.join(" · ") : "—";
}

function planoOficialLabel(item: ExpenseDetailItem) {
  return (
    item.planoContaOficial ||
    item.planoConta ||
    (item.planoContaCodigo ? `Plano ${item.planoContaCodigo}` : "—")
  );
}

export function ExpenseDetailModal({
  isOpen,
  onClose,
  empresaCodigo,
  empresaNome,
  categoria,
  categoriaKey,
  cardTotal,
  periodStart,
  periodEnd,
  seedItens = [],
}: ExpenseDetailModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [payload, setPayload] = useState<ExpenseDetailsResponse | null>(null);

  const fetchDetails = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await apiService.getExpenseDetails(
        periodStart,
        periodEnd,
        categoriaKey || categoria,
        empresaCodigo
      );
      if (result.success === false && !(result.itens && result.itens.length)) {
        setPayload({
          ...result,
          itens: seedItens,
          subtotal: cardTotal,
          quantidade: seedItens.length,
          categoria,
          categoriaKey,
        });
        if (result.mensagem) setError(result.mensagem);
      } else {
        setPayload(result);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar detalhes");
      setPayload({
        empresaCodigo,
        empresaNome,
        periodo: { inicio: periodStart, fim: periodEnd },
        categoria,
        categoriaKey,
        subtotal: cardTotal,
        quantidade: seedItens.length,
        itens: seedItens,
        success: false,
      });
    } finally {
      setLoading(false);
    }
  }, [
    periodStart,
    periodEnd,
    categoriaKey,
    categoria,
    empresaCodigo,
    empresaNome,
    cardTotal,
    seedItens,
  ]);

  useEffect(() => {
    if (!isOpen) return;
    if (seedItens.length) {
      setPayload({
        empresaCodigo,
        empresaNome,
        periodo: { inicio: periodStart, fim: periodEnd },
        categoria,
        categoriaKey,
        subtotal: cardTotal,
        quantidade: seedItens.length,
        itens: seedItens,
        success: true,
      });
    }
    void fetchDetails();
  }, [isOpen]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen, onClose]);

  const itens = payload?.itens || [];
  const subtotal = useMemo(
    () => round2(itens.reduce((s, i) => s + (Number(i.valor) || 0), 0)),
    [itens]
  );
  const expected = round2(cardTotal);
  const matches = Math.abs(subtotal - expected) < 0.015;

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="bg-slate-900 border border-white/10 rounded-xl shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={`Detalhes ${categoria}`}
      >
        <div className="p-5 border-b border-white/5 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <Search size={14} className="text-cyan-400 shrink-0" />
              <span className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">
                Drill-down Plano de Contas webPosto
              </span>
            </div>
            <h2 className="text-lg font-bold text-white leading-tight truncate">
              {payload?.categoria || categoria}
            </h2>
            <p className="text-sm text-slate-400 mt-0.5">
              {empresaNome} ({empresaCodigo}) • {formatDateBR(periodStart)}
              {periodEnd !== periodStart ? ` → ${formatDateBR(periodEnd)}` : ""}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => void fetchDetails()}
              disabled={loading}
              className="bg-cyan-500/10 border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20"
              title="Atualizar"
            >
              <RefreshCcw size={14} className={cn(loading && "animate-spin")} />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={onClose}
              className="border-white/20 bg-white/5 text-white hover:bg-white/10 gap-1.5"
            >
              <ArrowLeft size={14} />
              Voltar
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={onClose}
              className="bg-slate-100 text-slate-900 hover:bg-white gap-1.5 font-semibold"
            >
              <X size={14} />
              Fechar
            </Button>
          </div>
        </div>

        <div className="px-5 py-3 border-b border-white/5 flex flex-wrap items-center gap-3 justify-between">
          <div>
            <p className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">
              Subtotal do grupo
            </p>
            <p className="text-xl font-bold text-amber-300">{formatBRL(subtotal)}</p>
            <p className="text-[11px] text-slate-500">
              {itens.length} lançamento{itens.length === 1 ? "" : "s"}
            </p>
          </div>
          <div
            className={cn(
              "flex items-center gap-2 rounded-md border px-3 py-2 text-xs",
              matches
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                : "border-red-500/30 bg-red-500/10 text-red-300"
            )}
          >
            {matches ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
            <span>
              Soma tabela {formatBRL(subtotal)} {matches ? "=" : "≠"} card{" "}
              {formatBRL(expected)}
            </span>
          </div>
        </div>

        <div className="flex-1 overflow-auto p-5">
          {loading && itens.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 gap-3">
              <RefreshCcw className="animate-spin text-cyan-400" size={28} />
              <p className="text-slate-400 text-sm">Carregando lançamentos…</p>
            </div>
          ) : itens.length === 0 ? (
            <div className="text-center py-16 text-slate-500 text-sm">
              {error || "Nenhum lançamento nesta categoria para o período."}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-[10px] uppercase tracking-wider text-slate-500 border-b border-white/5">
                    <th className="text-left py-2 pr-3 font-bold">Data / Docs</th>
                    <th className="text-left py-2 pr-3 font-bold">Plano de Contas webPosto</th>
                    <th className="text-left py-2 pr-3 font-bold">Histórico</th>
                    <th className="text-left py-2 pr-3 font-bold">Fornecedor / Favorecido</th>
                    <th className="text-right py-2 font-bold">Valor (R$)</th>
                  </tr>
                </thead>
                <tbody>
                  {itens.map((item, idx) => (
                    <tr
                      key={`${item.id || idx}-${item.valor}`}
                      className="border-b border-white/5 hover:bg-white/[0.02]"
                    >
                      <td className="py-2.5 pr-3 text-slate-300 whitespace-nowrap align-top">
                        <div>{formatDateBR(item.dataPagamento || item.dataVencimento)}</div>
                        <div className="text-[11px] text-slate-500">{docLabel(item)}</div>
                      </td>
                      <td className="py-2.5 pr-3 text-cyan-100 max-w-[260px] align-top">
                        <p className="font-medium leading-snug">{planoOficialLabel(item)}</p>
                        <p className="text-[11px] text-slate-500 mt-0.5">
                          {[
                            item.planoContaCodigo ? `cód. ${item.planoContaCodigo}` : null,
                            item.grupoConta ? `Grupo: ${item.grupoConta}` : null,
                            item.centroCusto ? `CC: ${item.centroCusto}` : null,
                          ]
                            .filter(Boolean)
                            .join(" · ") || null}
                        </p>
                      </td>
                      <td className="py-2.5 pr-3 text-slate-300 max-w-[280px] align-top">
                        <p className="leading-snug">
                          {item.historico || item.descricao || "—"}
                        </p>
                      </td>
                      <td className="py-2.5 pr-3 text-slate-400 max-w-[180px] align-top">
                        {item.fornecedor || item.favorecido || "—"}
                      </td>
                      <td className="py-2.5 text-right font-semibold text-white whitespace-nowrap align-top">
                        {formatBRL(Number(item.valor) || 0)}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t border-white/10">
                    <td
                      colSpan={4}
                      className="py-3 text-right text-slate-400 text-xs font-bold uppercase tracking-wider"
                    >
                      Total
                    </td>
                    <td className="py-3 text-right font-bold text-amber-300">
                      {formatBRL(subtotal)}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          )}
          {error && itens.length > 0 ? (
            <p className="text-[11px] text-amber-400/80 mt-3 flex items-center gap-1">
              <AlertTriangle size={12} />
              API: {error} — exibindo itens do consolidado.
            </p>
          ) : null}
        </div>

        <div className="p-4 border-t border-white/5 flex justify-end gap-2">
          <Button
            variant="outline"
            onClick={onClose}
            className="border-white/20 text-slate-200 hover:bg-white/10 gap-1.5"
          >
            <ArrowLeft size={14} />
            Voltar
          </Button>
          <Button
            onClick={onClose}
            className="bg-cyan-500 text-slate-950 hover:bg-cyan-400 font-semibold gap-1.5"
          >
            <X size={14} />
            Fechar
          </Button>
        </div>
      </div>
    </div>
  );
}

function round2(n: number) {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}
