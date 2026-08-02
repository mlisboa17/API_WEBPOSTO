"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Fuel, RefreshCcw, Thermometer, X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { apiService } from "@/lib/api";
import type {
  CardFraudBicoDetalhe,
  CardFraudOcorrencia,
  PistaLiveBico,
  PistaLiveFilial,
  PistaLiveResponse,
} from "@/types/api";
import { cn } from "@/lib/utils";

type Props = {
  empresaCodigo?: number;
  ready?: boolean;
};

function formatBRL(v: number) {
  return (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatDataHora(raw?: string | null) {
  if (!raw) return "—";
  const d = new Date(raw.includes("T") ? raw : raw.replace(" ", "T"));
  if (Number.isNaN(d.getTime())) return raw;
  return d.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatLitros(v: number) {
  return `${(v ?? 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3,
  })} L`;
}

function Meta({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-slate-500">{label}</p>
      <p
        className={cn(
          "font-medium tabular-nums",
          highlight ? "text-amber-300" : "text-slate-100"
        )}
      >
        {value}
      </p>
    </div>
  );
}

function syntheticOcorrencia(b: PistaLiveBico): CardFraudOcorrencia {
  const detalhe: CardFraudBicoDetalhe = {
    idAbastecimento: b.idAbastecimento,
    bico: b.bico,
    bomba: b.bomba,
    dataHoraBico: b.dataHoraT1,
    horaBico: b.dataHoraT1,
    produto: b.produto,
    tipoCombustivel: b.produto,
    litros: b.litros,
    valorTotal: b.valorPendente || b.valorUltimo,
    tempoRetencaoMinutos: b.tempoRetencaoMinutos,
  };
  return {
    id: b.ocorrenciaId || `LIVE-${b.idAbastecimento}`,
    idOcorrencia: b.ocorrenciaId || `LIVE-${b.idAbastecimento}`,
    gatilho: "RETENCAO_ATIVA",
    frentistaId: b.frentistaId ?? null,
    frentistaNome: b.frentistaNome,
    funcionarioNome: b.frentistaNome,
    funcionarioId: b.frentistaId ?? null,
    empresaCodigo: b.empresaCodigo,
    empresaNome: b.empresaNome,
    postoNome: b.empresaNome,
    postoUnidade: b.empresaCodigo,
    vendaCodigo: 0,
    dataHoraBico: b.dataHoraT1,
    horaBico: b.dataHoraT1,
    dataHora: b.dataHoraT1,
    tempoRetencaoMinutos: b.tempoRetencaoMinutos,
    intervaloBicosMinutos: 0,
    qtdAbastecimentosAgrupados: 1,
    valorTotalCartao: b.valorPendente || b.valorUltimo,
    valorTotal: b.valorPendente || b.valorUltimo,
    nivelRisco: b.tempoRetencaoMinutos > 30 ? "ALTO" : "MEDIO",
    scoreGravidade: b.scoreGravidade ?? (b.tempoRetencaoMinutos > 30 ? 80 : 50),
    meioPagamento: b.formaPagamento || "PENDENTE",
    formaPagamento: b.formaPagamento || "PENDENTE",
    tipoCombustivel: b.produto,
    litros: b.litros,
    valorDesconto: 0,
    descontoPorLitro: 0,
    percentualDesconto: 0,
    origemDesconto: "SEM DESCONTO",
    motivoSuspeita: `Retenção ativa no bico ${b.bico} — T1 ${formatDataHora(b.dataHoraT1)}`,
    cartaoRepetido: Boolean(b.cartaoRepetido),
    detalhes: [detalhe],
    abastecimentosAgrupados: [detalhe],
  };
}

export function PistaLivePanel({ empresaCodigo, ready = true }: Props) {
  const [data, setData] = useState<PistaLiveResponse | null>(null);
  const [ocorrencias, setOcorrencias] = useState<CardFraudOcorrencia[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<CardFraudOcorrencia | null>(null);
  const [selectedBico, setSelectedBico] = useState<PistaLiveBico | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const today = new Date().toISOString().slice(0, 10);
      const [live, fraud] = await Promise.all([
        apiService.getPistaLive(empresaCodigo),
        apiService.getCardFraudAudit(today, today, empresaCodigo, null),
      ]);
      setData(live);
      setOcorrencias(fraud.ocorrencias || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar pista ao vivo");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [empresaCodigo]);

  useEffect(() => {
    if (!ready) return;
    void fetchData();
    const id = window.setInterval(() => void fetchData(), 15_000);
    return () => window.clearInterval(id);
  }, [fetchData, ready]);

  const filiais: PistaLiveFilial[] = data?.filiais || [];

  const openBico = useCallback(
    (b: PistaLiveBico) => {
      if (b.status !== "RETENCAO") return;
      setSelectedBico(b);
      const oid = b.ocorrenciaId;
      const matched = oid
        ? ocorrencias.find((o) => (o.idOcorrencia || o.id) === oid)
        : ocorrencias.find((o) =>
            (o.abastecimentosAgrupados || o.detalhes || []).some(
              (d) =>
                Number(d.idAbastecimento || d.abastecimentoId || 0) ===
                Number(b.idAbastecimento)
            )
          );
      setSelected(matched || syntheticOcorrencia(b));
    },
    [ocorrencias]
  );

  const closeModal = useCallback(() => {
    setSelected(null);
    setSelectedBico(null);
  }, []);

  useEffect(() => {
    if (!selected) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeModal();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selected, closeModal]);

  const syncLabel = useMemo(() => {
    if (!data?.ultimaSincronizacaoIso) return "aguardando sync";
    return formatDataHora(data.ultimaSincronizacaoIso);
  }, [data?.ultimaSincronizacaoIso]);

  if (loading && !data) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-20 w-full bg-slate-900" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-28 w-full bg-slate-900" />
          ))}
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <Card className="border-red-500/30 bg-red-500/5 p-8 text-center">
        <AlertTriangle className="mx-auto text-red-400 mb-2" />
        <p className="text-red-300 font-medium">{error}</p>
        <Button className="mt-4" variant="outline" onClick={() => void fetchData()}>
          Tentar novamente
        </Button>
      </Card>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
            <Thermometer className="text-cyan-400" size={18} />
            Pista ao Vivo / Status Bicos
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Sync RAM: {syncLabel}
            {data?.syncing ? " · sincronizando…" : ""} · refresh 15s
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge className="bg-emerald-500/15 text-emerald-300 border-emerald-500/30">
            {Math.max(0, (data?.totalBicos || 0) - (data?.totalRetencoes || 0))} normais
          </Badge>
          <Badge className="bg-rose-500/20 text-rose-200 border-rose-500/40 animate-pulse">
            {data?.totalRetencoes || 0} retenções
          </Badge>
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
      </div>

      {filiais.length === 0 ? (
        <Card className="border-slate-800 bg-slate-950/60 p-8 text-center">
          <Fuel className="mx-auto text-slate-600 mb-2" />
          <p className="text-slate-400 text-sm">
            Nenhum bico no cache da filial selecionada. Aguarde o PistaSyncWorker (~30s).
          </p>
        </Card>
      ) : (
        filiais.map((filial) => (
          <section key={filial.empresaCodigo} className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-cyan-200">
                {filial.empresaNome}{" "}
                <span className="text-slate-500 font-normal">
                  ({filial.empresaCodigo})
                </span>
              </h3>
              <span className="text-xs text-slate-500">
                {filial.totalBicos} bicos · {filial.totalRetencoes} retidos
              </span>
            </div>

            {filial.ilhas.map((ilha) => (
              <Card
                key={`${filial.empresaCodigo}-ilha-${ilha.ilha}`}
                className="border-slate-800 bg-slate-950/50"
              >
                <CardHeader className="py-3 px-4">
                  <CardTitle className="text-sm text-slate-200 flex items-center gap-2">
                    {ilha.label}
                    {ilha.retencoes > 0 ? (
                      <Badge className="text-[10px] bg-rose-600/30 text-rose-200 border-rose-500/40 animate-pulse">
                        {ilha.retencoes} alerta{ilha.retencoes > 1 ? "s" : ""}
                      </Badge>
                    ) : (
                      <Badge className="text-[10px] bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
                        operação regular
                      </Badge>
                    )}
                  </CardTitle>
                </CardHeader>
                <CardContent className="px-4 pb-4 space-y-4">
                  {ilha.bombas.map((bomba) => (
                    <div key={bomba.bomba}>
                      <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-2">
                        Bomba {String(bomba.bomba).padStart(2, "0")}
                      </p>
                      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2">
                        {bomba.bicos.map((b) => {
                          const alert = b.status === "RETENCAO";
                          return (
                            <button
                              key={`${b.empresaCodigo}-${b.bico}-${b.idAbastecimento}`}
                              type="button"
                              disabled={!alert}
                              onClick={() => openBico(b)}
                              className={cn(
                                "rounded-lg border p-3 text-left transition-all",
                                alert
                                  ? "border-rose-500/70 bg-rose-950/50 shadow-[0_0_18px_rgba(244,63,94,0.35)] animate-pulse cursor-pointer hover:bg-rose-900/40"
                                  : "border-emerald-500/30 bg-emerald-950/20 cursor-default opacity-90"
                              )}
                              title={
                                alert
                                  ? "Abrir modal de auditoria"
                                  : "Operação regular"
                              }
                            >
                              <div className="flex items-center justify-between gap-1">
                                <span className="text-xs font-bold text-white">
                                  Bico {String(b.bico).padStart(2, "0")}
                                </span>
                                <span
                                  className={cn(
                                    "h-2.5 w-2.5 rounded-full",
                                    alert
                                      ? "bg-rose-400 shadow-[0_0_8px_#f43f5e]"
                                      : "bg-emerald-400"
                                  )}
                                />
                              </div>
                              {alert ? (
                                <div className="mt-2 space-y-0.5 text-[11px] leading-snug">
                                  <p className="text-rose-100 font-medium">
                                    {formatBRL(b.valorPendente)}
                                  </p>
                                  <p className="text-rose-200/80">
                                    T₁ {formatDataHora(b.dataHoraT1)}
                                  </p>
                                  <p className="text-slate-300 truncate">
                                    {b.frentistaNome}
                                  </p>
                                  <p className="text-amber-300/90">
                                    {b.tempoRetencaoMinutos} min retido
                                  </p>
                                </div>
                              ) : (
                                <p className="mt-2 text-[11px] text-emerald-300/80">
                                  Liberado
                                </p>
                              )}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            ))}
          </section>
        ))
      )}

      {selected && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          onClick={closeModal}
          role="presentation"
        >
          <Card
            className="w-full max-w-3xl max-h-[90vh] overflow-y-auto border border-rose-500/40 bg-slate-900"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
          >
            <CardHeader className="flex flex-row items-start justify-between gap-3 sticky top-0 bg-slate-900/95 z-10 border-b border-slate-800">
              <div>
                <CardTitle className="text-lg text-white">
                  Auditoria — Bico{" "}
                  {selectedBico
                    ? String(selectedBico.bico).padStart(2, "0")
                    : "—"}
                </CardTitle>
                <p className="text-xs text-slate-400 mt-1">
                  #{selected.idOcorrencia || selected.id} ·{" "}
                  {selected.funcionarioNome || selected.frentistaNome} ·{" "}
                  {selected.postoNome || selected.empresaNome}
                </p>
              </div>
              <Button size="sm" variant="outline" onClick={closeModal}>
                <X size={14} className="mr-1" /> Fechar
              </Button>
            </CardHeader>
            <CardContent className="space-y-4 pt-4">
              <div className="rounded-lg border border-rose-500/30 bg-rose-950/20 px-4 py-3">
                <p className="text-[10px] uppercase tracking-wider text-rose-300 font-bold mb-2">
                  Campos de prova (pista ao vivo)
                </p>
                <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 text-sm">
                  <Meta label="1. Filial" value={selected.postoNome || selected.empresaNome || "—"} />
                  <Meta
                    label="2. Frentista"
                    value={selected.funcionarioNome || selected.frentistaNome || "—"}
                  />
                  <Meta
                    label="3. Data/Hora T₁ (Bico)"
                    value={formatDataHora(
                      selected.dataHoraBico || selected.horaBico || selected.dataHora
                    )}
                  />
                  <Meta
                    label="4. Data/Hora Baixa"
                    value={formatDataHora(
                      selected.dataHoraBaixa || selected.horaBaixa || "—"
                    )}
                  />
                  <Meta
                    label="5. Retenção"
                    value={`${selected.tempoRetencaoMinutos} min`}
                    highlight={(selected.tempoRetencaoMinutos ?? 0) > 30}
                  />
                  <Meta
                    label="6. Valor (R$)"
                    value={formatBRL(selected.valorTotal ?? selected.valorTotalCartao)}
                  />
                  <Meta label="7. Litros" value={formatLitros(selected.litros ?? 0)} />
                  <Meta
                    label="8. Combustível"
                    value={selected.tipoCombustivel || selectedBico?.produto || "—"}
                  />
                  <Meta
                    label="9. Forma pagamento"
                    value={selected.formaPagamento || selected.meioPagamento || "—"}
                  />
                  <Meta
                    label="10. Cartão / Final"
                    value={
                      selected.cartaoBandeira || selected.cartaoFinal
                        ? `${selected.cartaoBandeira || "—"} · ****${(
                            selected.cartaoFinal || ""
                          )
                            .replace(/\D/g, "")
                            .slice(-4) || "----"}`
                        : "—"
                    }
                  />
                  <Meta label="11. NSU" value={selected.cartaoNsu || "—"} />
                  <Meta
                    label="12. Score"
                    value={`${selected.scoreGravidade ?? 0}/100`}
                    highlight={(selected.scoreGravidade ?? 0) >= 100}
                  />
                  <Meta
                    label="13. Motivo"
                    value={selected.motivoSuspeita || selected.gatilho || "—"}
                  />
                </div>
              </div>
              {(selected.abastecimentosAgrupados || selected.detalhes || []).length >
                0 && (
                <div className="rounded-lg border border-slate-700 px-3 py-2">
                  <p className="text-[10px] uppercase text-slate-500 mb-2">
                    Abastecimentos agrupados
                  </p>
                  <ul className="space-y-1 text-xs text-slate-300">
                    {(selected.abastecimentosAgrupados || selected.detalhes || []).map(
                      (d, i) => (
                        <li key={i} className="flex justify-between gap-2">
                          <span>
                            Bico {d.bico} · {d.produto || d.tipoCombustivel || "—"}
                          </span>
                          <span className="tabular-nums">
                            {formatBRL(d.valorTotal ?? d.valor ?? 0)}
                          </span>
                        </li>
                      )
                    )}
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
