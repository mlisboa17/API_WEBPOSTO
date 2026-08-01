"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  CreditCard,
  ExternalLink,
  RefreshCcw,
  Settings2,
  ShieldAlert,
  X,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { InfoTooltip } from "@/components/ui/info-tooltip";
import { apiService } from "@/lib/api";
import type {
  AuditFraudSettings,
  CardFraudAuditResponse,
  CardFraudBicoDetalhe,
  CardFraudOcorrencia,
} from "@/types/api";
import { cn } from "@/lib/utils";

interface Props {
  start: string;
  end: string;
  empresaCodigo?: number;
  periodReady: boolean;
}

function formatBRL(v: number) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(v || 0);
}

function formatLitros(v: number) {
  return `${(v ?? 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3,
  })} L`;
}

function formatHora(iso?: string) {
  if (!iso) return "—";
  if (iso.includes("T")) return iso.split("T")[1]?.slice(0, 8) || iso;
  if (iso.includes(" ")) return iso.split(" ")[1]?.slice(0, 8) || iso;
  return iso.slice(0, 8);
}

function formatDataHora(iso?: string) {
  if (!iso) return "—";
  const raw = iso.trim();
  const [datePart, timePart] = raw.includes("T")
    ? raw.split("T")
    : raw.includes(" ")
      ? raw.split(" ")
      : [raw, ""];
  const d = datePart?.slice(0, 10) || "";
  const t = (timePart || "").slice(0, 8);
  if (d && t) {
    const [y, m, day] = d.split("-");
    return `${day}/${m}/${y} ${t}`;
  }
  return formatHora(iso);
}

function bicoBombaLabel(d: CardFraudBicoDetalhe) {
  const bico = String(d.bico ?? 0).padStart(2, "0");
  const bomba =
    d.bomba && d.bomba > 0
      ? String(d.bomba).padStart(2, "0")
      : String(Math.floor((Math.max(1, d.bico || 1) - 1) / 2) + 1).padStart(2, "0");
  return `Bico ${bico} - Bomba ${bomba}`;
}

function riskTone(nivel: string, score?: number) {
  const n = (nivel || "").toUpperCase();
  if (n === "ALTO" || n === "CRITICO" || n === "CRÍTICO") {
    return {
      label: score != null ? `CRÍTICO · ${score}` : "CRÍTICO",
      badge: "bg-rose-950/80 text-rose-400 border-rose-500/40",
      card: "border-rose-500/40 bg-rose-950/20",
      rank: 0,
    };
  }
  if (n === "DESCONTO") {
    return {
      label: score != null ? `DESCONTO · ${score}` : "DESCONTO/APP",
      badge: "bg-orange-950/80 text-orange-400 border-orange-500/40",
      card: "border-orange-500/40 bg-orange-950/15",
      rank: 1,
    };
  }
  if (n === "MEDIO" || n === "MÉDIO" || n === "ATENCAO" || n === "ATENÇÃO") {
    return {
      label: score != null ? `MÉDIO · ${score}` : "MÉDIO",
      badge: "bg-amber-950/80 text-amber-400 border-amber-500/40",
      card: "border-amber-500/30 bg-amber-950/10",
      rank: 2,
    };
  }
  return {
    label: score != null ? `BAIXO · ${score}` : "BAIXO",
    badge: "bg-slate-800 text-slate-300 border-slate-600",
    card: "border-slate-700 bg-slate-900/60",
    rank: 3,
  };
}

function detalhesOf(o: CardFraudOcorrencia): CardFraudBicoDetalhe[] {
  if (o.abastecimentosAgrupados?.length) return o.abastecimentosAgrupados;
  return o.detalhes || [];
}

/** Normaliza forma/bandeira/final — formato: 💳 [forma] • [bandeira] Final [xxxx]. */
function pagamentoInfo(o: CardFraudOcorrencia) {
  const forma =
    (o.formaPagamento || o.meioPagamento || "").trim() || "Não informado";
  const upper = `${forma} ${o.meioPagamento || ""} ${o.cartaoBandeira || ""}`.toUpperCase();
  const isPix = upper.includes("PIX");
  const isCash =
    !!o.isEspecie ||
    /\bDINHEIRO\b|\bESP[EÉ]CIE\b|\bCASH\b/.test(upper);

  let bandeira = (o.cartaoBandeira || "").trim();
  if (/^n\/?i$/i.test(bandeira) || bandeira === "—" || bandeira === "-") {
    bandeira = "";
  }
  if (!bandeira || /^cart[aã]o\/tef$/i.test(bandeira)) {
    if (isPix) bandeira = "PIX";
    else if (isCash) bandeira = "—";
    else {
      for (const name of [
        "VISA",
        "MAESTRO",
        "MASTERCARD",
        "MASTER",
        "ELO",
        "HIPER",
        "AMEX",
        "PREMMIA",
      ]) {
        if (upper.includes(name)) {
          bandeira =
            name === "MASTER" || name === "MASTERCARD"
              ? "Mastercard"
              : name.charAt(0) + name.slice(1).toLowerCase();
          break;
        }
      }
    }
  }
  if (!bandeira) bandeira = isPix ? "PIX" : isCash ? "—" : "—";

  const finalDigits =
    (o.cartaoFinal || "").replace(/\D/g, "").slice(-4) ||
    ((o.meioPagamento || "").match(/\d{4}\s*$/) || [])[0]?.replace(/\D/g, "") ||
    "";
  const finalLabel = finalDigits || (isPix || isCash ? "—" : "****");

  const linha =
    isCash
      ? `💵 ${forma}`
      : isPix
        ? `⚡ PIX${finalDigits ? ` · Final ${finalDigits}` : ""}`
        : `💳 ${forma} • ${bandeira}${finalDigits ? ` Final ${finalDigits}` : ""}`;
  return { forma, bandeira, finalDigits: finalLabel, linha, isPix, isCash };
}

function PagamentoBlock({ o }: { o: CardFraudOcorrencia }) {
  const { linha, forma, bandeira, finalDigits, isPix, isCash } = pagamentoInfo(o);
  return (
    <div className="rounded-md border border-cyan-500/20 bg-cyan-950/20 px-3 py-2.5 space-y-1.5">
      <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-cyan-400/90 font-bold">
        <CreditCard size={12} />
        Dados de Pagamento
      </div>
      <p className="text-sm text-slate-100 font-medium font-mono tracking-tight">{linha}</p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[11px] text-slate-400">
        <span>
          Forma: <strong className="text-slate-200">{forma}</strong>
        </span>
        <span>
          {isPix ? "Canal" : isCash ? "Espécie" : "Bandeira"}:{" "}
          <strong className="text-slate-200">{bandeira}</strong>
        </span>
        {!isCash && !isPix ? (
          <span>
            Final: <strong className="text-slate-200 font-mono">{finalDigits}</strong>
          </span>
        ) : null}
        {o.cartaoNsu ? (
          <span>
            NSU: <strong className="text-slate-200 font-mono">{o.cartaoNsu}</strong>
          </span>
        ) : null}
        {o.cartaoAutorizacao ? (
          <span>
            Autorização:{" "}
            <strong className="text-slate-200 font-mono">{o.cartaoAutorizacao}</strong>
          </span>
        ) : null}
      </div>
    </div>
  );
}

const DEFAULT_SETTINGS: AuditFraudSettings = {
  empresa_id: 0,
  tempo_retencao_critico_min: 30,
  tempo_retencao_atencao_min: 15,
  tempo_agrupamento_max_min: 15,
  percentual_desconto_suspeito_pct: 10,
  recorrencia_cpf_cartao_limite: 3,
};

export function CardFraudAuditPanel({ start, end, empresaCodigo, periodReady }: Props) {
  const [data, setData] = useState<CardFraudAuditResponse | null>(null);
  const [settings, setSettings] = useState<AuditFraudSettings>(DEFAULT_SETTINGS);
  const [draft, setDraft] = useState<AuditFraudSettings>(DEFAULT_SETTINGS);
  const [showSettings, setShowSettings] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<CardFraudOcorrencia | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [result, cfg] = await Promise.all([
        apiService.getCardFraudAudit(start, end, empresaCodigo, null),
        apiService.getAuditFraudSettings(empresaCodigo ?? 0),
      ]);
      setData(result);
      setSettings(cfg);
      setDraft(cfg);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar auditoria anti-fraude");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [start, end, empresaCodigo]);

  useEffect(() => {
    if (!periodReady) return;
    void fetchData();
  }, [fetchData, periodReady]);

  const closeOccurrence = useCallback(() => setSelected(null), []);
  const closeSettings = useCallback(() => setShowSettings(false), []);

  useEffect(() => {
    if (!selected && !showSettings) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (selected) closeOccurrence();
        else if (showSettings) closeSettings();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selected, showSettings, closeOccurrence, closeSettings]);

  const saveSettings = async () => {
    setSaving(true);
    try {
      const saved = await apiService.saveAuditFraudSettings({
        ...draft,
        empresa_id: empresaCodigo ?? 0,
      });
      setSettings(saved);
      setDraft(saved);
      setShowSettings(false);
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao salvar parâmetros");
    } finally {
      setSaving(false);
    }
  };

  const resumo = data?.resumoExecutivo || data?.resumo;
  const banner = data?.bannerAlerta;
  const dist = resumo?.distribuicaoRisco || {
    ALTO: resumo?.totalCriticos ?? 0,
    DESCONTO: 0,
    MEDIO: resumo?.totalAtencao ?? 0,
    BAIXO: 0,
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <ShieldAlert className="text-rose-400" size={20} />
            Auditoria Anti-Fraude de Pista
            <InfoTooltip content="Thresholds dinâmicos (settings). Retenção crítica/atenção, agrupamento, desconto e recorrência de cartão. Fonte: cache RAM / baixados REST v1." />
          </h2>
          <div className="text-xs text-slate-300 flex items-center gap-2 flex-wrap mt-1">
            Crítico &gt; {settings.tempo_retencao_critico_min} min · Atenção &gt;{" "}
            {settings.tempo_retencao_atencao_min} min · Agrup. &gt;{" "}
            {settings.tempo_agrupamento_max_min} min
            {data?.fonte && (
              <Badge className="bg-emerald-500/15 text-emerald-300 border-emerald-500/30 text-[10px]">
                {data.fonte}
              </Badge>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              setDraft(settings);
              setShowSettings(true);
            }}
            className="border-violet-500/40 text-violet-300 hover:bg-violet-500/10"
          >
            <Settings2 size={14} className="mr-2" />
            Parâmetros de Auditoria
          </Button>
          <Button
            size="sm"
            onClick={() => void fetchData()}
            disabled={loading}
            className="bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20"
          >
            <RefreshCcw size={14} className={cn("mr-2", loading && "animate-spin")} />
            Atualizar
          </Button>
        </div>
      </div>

      {banner && (
        <div className="rounded-lg border border-red-500/40 bg-gradient-to-r from-red-500/20 to-amber-500/10 px-4 py-3 flex items-start gap-3">
          <AlertTriangle className="text-red-400 shrink-0 mt-0.5" size={20} />
          <p className="text-sm font-semibold text-red-100 leading-relaxed">⚠️ {banner}</p>
        </div>
      )}

      {loading && !data ? (
        <div className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-24 bg-slate-800" />
            ))}
          </div>
          <Skeleton className="h-64 bg-slate-800" />
        </div>
      ) : error && !data ? (
        <Card className="border-red-500/30 bg-red-500/5 p-6 text-center">
          <p className="text-red-300">{error}</p>
          <Button className="mt-3" variant="outline" onClick={() => void fetchData()}>
            Tentar novamente
          </Button>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
            <Kpi
              label="Total Fraudes"
              value={String(resumo?.totalFraudes ?? resumo?.totalAgrupamentosSuspeitos ?? 0)}
              sub={`🔴${dist.ALTO ?? 0} · 🟧${dist.DESCONTO ?? 0} · 🟡${dist.MEDIO ?? 0} · 🟢${dist.BAIXO ?? 0}`}
            />
            <Kpi
              label="Valor Envolvido"
              value={formatBRL(resumo?.valorTotalEnvolvido ?? resumo?.valorTotalRetidoCartoes ?? 0)}
              sub={`Crítico: ${formatBRL(resumo?.valorCritico ?? 0)}`}
            />
            <Kpi
              label="Abast. Suspeitos"
              value={String(
                resumo?.totalAbastecimentosSuspeitos ??
                  resumo?.abastecimentosCriticosBanner ??
                  0
              )}
              sub={`Descontos: ${formatBRL(resumo?.totalDescontosIdentificados ?? 0)}`}
            />
            <Kpi
              label="Top Frentista"
              value={resumo?.frentistaMaiorIncidencia || "—"}
              sub={`${resumo?.frentistaMaiorIncidenciaQtd ?? 0} ocorrência(s)`}
            />
          </div>

          {(resumo?.rankingFrentistas?.length ||
            resumo?.rankingPostos?.length ||
            resumo?.rankingCartoes?.length) && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <Ranking title="Top Frentistas" items={resumo?.rankingFrentistas || []} />
              <Ranking title="Top Postos" items={resumo?.rankingPostos || []} />
              <Ranking title="Top Cartões" items={resumo?.rankingCartoes || []} />
            </div>
          )}

          <div className="space-y-3">
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">
              Ocorrências ({data?.ocorrencias?.length ?? 0})
            </h3>
            {!data?.ocorrencias?.length ? (
              <Card className="border-slate-700/50 bg-slate-900/60 p-8 text-center text-slate-300 text-sm">
                Nenhuma anomalia acima dos limiares configurados no período.
              </Card>
            ) : (
              data.ocorrencias.map((o) => {
                const id = o.idOcorrencia || o.id;
                const tone = riskTone(o.nivelRisco, o.scoreGravidade);
                const rows = detalhesOf(o);
                const nome = o.funcionarioNome || o.frentistaNome;
                const valor = o.valorTotal ?? o.valorTotalCartao;
                return (
                  <Card key={id} className={cn("border", tone.card)}>
                    <CardContent className="pt-4 space-y-3">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div>
                          <p className="text-base font-bold text-white">
                            🚨 POSSÍVEL FRAUDE #{id}
                          </p>
                          <p className="text-xs text-slate-300 mt-1">
                            {nome} · {o.postoNome || o.empresaNome}
                            {o.cpfRepetido ? (
                              <span className="ml-2 text-orange-400 font-semibold">
                                · CPF/App repetido
                              </span>
                            ) : null}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge className={cn("text-[10px] border", tone.badge)}>
                            {tone.label}
                          </Badge>
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 text-xs border-cyan-500/40 text-cyan-300"
                            onClick={() => setSelected(o)}
                          >
                            <ExternalLink size={12} className="mr-1" />
                            Abrir Ocorrência #{id}
                          </Button>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs">
                        <Meta
                          label="Emissão cupom"
                          value={formatDataHora(
                            o.dataHoraEmissaoCupom || o.dataHoraBaixa || o.horaBaixa
                          )}
                        />
                        <Meta
                          label="1º bico"
                          value={formatHora(o.dataHoraBico || o.dataHora || o.horaBico)}
                        />
                        <Meta label="Retenção" value={`${o.tempoRetencaoMinutos} min`} />
                        <Meta label="Valor" value={formatBRL(valor)} />
                        <Meta
                          label="Desconto App"
                          value={formatBRL(o.valorDesconto ?? 0)}
                          highlight={!!o.cpfRepetido || (o.valorDesconto ?? 0) > 0}
                        />
                      </div>

                      <PagamentoBlock o={o} />

                      {rows.length > 0 && (
                        <BicosTable rows={rows} postoFallback={o.postoNome || o.empresaNome} compact />
                      )}

                      <div className="rounded-md border border-slate-700/50 bg-slate-950/40 px-3 py-2 text-xs text-slate-200">
                        <span className="font-bold text-amber-300">Motivo: </span>
                        {o.motivoSuspeita || o.gatilho || "Anomalia detectada"}
                      </div>
                    </CardContent>
                  </Card>
                );
              })
            )}
          </div>
        </>
      )}

      {showSettings && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          onClick={closeSettings}
          role="presentation"
        >
          <Card
            className="w-full max-w-lg border-violet-500/30 bg-slate-900"
            onClick={(e) => e.stopPropagation()}
          >
            <CardHeader className="flex flex-row items-start justify-between pb-2">
              <div>
                <CardTitle className="text-white flex items-center gap-2">
                  <Settings2 size={18} className="text-violet-400" />
                  Parâmetros de Auditoria
                </CardTitle>
                <p className="text-xs text-slate-300 mt-1">
                  Thresholds dinâmicos — salvar recalcula as regras na próxima carga.
                </p>
              </div>
              <Button
                size="sm"
                variant="outline"
                className="border-slate-600 text-slate-200"
                onClick={closeSettings}
                aria-label="Fechar"
              >
                ✕ Fechar
              </Button>
            </CardHeader>
            <CardContent className="space-y-3">
              <Field
                label="Tempo Crítico (min)"
                value={draft.tempo_retencao_critico_min}
                onChange={(v) => setDraft({ ...draft, tempo_retencao_critico_min: v })}
              />
              <Field
                label="Tempo Atenção (min)"
                value={draft.tempo_retencao_atencao_min}
                onChange={(v) => setDraft({ ...draft, tempo_retencao_atencao_min: v })}
              />
              <Field
                label="Janela Agrupamento (min)"
                value={draft.tempo_agrupamento_max_min}
                onChange={(v) => setDraft({ ...draft, tempo_agrupamento_max_min: v })}
              />
              <Field
                label="Desconto Suspeito (%)"
                value={draft.percentual_desconto_suspeito_pct}
                step={0.5}
                onChange={(v) => setDraft({ ...draft, percentual_desconto_suspeito_pct: v })}
              />
              <Field
                label="Recorrência CPF/Cartão (qtd)"
                value={draft.recorrencia_cpf_cartao_limite}
                onChange={(v) => setDraft({ ...draft, recorrencia_cpf_cartao_limite: v })}
              />
              <Button
                className="w-full bg-violet-600 hover:bg-violet-500 text-white"
                disabled={saving}
                onClick={() => void saveSettings()}
              >
                {saving ? "Salvando…" : "Salvar e Recalcular Regras"}
              </Button>
              <Button
                type="button"
                className="w-full bg-slate-800 hover:bg-slate-700 text-slate-200"
                onClick={closeSettings}
              >
                ← Voltar
              </Button>
            </CardContent>
          </Card>
        </div>
      )}

      {selected && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          onClick={closeOccurrence}
          role="presentation"
        >
          <Card
            className={cn(
              "w-full max-w-5xl max-h-[90vh] overflow-y-auto border bg-slate-900",
              riskTone(selected.nivelRisco, selected.scoreGravidade).card
            )}
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="fraud-ocorrencia-title"
          >
            <CardHeader className="flex flex-row items-start justify-between gap-3 pb-2 sticky top-0 bg-slate-900/95 z-10 border-b border-slate-800 backdrop-blur">
              <div>
                <CardTitle id="fraud-ocorrencia-title" className="text-lg text-white">
                  🚨 POSSÍVEL FRAUDE #{selected.idOcorrencia || selected.id}
                </CardTitle>
                <p className="text-xs text-slate-300 mt-1">
                  {selected.funcionarioNome || selected.frentistaNome} ·{" "}
                  {selected.postoNome || selected.empresaNome}
                </p>
                <Badge
                  className={cn(
                    "mt-2 text-[10px] border",
                    riskTone(selected.nivelRisco, selected.scoreGravidade).badge
                  )}
                >
                  {riskTone(selected.nivelRisco, selected.scoreGravidade).label}
                </Badge>
              </div>
              <Button
                size="sm"
                variant="outline"
                className="border-slate-500 text-slate-100 shrink-0 gap-1.5"
                onClick={closeOccurrence}
                aria-label="Fechar"
              >
                <X size={14} />
                ✕ Fechar
              </Button>
            </CardHeader>
            <CardContent className="space-y-4 pt-4">
              {/* Bloco da Emissão (Topo) */}
              <div className="rounded-lg border border-emerald-500/25 bg-emerald-950/20 px-4 py-3 space-y-3">
                <p className="text-[10px] uppercase tracking-wider text-emerald-400/90 font-bold">
                  Bloco da Emissão do Cupom (Baixa)
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-sm">
                  <Meta
                    label="Data/Hora Emissão"
                    value={formatDataHora(
                      selected.dataHoraEmissaoCupom ||
                        selected.dataHoraBaixa ||
                        selected.horaBaixa
                    )}
                  />
                  <Meta
                    label="Valor Total (R$)"
                    value={formatBRL(selected.valorTotal ?? selected.valorTotalCartao)}
                  />
                  <Meta
                    label="Desconto App/Fidelidade"
                    value={formatBRL(selected.valorDesconto ?? 0)}
                    highlight={
                      !!selected.cpfRepetido || (selected.valorDesconto ?? 0) > 0
                    }
                  />
                  <Meta
                    label="Litros totais"
                    value={formatLitros(selected.litros ?? 0)}
                  />
                </div>
                {(selected.cpfRepetido || selected.cpfDesconto) && (
                  <p
                    className={cn(
                      "text-xs font-medium",
                      selected.cpfRepetido ? "text-orange-300" : "text-slate-400"
                    )}
                  >
                    CPF/App: {selected.cpfDesconto || "—"}
                    {selected.cpfRepetido
                      ? " · REPETIDO no turno (abuso de fidelidade)"
                      : ""}
                    {selected.origemDesconto
                      ? ` · Origem: ${selected.origemDesconto}`
                      : ""}
                  </p>
                )}
              </div>

              <PagamentoBlock o={selected} />

              <p className="text-sm text-amber-200">
                <strong>Motivo:</strong> {selected.motivoSuspeita || selected.gatilho}
              </p>

              <div>
                <p className="text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-2">
                  Abastecimentos / Bicos Agrupados
                </p>
                <BicosTable
                  rows={detalhesOf(selected)}
                  postoFallback={selected.postoNome || selected.empresaNome}
                />
              </div>

              <div className="flex flex-col sm:flex-row gap-2 pt-2 border-t border-slate-800 sticky bottom-0 bg-slate-900/95 pb-1">
                <Button
                  type="button"
                  className="bg-cyan-700 hover:bg-cyan-600 text-white px-4 py-2 rounded-lg gap-1.5"
                  onClick={closeOccurrence}
                >
                  <ArrowLeft size={14} />
                  ← Voltar para Auditoria
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className="border-slate-600 text-slate-200 gap-1.5"
                  onClick={closeOccurrence}
                  aria-label="Fechar"
                >
                  <X size={14} />
                  ✕ Fechar
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

function BicosTable({
  rows,
  postoFallback,
  compact,
}: {
  rows: CardFraudBicoDetalhe[];
  postoFallback?: string;
  compact?: boolean;
}) {
  if (!rows.length) {
    return (
      <p className="text-xs text-slate-500">Sem abastecimentos detalhados nesta ocorrência.</p>
    );
  }
  const th = compact ? "px-2 py-1.5" : "px-3 py-2";
  const td = compact ? "px-2 py-1.5" : "px-3 py-2";
  const text = compact ? "text-xs" : "text-sm";
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-700/60">
      <table className={cn("w-full", text)}>
        <thead>
          <tr className="text-left text-[10px] uppercase text-slate-400 bg-slate-800/60">
            <th className={th}>Bico / Bomba</th>
            <th className={th}>Hora Abast.</th>
            <th className={th}>Retenção</th>
            <th className={th}>Combustível</th>
            <th className={cn(th, "text-right")}>Volume</th>
            <th className={cn(th, "text-right")}>Tabela</th>
            <th className={cn(th, "text-right")}>Praticado</th>
            <th className={cn(th, "text-right")}>Desc. Bico</th>
            <th className={th}>Origem</th>
            {!compact && <th className={th}>Posto</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((d, idx) => {
            const tab = d.precoTabela ?? d.precoUnitario ?? 0;
            const prat = d.precoPraticado ?? d.precoUnitario ?? 0;
            const gap = tab > 0 && prat > 0 && Math.abs(tab - prat) > 0.001;
            return (
              <tr
                key={`${d.idAbastecimento || d.abastecimentoId}-${idx}`}
                className="border-t border-slate-800 text-slate-200"
              >
                <td className={cn(td, "font-mono whitespace-nowrap")}>{bicoBombaLabel(d)}</td>
                <td className={cn(td, "font-mono")}>
                  {formatHora(d.dataHoraBico || d.horaBico)}
                </td>
                <td className={cn(td, "font-mono")}>
                  {d.tempoRetencaoMinutos != null ? `${d.tempoRetencaoMinutos} min` : "—"}
                </td>
                <td className={td}>{d.tipoCombustivel || d.produto || "—"}</td>
                <td className={cn(td, "text-right font-mono")}>{formatLitros(d.litros)}</td>
                <td className={cn(td, "text-right font-mono")}>{formatBRL(tab)}</td>
                <td
                  className={cn(
                    td,
                    "text-right font-mono",
                    gap && "text-amber-300"
                  )}
                >
                  {formatBRL(prat)}
                </td>
                <td
                  className={cn(
                    td,
                    "text-right font-mono",
                    (d.valorDesconto ?? 0) > 0 && "text-orange-300"
                  )}
                >
                  {formatBRL(d.valorDesconto ?? 0)}
                </td>
                <td className={cn(td, "text-slate-400 text-[11px]")}>
                  {d.origemDesconto || ((d.valorDesconto ?? 0) > 0 ? "App/Fid." : "—")}
                </td>
                {!compact && (
                  <td className={td}>{d.postoNome || postoFallback || "—"}</td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Kpi({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <Card className="border-slate-700/50 bg-slate-900/60">
      <CardContent className="pt-4">
        <p className="text-xs text-slate-300">{label}</p>
        <p className="text-xl font-bold text-white mt-1 truncate">{value}</p>
        <p className="text-[11px] text-slate-400 mt-1">{sub}</p>
      </CardContent>
    </Card>
  );
}

function Ranking({
  title,
  items,
}: {
  title: string;
  items: { nome: string; qtd: number; valor: number }[];
}) {
  return (
    <Card className="border-slate-700/50 bg-slate-900/60">
      <CardHeader className="pb-1">
        <CardTitle className="text-sm text-slate-200">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-1.5">
        {!items.length ? (
          <p className="text-xs text-slate-500">Sem dados</p>
        ) : (
          items.slice(0, 5).map((it, i) => (
            <div key={`${it.nome}-${i}`} className="flex justify-between text-xs text-slate-300">
              <span className="truncate mr-2">
                {i + 1}. {it.nome}
              </span>
              <span className="font-mono shrink-0">
                {it.qtd}x · {formatBRL(it.valor)}
              </span>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
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
      <p className="text-[10px] uppercase text-slate-500">{label}</p>
      <p
        className={cn(
          "font-medium font-mono",
          highlight ? "text-orange-300 font-bold" : "text-white"
        )}
      >
        {value}
      </p>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  step = 1,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
}) {
  return (
    <label className="block text-sm text-slate-200">
      <span className="text-xs text-slate-400">{label}</span>
      <input
        type="number"
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-1 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-white font-mono"
      />
    </label>
  );
}
