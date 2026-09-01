"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  RefreshCcw,
  Search,
  X,
  AlertTriangle,
  CheckCircle2,
  Pencil,
} from "lucide-react";
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
  seedItens?: ExpenseDetailItem[];
  /** Notifica o pai para refrescar KPIs/DRE após reclassificação. */
  onReclassified?: () => void;
}

type PlanoOption = {
  codigo: number;
  nome: string;
  label: string;
  hierarquia?: string;
  categoria?: string;
};

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

/** `[Código] - [NOME]` em maiúsculas. */
function planoOficialLabel(item: ExpenseDetailItem) {
  const code = item.planoContaCodigo;
  const raw = (item.planoContaOficial || item.planoConta || "").trim();
  if (code && raw) {
    const upper = raw.toUpperCase();
    if (upper.startsWith(`${code} -`) || upper.startsWith(`${code}-`)) return upper;
    // Evita "Plano 141278"
    if (/^PLANO\s+\d+$/i.test(raw)) {
      return `${code} - PLANO ${code}`;
    }
    const nome = raw.replace(/^\d+\s*[-–]\s*/, "").toUpperCase();
    return `${code} - ${nome}`;
  }
  if (code) return `${code} - PLANO ${code}`;
  return raw ? raw.toUpperCase() : "—";
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
  onReclassified,
}: ExpenseDetailModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [payload, setPayload] = useState<ExpenseDetailsResponse | null>(null);
  const [planoOptions, setPlanoOptions] = useState<PlanoOption[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftPlano, setDraftPlano] = useState<string>("");
  const [savingId, setSavingId] = useState<string | null>(null);
  const [filterPlano, setFilterPlano] = useState("");

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
    void apiService.getPlanoContasOptions().then(setPlanoOptions);
  }, [isOpen]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (editingId) {
          setEditingId(null);
          return;
        }
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen, onClose, editingId]);

  const itens = payload?.itens || [];
  const subtotal = useMemo(
    () => round2(itens.reduce((s, i) => s + (Number(i.valor) || 0), 0)),
    [itens]
  );
  const expected = round2(cardTotal);
  const matches = Math.abs(subtotal - expected) < 0.015;

  const filteredOptions = useMemo(() => {
    const q = filterPlano.trim().toLowerCase();
    const base = planoOptions.length
      ? planoOptions
      : FALLBACK_PLANOS.map((p) => ({
          codigo: p.codigo,
          nome: p.nome,
          label: `${p.codigo} - ${p.nome}`,
          categoria: p.categoria,
        }));
    if (!q) return base.slice(0, 80);
    return base
      .filter(
        (o) =>
          String(o.codigo).includes(q) ||
          o.nome.toLowerCase().includes(q) ||
          o.label.toLowerCase().includes(q)
      )
      .slice(0, 80);
  }, [planoOptions, filterPlano]);

  const confirmReclassify = async (item: ExpenseDetailItem) => {
    if (!item.id || !draftPlano) return;
    setSavingId(item.id);
    setError(null);
    const res = await apiService.reclassifyExpenseEntry(
      item.id,
      draftPlano,
      "Reclassificação via DRE Executiva",
      item.planoContaCodigo
    );
    setSavingId(null);
    if (!res.success) {
      setError(res.error || "Falha ao reclassificar");
      return;
    }
    const novoCodigo = Number(res.novo_plano_codigo || draftPlano);
    const novoLabel =
      res.plano_label ||
      `${novoCodigo} - ${(res.plano_nome || "").toUpperCase()}`.trim();
    const novaCat = (res.categoria || item.categoria || "").toUpperCase();
    const sameGroup =
      !novaCat ||
      novaCat === (categoriaKey || "").toUpperCase() ||
      novaCat === (item.categoria || "").toUpperCase();

    setPayload((prev) => {
      if (!prev) return prev;
      const nextItens = (prev.itens || [])
        .map((row) => {
          if (row.id !== item.id) return row;
          return {
            ...row,
            planoContaCodigo: novoCodigo,
            planoConta: novoLabel,
            planoContaOficial: novoLabel,
            categoria: novaCat || row.categoria,
          };
        })
        .filter((row) => {
          // Se mudou de grupo DRE, remove da lista atual (subtotal atualiza)
          if (row.id !== item.id) return true;
          return sameGroup;
        });
      const nextSub = round2(
        nextItens.reduce((s, i) => s + (Number(i.valor) || 0), 0)
      );
      return {
        ...prev,
        itens: nextItens,
        quantidade: nextItens.length,
        subtotal: nextSub,
      };
    });
    setEditingId(null);
    setDraftPlano("");
    setFilterPlano("");
    onReclassified?.();
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="bg-slate-900 border border-white/10 rounded-xl shadow-2xl w-full max-w-6xl max-h-[90vh] flex flex-col"
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
                : "border-amber-500/30 bg-amber-500/10 text-amber-200"
            )}
          >
            {matches ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
            <span>
              Soma tabela {formatBRL(subtotal)} {matches ? "=" : "≠"} card{" "}
              {formatBRL(expected)}
              {!matches ? " (após reclassificação o card atualiza no refresh)" : ""}
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
                    <th className="text-right py-2 pr-3 font-bold">Valor (R$)</th>
                    <th className="text-right py-2 font-bold">Ação</th>
                  </tr>
                </thead>
                <tbody>
                  {itens.map((item, idx) => {
                    const isEditing = editingId === item.id;
                    return (
                      <tr
                        key={`${item.id || idx}-${item.valor}`}
                        className="border-b border-white/5 hover:bg-white/[0.02]"
                      >
                        <td className="py-2.5 pr-3 text-slate-300 whitespace-nowrap align-top">
                          <div>{formatDateBR(item.dataPagamento || item.dataVencimento)}</div>
                          <div className="text-[11px] text-slate-500">{docLabel(item)}</div>
                        </td>
                        <td className="py-2.5 pr-3 text-cyan-100 max-w-[320px] align-top">
                          {isEditing ? (
                            <div className="space-y-2">
                              <input
                                value={filterPlano}
                                onChange={(e) => setFilterPlano(e.target.value)}
                                placeholder="Buscar plano…"
                                className="w-full rounded-md border border-white/10 bg-slate-950 px-2 py-1.5 text-xs text-white"
                              />
                              <select
                                value={draftPlano}
                                onChange={(e) => setDraftPlano(e.target.value)}
                                className="w-full rounded-md border border-cyan-500/40 bg-slate-950 px-2 py-1.5 text-xs text-cyan-100"
                                size={6}
                              >
                                {filteredOptions.map((o) => (
                                  <option key={o.codigo} value={String(o.codigo)}>
                                    {o.label}
                                  </option>
                                ))}
                              </select>
                              <div className="flex gap-2">
                                <Button
                                  size="sm"
                                  className="h-7 bg-cyan-500 text-slate-950 text-xs"
                                  disabled={!draftPlano || savingId === item.id}
                                  onClick={() => void confirmReclassify(item)}
                                >
                                  {savingId === item.id ? "Salvando…" : "Confirmar"}
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  className="h-7 border-white/20 text-xs"
                                  onClick={() => {
                                    setEditingId(null);
                                    setDraftPlano("");
                                    setFilterPlano("");
                                  }}
                                >
                                  Cancelar
                                </Button>
                              </div>
                            </div>
                          ) : (
                            <>
                              <p className="font-medium leading-snug uppercase tracking-tight">
                                {planoOficialLabel(item)}
                              </p>
                              <p className="text-[11px] text-slate-500 mt-0.5">
                                {[
                                  item.grupoConta ? `Grupo: ${item.grupoConta}` : null,
                                  item.centroCusto ? `CC: ${item.centroCusto}` : null,
                                ]
                                  .filter(Boolean)
                                  .join(" · ") || null}
                              </p>
                            </>
                          )}
                        </td>
                        <td className="py-2.5 pr-3 text-slate-300 max-w-[240px] align-top">
                          <p className="leading-snug">
                            {item.historico || item.descricao || "—"}
                          </p>
                        </td>
                        <td className="py-2.5 pr-3 text-slate-400 max-w-[160px] align-top">
                          {item.fornecedor || item.favorecido || "—"}
                        </td>
                        <td className="py-2.5 pr-3 text-right font-semibold text-white whitespace-nowrap align-top">
                          {formatBRL(Number(item.valor) || 0)}
                        </td>
                        <td className="py-2.5 text-right align-top">
                          {!isEditing ? (
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-7 border-amber-500/30 bg-amber-500/10 text-amber-200 text-[11px] gap-1"
                              disabled={!item.id}
                              onClick={() => {
                                setEditingId(item.id || null);
                                setDraftPlano(
                                  item.planoContaCodigo
                                    ? String(item.planoContaCodigo)
                                    : ""
                                );
                                setFilterPlano("");
                              }}
                            >
                              <Pencil size={12} />
                              Reclassificar
                            </Button>
                          ) : null}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
                <tfoot>
                  <tr className="border-t border-white/10">
                    <td
                      colSpan={5}
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
          {error ? (
            <p className="text-[11px] text-amber-400/80 mt-3 flex items-center gap-1">
              <AlertTriangle size={12} />
              {error}
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

const FALLBACK_PLANOS = [
  { codigo: 141278, nome: "MANUTENÇÃO DE MÁQUINAS E EQUIPAMENTOS", categoria: "OUTRAS" },
  { codigo: 141275, nome: "AFERIÇÃO E CALIBRAGEM", categoria: "OUTRAS" },
  { codigo: 148304, nome: "COMBUSTÍVEL DE APOIO / FROTA", categoria: "OUTRAS" },
  { codigo: 141276, nome: "MANUTENÇÃO PREDIAL / INSTALAÇÕES", categoria: "ADMINISTRATIVA" },
  { codigo: 137578, nome: "MATERIAL DE USO E CONSUMO", categoria: "ADMINISTRATIVA" },
  { codigo: 48547, nome: "VALES / BENEFÍCIOS A FUNCIONÁRIOS", categoria: "PESSOAL" },
  { codigo: 29019, nome: "COMPRAS DE MERCADORIAS / CONVENIÊNCIA", categoria: "CPV" },
];

function round2(n: number) {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}
