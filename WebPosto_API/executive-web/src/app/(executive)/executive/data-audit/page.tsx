"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  RefreshCcw,
  Droplet,
  Fuel,
  Wallet,
  Gauge,
  TrendingDown,
  AlertTriangle,
  ClipboardCheck,
  UserMinus,
  Search,
  FileDown,
  FileSpreadsheet,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { GlobalFilterHeader } from "@/components/executive/global-filter-header";
import { ExpenseDetailModal } from "@/components/executive/expense-detail-modal";
import { CardFraudAuditPanel } from "@/components/executive/card-fraud-audit-panel";
import { CashierAuditPanel } from "@/components/executive/cashier-audit-panel";
import { useGlobalFilter } from "@/contexts/global-filter-context";
import { apiService } from "@/lib/api";
import { exportDataAuditExcel, exportDataAuditPdf } from "@/lib/export-executive-report";
import { exportFraudAuditExcel, exportFraudAuditPdf } from "@/lib/export-fraud-audit-report";
import type {
  CardFraudAuditResponse,
  DataAuditExpenseCategory,
  DataAuditFilial,
  DataAuditResponse,
  DataAuditValeItem,
} from "@/types/api";
import { cn } from "@/lib/utils";

const FILIAL_ORDER = [5555, 11495, 74014];

type AuditTab = "afericao" | "anti-fraude" | "caixas" | "pista-ao-vivo";

function resolveTab(raw: string | null): AuditTab {
  if (raw === "caixas" || raw === "cashier") return "caixas";
  if (raw === "anti-fraude" || raw === "fraude") return "anti-fraude";
  // Pista ao Vivo desativada — redireciona para aferição
  if (raw === "pista-ao-vivo" || raw === "pista" || raw === "live") return "afericao";
  return "afericao";
}

export default function DataAuditPage() {
  return (
    <Suspense
      fallback={
        <div className="p-4 lg:p-8 max-w-[1600px] mx-auto">
          <Skeleton className="h-10 w-64 bg-slate-900 mb-4" />
          <Skeleton className="h-40 w-full bg-slate-900" />
        </div>
      }
    >
      <DataAuditPageContent />
    </Suspense>
  );
}

function DataAuditPageContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const urlTab = resolveTab(searchParams.get("tab"));
  const [data, setData] = useState<DataAuditResponse | null>(null);
  const [fraudData, setFraudData] = useState<CardFraudAuditResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [periodReady, setPeriodReady] = useState(false);
  const [activeTab, setActiveTab] = useState<AuditTab>(urlTab);

  const {
    selectedFilial,
    isConsolidated,
    periodDates,
    periodLabel,
    filialShortLabel,
    setSelectedPeriod,
  } = useGlobalFilter();
  const empresaCodigo = isConsolidated ? undefined : selectedFilial;

  const selectTab = useCallback(
    (tab: AuditTab) => {
      setActiveTab(tab);
      const params = new URLSearchParams(searchParams.toString());
      if (tab === "afericao") params.delete("tab");
      else params.set("tab", tab);
      const qs = params.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [router, pathname, searchParams]
  );

  // Aferição: default ONTEM (D-1). Anti-fraude: preserva o período do filtro global
  // (ex.: Últimos 7 Dias) para auditoria histórica real.
  useEffect(() => {
    if (urlTab === "afericao") {
      setSelectedPeriod("yesterday");
    }
    setPeriodReady(true);
  }, [setSelectedPeriod, urlTab]);

  const onFraudDataLoaded = useCallback((payload: CardFraudAuditResponse | null) => {
    setFraudData(payload);
  }, []);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setData(null);
      setError(null);
      const result = await apiService.getDataAudit(
        periodDates.start,
        periodDates.end,
        empresaCodigo
      );
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar aferição");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [periodDates.start, periodDates.end, empresaCodigo]);

  useEffect(() => {
    setActiveTab(urlTab);
  }, [urlTab]);

  useEffect(() => {
    if (!periodReady) return;
    // Aferição pesada só quando a aba correspondente está ativa
    if (activeTab !== "afericao") return;
    void fetchData();
  }, [fetchData, periodReady, activeTab]);

  const formatBRL = (v: number) =>
    new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(v || 0);

  const formatL = (v: number) =>
    `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(v || 0)} L`;

  const filiais = (data?.filiais || [])
    .slice()
    .sort(
      (a, b) =>
        FILIAL_ORDER.indexOf(a.empresaCodigo) - FILIAL_ORDER.indexOf(b.empresaCodigo)
    );

  const consolidado = data?.consolidado || {};

  return (
    <div className="p-4 lg:p-8 max-w-[1600px] mx-auto space-y-6">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className="bg-amber-500/10 text-amber-400 border-amber-500/20">
              S60
            </Badge>
            <span className="text-[10px] text-slate-300 uppercase tracking-widest font-bold">
              Homologação Diretoria
            </span>
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-2">
            <ClipboardCheck className="text-amber-400" size={28} />
            Aferição de Dados Reais
          </h1>
          <p className="text-slate-400 text-sm">
            Faturamento, volume, abastecimentos, tanques, DRE e vales de funcionários •{" "}
            {filialShortLabel} • {periodLabel}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={
              activeTab === "anti-fraude"
                ? !fraudData
                : !data || loading
            }
            onClick={() => {
              if (activeTab === "anti-fraude") {
                if (fraudData) {
                  exportFraudAuditPdf(fraudData, {
                    filialLabel: filialShortLabel,
                    periodLabel,
                  });
                }
                return;
              }
              if (data) {
                exportDataAuditPdf(data, {
                  filialLabel: filialShortLabel,
                  periodLabel,
                });
              }
            }}
            className="border-rose-500/30 text-rose-200 hover:bg-rose-500/10"
          >
            <FileDown size={14} className="mr-2" />
            Baixar PDF Executivo
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={
              activeTab === "anti-fraude"
                ? !fraudData
                : !data || loading
            }
            onClick={() => {
              if (activeTab === "anti-fraude") {
                if (fraudData) exportFraudAuditExcel(fraudData);
                return;
              }
              if (data) exportDataAuditExcel(data);
            }}
            className="border-emerald-500/30 text-emerald-200 hover:bg-emerald-500/10"
          >
            <FileSpreadsheet size={14} className="mr-2" />
            Exportar Excel
          </Button>
          <Button
            size="sm"
            onClick={() => void fetchData()}
            disabled={loading || activeTab !== "afericao"}
            className="bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20"
          >
            <RefreshCcw size={14} className={cn("mr-2", loading && "animate-spin")} />
            Atualizar
          </Button>
        </div>
      </header>

      <GlobalFilterHeader />

      <div className="flex gap-1 border-b border-slate-800 pb-0">
        <button
          type="button"
          onClick={() => selectTab("afericao")}
          className={cn(
            "px-4 py-2 text-sm font-medium rounded-t-md border-b-2 transition-colors",
            activeTab === "afericao"
              ? "border-amber-400 text-amber-300 bg-amber-500/5"
              : "border-transparent text-slate-400 hover:text-slate-200"
          )}
        >
          Aferição de Dados
        </button>
        <button
          type="button"
          onClick={() => selectTab("anti-fraude")}
          className={cn(
            "px-4 py-2 text-sm font-medium rounded-t-md border-b-2 transition-colors",
            activeTab === "anti-fraude"
              ? "border-rose-400 text-rose-300 bg-rose-500/5"
              : "border-transparent text-slate-400 hover:text-slate-200"
          )}
        >
          Auditoria Anti-Fraude
        </button>
        <button
          type="button"
          onClick={() => selectTab("caixas")}
          className={cn(
            "px-4 py-2 text-sm font-medium rounded-t-md border-b-2 transition-colors",
            activeTab === "caixas"
              ? "border-emerald-400 text-emerald-300 bg-emerald-500/5"
              : "border-transparent text-slate-400 hover:text-slate-200"
          )}
        >
          Auditoria de Caixas
        </button>
        <button
          type="button"
          disabled
          title="Recurso em desenvolvimento"
          className={cn(
            "px-4 py-2 text-sm font-medium rounded-t-md border-b-2 transition-colors",
            "opacity-50 text-slate-500 bg-slate-900/50 border-slate-800 border-b-2",
            "cursor-not-allowed pointer-events-none select-none inline-flex items-center gap-2"
          )}
        >
          Pista ao Vivo / Status Bicos
          <span className="bg-slate-800 text-slate-400 text-[10px] px-2 py-0.5 rounded border border-slate-700 font-semibold uppercase">
            Inativo
          </span>
        </button>
      </div>

      {activeTab === "caixas" ? (
        <CashierAuditPanel empresaCodigo={empresaCodigo} ready />
      ) : activeTab === "anti-fraude" ? (
        <CardFraudAuditPanel
          start={periodDates.start}
          end={periodDates.end}
          empresaCodigo={empresaCodigo}
          periodReady={periodReady}
          onDataLoaded={onFraudDataLoaded}
        />
      ) : loading ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
          <Skeleton className="h-64 w-full" />
        </div>
      ) : error ? (
        <Card className="border-red-500/30 bg-red-500/5 p-8 text-center">
          <AlertTriangle className="mx-auto text-red-400 mb-2" />
          <p className="text-red-300 font-medium">{error}</p>
          <Button className="mt-4" variant="outline" onClick={() => void fetchData()}>
            Tentar novamente
          </Button>
        </Card>
      ) : (
        <div
          key={`audit-${empresaCodigo ?? "all"}-${periodDates.start}`}
          className="space-y-6 animate-in fade-in duration-300"
        >
          <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
            <Kpi
              label="Faturamento"
              value={formatBRL(Number(consolidado.faturamentoTotal || 0))}
              icon={<Wallet className="text-emerald-400" size={16} />}
            />
            <Kpi
              label="Volume"
              value={formatL(Number(consolidado.volumeLitros || 0))}
              icon={<Droplet className="text-blue-400" size={16} />}
            />
            <Kpi
              label="Abastecimentos"
              value={String(consolidado.quantidadeAbastecimentos ?? 0)}
              icon={<Fuel className="text-cyan-400" size={16} />}
            />
            <Kpi
              label="Ocupação Tanques"
              value={`${Number(consolidado.ocupacaoTanquesPctMedia || 0).toFixed(1)}%`}
              icon={<Gauge className="text-violet-400" size={16} />}
            />
            <Kpi
              label="Vales Funcionários"
              value={formatBRL(Number(consolidado.valesFuncionariosTotal || 0))}
              icon={<UserMinus className="text-rose-400" size={16} />}
              highlight={Number(consolidado.valesFuncionariosTotal || 0) > 0}
            />
            <Kpi
              label="Resultado Operacional"
              value={formatBRL(Number(consolidado.resultadoOperacionalDiario || 0))}
              icon={<TrendingDown className="text-amber-400" size={16} />}
              highlight={Number(consolidado.resultadoOperacionalDiario || 0) < 0}
            />
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
            {filiais.map((f) => (
              <FilialCard
                key={f.empresaCodigo}
                filial={f}
                formatBRL={formatBRL}
                formatL={formatL}
                periodStart={periodDates.start}
                periodEnd={periodDates.end}
              />
            ))}
            {filiais.length === 0 && (
              <Card className="border-slate-800 bg-slate-900/90 xl:col-span-3 p-10 text-center text-slate-300">
                Sem dados para o período/filial selecionados.
              </Card>
            )}
          </div>

          <ValesConsolidatedTable filiais={filiais} formatBRL={formatBRL} />
        </div>
      )}
    </div>
  );
}

function Kpi({
  label,
  value,
  icon,
  highlight,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  highlight?: boolean;
}) {
  return (
    <Card className="border-slate-800 bg-slate-900/90 p-4">
      <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-slate-300 font-bold">
        {icon}
        {label}
      </div>
      <p
        className={cn(
          "text-xl font-bold mt-2",
          highlight ? "text-red-400" : "text-white"
        )}
      >
        {value}
      </p>
    </Card>
  );
}

function FilialCard({
  filial,
  formatBRL,
  formatL,
  periodStart,
  periodEnd,
}: {
  filial: DataAuditFilial;
  formatBRL: (v: number) => string;
  formatL: (v: number) => string;
  periodStart: string;
  periodEnd: string;
}) {
  const cats = filial.despesasPorCategoria || [];
  const [selected, setSelected] = useState<DataAuditExpenseCategory | null>(null);

  return (
    <Card className="border-slate-800 bg-slate-900/90">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-base text-white">{filial.empresaNome}</CardTitle>
          <Badge variant="outline" className="text-[10px] border-white/10 text-slate-400">
            {filial.empresaCodigo}
          </Badge>
        </div>
        <CardDescription>
          Resultado {formatBRL(filial.resultadoOperacionalDiario ?? 0)}
          {filial.fallback ? " • fallback" : ""}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-2 text-xs">
          <Metric label="Faturamento" value={formatBRL(filial.faturamentoTotal ?? 0)} />
          <Metric label="Volume" value={formatL(filial.volumeLitros ?? 0)} />
          <Metric
            label="Abastecimentos"
            value={String(filial.quantidadeAbastecimentos ?? 0)}
          />
          <Metric
            label="Ocupação Tanques"
            value={`${(filial.ocupacaoTanquesPct ?? 0).toFixed(1)}%`}
          />
          <Metric
            label="Margem Bruta média"
            value={`R$ ${(filial.margemBrutaMediaRsLitro ?? 0).toFixed(3)}/L`}
          />
          <Metric
            label="Estoque imobilizado"
            value={formatBRL(filial.valorEstoqueImobilizado ?? 0)}
          />
        </div>

        <div>
          <p className="text-[10px] uppercase tracking-widest text-slate-300 font-bold mb-2">
            Despesas por Plano de Contas
          </p>
          <div className="space-y-2">
            {cats.map((c) => {
              const qtd = c.qtd_lancamentos ?? 0;
              const clickable = qtd > 0 || (c.itens?.length ?? 0) > 0;
              return (
                <button
                  key={c.categoriaKey || c.categoria}
                  type="button"
                  disabled={!clickable}
                  onClick={() => clickable && setSelected(c)}
                  className={cn(
                    "w-full flex items-center justify-between rounded-md border px-3 py-2 text-left transition-colors",
                    clickable
                      ? "border-slate-800 bg-white/[0.03] hover:border-cyan-500/40 hover:bg-cyan-500/[0.06] cursor-pointer group"
                      : "border-slate-800 bg-white/[0.02] opacity-60 cursor-default"
                  )}
                >
                  <div className="min-w-0 pr-2">
                    <p className="text-[11px] text-slate-300 leading-tight group-hover:text-cyan-100">
                      {c.categoria}
                    </p>
                    <p className="text-[10px] text-slate-300 flex items-center gap-1.5 mt-0.5">
                      <span>
                        {qtd} lançamento{qtd === 1 ? "" : "s"}
                      </span>
                      {clickable ? (
                        <span className="inline-flex items-center gap-0.5 text-cyan-400/80 group-hover:text-cyan-300">
                          <Search size={10} />
                          Ver Detalhes
                        </span>
                      ) : null}
                    </p>
                  </div>
                  <p className="text-sm font-semibold text-white shrink-0">
                    {formatBRL(c.valor ?? 0)}
                  </p>
                </button>
              );
            })}
          </div>
          <div className="mt-3 flex justify-between text-xs border-t border-slate-800 pt-2">
            <span className="text-slate-300">Total despesas</span>
            <span className="font-bold text-amber-300">
              {formatBRL(filial.despesasTotal ?? 0)}
            </span>
          </div>
          <p className="text-[10px] text-slate-300 mt-2">
            Resultado = Faturamento − (CPV + Pessoal + Admin + Outras)
          </p>
        </div>

        <ValesFilialBlock
          vales={filial.valesFuncionarios}
          formatBRL={formatBRL}
        />
      </CardContent>

      {selected ? (
        <ExpenseDetailModal
          key={`${filial.empresaCodigo}-${selected.categoriaKey || selected.categoria}`}
          isOpen={!!selected}
          onClose={() => setSelected(null)}
          empresaCodigo={filial.empresaCodigo}
          empresaNome={filial.empresaNome}
          categoria={selected.categoria}
          categoriaKey={selected.categoriaKey || selected.categoria}
          cardTotal={selected.valor ?? 0}
          periodStart={periodStart}
          periodEnd={periodEnd}
          seedItens={selected.itens || []}
        />
      ) : null}
    </Card>
  );
}

function ValesFilialBlock({
  vales,
  formatBRL,
}: {
  vales?: DataAuditFilial["valesFuncionarios"];
  formatBRL: (v: number) => string;
}) {
  const total = vales?.total ?? 0;
  const itens = vales?.itens || [];
  return (
    <div className="rounded-md border border-rose-500/20 bg-rose-500/[0.04] p-3">
      <div className="flex items-center justify-between mb-2">
        <p className="text-[10px] uppercase tracking-widest text-rose-300/80 font-bold flex items-center gap-1.5">
          <UserMinus size={12} />
          Vales de Funcionários
        </p>
        <span className="text-sm font-bold text-rose-300">{formatBRL(total)}</span>
      </div>
      {itens.length === 0 ? (
        <p className="text-[11px] text-slate-300">Nenhum vale no período.</p>
      ) : (
        <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
          {itens.slice(0, 8).map((item, idx) => (
            <div
              key={`${item.descricao}-${idx}`}
              className="flex items-start justify-between gap-2 text-[11px]"
            >
              <div className="min-w-0">
                <p className="text-slate-200 truncate">
                  {item.funcionario || "—"}
                </p>
                <p className="text-slate-400 truncate text-[10px]">
                  {[item.dataCaixa, item.turno].filter(Boolean).join(" · ") || "sem rastreio"}
                </p>
                <p className="text-slate-300 truncate" title={item.descricao}>
                  {item.descricao}
                </p>
              </div>
              <span className="shrink-0 font-semibold text-rose-200 tabular-nums">
                {formatBRL(item.valor ?? 0)}
              </span>
            </div>
          ))}
          {(vales?.quantidade ?? 0) > 8 && (
            <p className="text-[10px] text-slate-300 pt-1">
              +{(vales?.quantidade ?? 0) - 8} lançamentos (ver tabela consolidada)
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function ValesConsolidatedTable({
  filiais,
  formatBRL,
}: {
  filiais: DataAuditFilial[];
  formatBRL: (v: number) => string;
}) {
  const rows: Array<DataAuditValeItem & { empresaNome: string; empresaCodigo: number }> =
    [];
  for (const f of filiais) {
    for (const item of f.valesFuncionarios?.itens || []) {
      rows.push({
        ...item,
        empresaNome: f.empresaNome,
        empresaCodigo: f.empresaCodigo,
      });
    }
  }
  rows.sort((a, b) => (b.valor || 0) - (a.valor || 0));
  const total = filiais.reduce((s, f) => s + (f.valesFuncionarios?.total || 0), 0);

  return (
    <Card className="border-rose-500/20 bg-slate-900/90">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
          <div>
            <CardTitle className="text-base text-white flex items-center gap-2">
              <UserMinus className="text-rose-400" size={18} />
              Vales de Funcionários — Rede
            </CardTitle>
            <CardDescription>
              {rows.length} lançamentos • Total {formatBRL(total)}
            </CardDescription>
          </div>
          <Badge variant="outline" className="border-rose-500/30 text-rose-300">
            Pessoal / Caixa
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        {rows.length === 0 ? (
          <p className="text-sm text-slate-300 py-6 text-center">
            Nenhum vale de funcionário identificado no período.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[10px] uppercase tracking-wider text-slate-300 border-b border-slate-800">
                  <th className="text-left py-2 pr-3 font-bold">Filial</th>
                  <th className="text-left py-2 pr-3 font-bold">Data do Caixa</th>
                  <th className="text-left py-2 pr-3 font-bold">Turno/PDV</th>
                  <th className="text-left py-2 pr-3 font-bold">Funcionário</th>
                  <th className="text-left py-2 pr-3 font-bold">Descrição</th>
                  <th className="text-left py-2 pr-3 font-bold">Fonte</th>
                  <th className="text-right py-2 font-bold">Valor</th>
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, 40).map((r, idx) => (
                  <tr
                    key={`${r.empresaCodigo}-${r.descricao}-${idx}`}
                    className="border-b border-slate-800 hover:bg-white/[0.02]"
                  >
                    <td className="py-2 pr-3 text-slate-300 whitespace-nowrap">
                      {r.empresaNome}
                    </td>
                    <td className="py-2 pr-3 text-slate-300 whitespace-nowrap">
                      {r.dataCaixa || "—"}
                    </td>
                    <td className="py-2 pr-3 text-slate-300 whitespace-nowrap">
                      {r.turno || "—"}
                    </td>
                    <td className="py-2 pr-3 text-white font-medium whitespace-nowrap">
                      {r.funcionario || "—"}
                    </td>
                    <td className="py-2 pr-3 text-slate-400 max-w-[280px] truncate" title={r.descricao}>
                      {r.descricao || "—"}
                    </td>
                    <td className="py-2 pr-3 text-slate-300 text-xs">
                      {r.fonte === "caixa_apresentado" ? "Caixa" : "Despesa"}
                    </td>
                    <td className="py-2 text-right font-semibold text-rose-300 whitespace-nowrap">
                      {formatBRL(r.valor ?? 0)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-white/[0.03] border border-slate-800 px-2 py-1.5">
      <p className="text-[9px] uppercase tracking-wider text-slate-300">{label}</p>
      <p className="text-[12px] font-semibold text-white mt-0.5">{value}</p>
    </div>
  );
}
