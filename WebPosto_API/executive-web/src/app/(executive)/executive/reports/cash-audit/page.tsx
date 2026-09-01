"use client";

import React, { useEffect, useState, useMemo } from "react";
import { Wallet, AlertTriangle, Receipt, TrendingDown, Fuel, Clock, User, CircleDot } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ReportFilterBar } from "@/components/executive/report-filter-bar";
import { InfoTooltip } from "@/components/ui/info-tooltip";
import { useReportFilter } from "@/contexts/report-filter-context";
import { apiService } from "@/lib/api";
import { ExecutiveReport } from "@/types/api";
import { ReportLayout } from "@/components/executive/report-layout";
import { cn } from "@/lib/utils";

export default function CashAuditReportPage() {
  const [report, setReport] = useState<ExecutiveReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { selectedFilial, isConsolidated } = useReportFilter();

  useEffect(() => {
    let active = true;
    apiService
      .getExecutiveConsolidatedReport()
      .then((data) => {
        if (active) {
          setReport(data);
          setError(null);
        }
      })
      .catch((err) => {
        if (!active) return;
        const raw = err instanceof Error ? err.message : "Erro ao carregar";
        const msg = /Failed to fetch|NetworkError|Load failed/i.test(raw)
          ? "Falha de rede ao carregar o relatório. Use /executive/cashier-audit (cache RAM) ou confira API :8040."
          : raw;
        setError(msg);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const formatBRL = (val: string | number) => {
    try {
      return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(
        Number(val || 0)
      );
    } catch {
      return "R$ 0,00";
    }
  };

  const formatNumber = (val: string | number) => {
    try {
      return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 }).format(Number(val || 0));
    } catch {
      return "0";
    }
  };

  const reconciliation = report?.bloco_9_anomalias.divergencias_caixa;
  const operatorDetails = report?.bloco_9_anomalias.rombo_por_operador_turno || [];
  const auditoriaPista = report?.bloco_9_anomalias.auditoria_pista;

  const { expensesByCompany, avgExpense, filteredReconciliation } = useMemo(() => {
    const expenses = report?.bloco_6_despesas.por_empresa || [];
    const filteredExpenses = isConsolidated
      ? expenses
      : expenses.filter((e) => e.empresa_codigo === selectedFilial);
    const avg =
      filteredExpenses.length === 0
        ? 0
        : filteredExpenses.reduce((acc, cur) => acc + Number(cur.valor || 0), 0) /
          filteredExpenses.length;

    const recon = reconciliation
      ? {
          ...reconciliation,
          valor_apurado: isConsolidated
            ? reconciliation.valor_apurado
            : (Number(reconciliation.valor_apurado || 0) / 3).toFixed(2),
          valor_apresentado: isConsolidated
            ? reconciliation.valor_apresentado
            : (Number(reconciliation.valor_apresentado || 0) / 3).toFixed(2),
          valor_divergente: isConsolidated
            ? reconciliation.valor_divergente
            : (Number(reconciliation.valor_divergente || 0) / 3).toFixed(2),
          valor_pendente: isConsolidated
            ? reconciliation.valor_pendente
            : (Number(reconciliation.valor_pendente || 0) / 3).toFixed(2),
        }
      : null;

    return { expensesByCompany: filteredExpenses, avgExpense: avg, filteredReconciliation: recon };
  }, [report?.bloco_6_despesas.por_empresa, reconciliation, selectedFilial, isConsolidated]);

  const renderSkeleton = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28 bg-slate-900" />
        ))}
      </div>
      <Skeleton className="h-64 bg-slate-900" />
      <Skeleton className="h-64 bg-slate-900" />
    </div>
  );

  return (
    <ReportLayout
      title="Auditoria de Caixa & Anomalias"
      subtitle="Detalhamento do rombo por operador, turno e meio de pagamento"
      loading={loading}
    >
      <div className="mb-6">
        <ReportFilterBar />
      </div>

      {loading ? (
        renderSkeleton()
      ) : error ? (
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-4 text-red-200">
          {error}
        </div>
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card className="bg-slate-900 border-white/5">
              <CardContent className="p-6">
                <div className="flex items-center gap-3">
                  <div className="grid size-10 place-items-center rounded-lg bg-blue-500/10">
                    <Wallet className="size-5 text-blue-400" />
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <p className="text-sm text-slate-400">Valor Apurado</p>
                      <InfoTooltip content="Valor total que o sistema calculou que deveria estar no caixa com base em todas as vendas registradas no período." />
                    </div>
                    <p className="text-xl font-bold text-white">
                      {formatBRL(filteredReconciliation?.valor_apurado || "0")}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="bg-slate-900 border-white/5">
              <CardContent className="p-6">
                <div className="flex items-center gap-3">
                  <div className="grid size-10 place-items-center rounded-lg bg-emerald-500/10">
                    <Receipt className="size-5 text-emerald-400" />
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <p className="text-sm text-slate-400">Valor Apresentado</p>
                      <InfoTooltip content="Valor efetivamente informado pelos operadores no fechamento de caixa. Inclui dinheiro contado, cheques e sangrias." />
                    </div>
                    <p className="text-xl font-bold text-white">
                      {formatBRL(filteredReconciliation?.valor_apresentado || "0")}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="bg-slate-900 border-white/5">
              <CardContent className="p-6">
                <div className="flex items-center gap-3">
                  <div className="grid size-10 place-items-center rounded-lg bg-red-500/10">
                    <AlertTriangle className="size-5 text-red-400" />
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <p className="text-sm text-slate-400">Divergente</p>
                      <InfoTooltip content="Diferença entre o valor apurado pelo sistema e o valor apresentado. Valores positivos indicam possível furo de caixa." />
                    </div>
                    <p className="text-xl font-bold text-white">
                      {formatBRL(filteredReconciliation?.valor_divergente || "0")}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="bg-slate-900 border-white/5">
              <CardContent className="p-6">
                <div className="flex items-center gap-3">
                  <div className="grid size-10 place-items-center rounded-lg bg-amber-500/10">
                    <TrendingDown className="size-5 text-amber-400" />
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <p className="text-sm text-slate-400">Pendente</p>
                      <InfoTooltip content="Valores ainda não reconciliados ou que estão em análise. Requer verificação manual por parte da gestão." />
                    </div>
                    <p className="text-xl font-bold text-white">
                      {formatBRL(filteredReconciliation?.valor_pendente || "0")}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {auditoriaPista && auditoriaPista.total_pendentes > 0 && (
            <>
              <Card className="bg-gradient-to-br from-orange-500/10 to-red-500/10 border-orange-500/20">
                <CardHeader className="pb-2">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="size-5 text-orange-400" />
                    <CardTitle className="text-lg text-orange-300">
                      Auditoria de Pista — Abastecimentos Pendentes
                    </CardTitle>
                  </div>
                  <CardDescription className="text-orange-200/70">
                    Litros e valores represados na bomba sem NFC-e emitida
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <div className="p-4 rounded-lg bg-slate-900/50 border border-white/5">
                      <div className="flex items-center gap-1.5 mb-1">
                        <Fuel className="size-4 text-orange-400" />
                        <span className="text-xs text-slate-400">Litros Pendentes</span>
                        <InfoTooltip content="Volume total de combustível abastecido mas ainda não baixado no PDV com emissão de NFC-e." />
                      </div>
                      <p className="text-xl font-bold text-orange-300">
                        {formatNumber(auditoriaPista.litros_pendentes)} L
                      </p>
                    </div>
                    <div className="p-4 rounded-lg bg-slate-900/50 border border-white/5">
                      <div className="flex items-center gap-1.5 mb-1">
                        <Wallet className="size-4 text-red-400" />
                        <span className="text-xs text-slate-400">Valor Represado</span>
                        <InfoTooltip content="Valor em R$ dos abastecimentos pendentes que ainda não entraram no caixa fiscal." />
                      </div>
                      <p className="text-xl font-bold text-red-300">
                        {formatBRL(auditoriaPista.valor_pendente)}
                      </p>
                    </div>
                    <div className="p-4 rounded-lg bg-slate-900/50 border border-white/5">
                      <div className="flex items-center gap-1.5 mb-1">
                        <Clock className="size-4 text-amber-400" />
                        <span className="text-xs text-slate-400">Alertas Retenção</span>
                        <InfoTooltip content="Abastecimentos pendentes há mais de 15 minutos sem baixa no PDV. Indica possível giro fraudulento." />
                      </div>
                      <p className="text-xl font-bold text-amber-300">
                        {auditoriaPista.alertas_retencao}
                      </p>
                    </div>
                    <div className="p-4 rounded-lg bg-slate-900/50 border border-white/5">
                      <div className="flex items-center gap-1.5 mb-1">
                        <CircleDot className="size-4 text-purple-400" />
                        <span className="text-xs text-slate-400">Total Pendentes</span>
                        <InfoTooltip content="Quantidade total de abastecimentos que ainda não receberam baixa no sistema." />
                      </div>
                      <p className="text-xl font-bold text-purple-300">
                        {auditoriaPista.total_pendentes}
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    <Card className="bg-slate-900/70 border-white/5">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm text-white flex items-center gap-2">
                          <User className="size-4 text-blue-400" />
                          Por Frentista
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <Table>
                          <TableHeader>
                            <TableRow className="border-white/5">
                              <TableHead className="text-slate-400 text-xs">Frentista</TableHead>
                              <TableHead className="text-slate-400 text-xs text-right">Pend.</TableHead>
                              <TableHead className="text-slate-400 text-xs text-right">Litros</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {(auditoriaPista.por_frentista || []).slice(0, 5).map((f, i) => (
                              <TableRow key={i} className="border-white/5">
                                <TableCell className="text-white text-xs font-medium">{f.frentista}</TableCell>
                                <TableCell className="text-slate-300 text-xs text-right">
                                  {f.total_pendentes}
                                  {f.alertas > 0 && (
                                    <Badge variant="outline" className="ml-1 bg-red-500/10 text-red-300 border-red-500/20 text-[9px]">
                                      {f.alertas} ALERTA
                                    </Badge>
                                  )}
                                </TableCell>
                                <TableCell className="text-slate-300 text-xs text-right">{formatNumber(f.litros)} L</TableCell>
                              </TableRow>
                            ))}
                            {(!auditoriaPista.por_frentista || auditoriaPista.por_frentista.length === 0) && (
                              <TableRow className="border-white/5">
                                <TableCell colSpan={3} className="text-center text-slate-500 text-xs">Sem dados</TableCell>
                              </TableRow>
                            )}
                          </TableBody>
                        </Table>
                      </CardContent>
                    </Card>

                    <Card className="bg-slate-900/70 border-white/5">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm text-white flex items-center gap-2">
                          <Fuel className="size-4 text-emerald-400" />
                          Por Bico/Bomba
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <Table>
                          <TableHeader>
                            <TableRow className="border-white/5">
                              <TableHead className="text-slate-400 text-xs">Bico</TableHead>
                              <TableHead className="text-slate-400 text-xs text-right">Pend.</TableHead>
                              <TableHead className="text-slate-400 text-xs text-right">Valor</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {(auditoriaPista.por_bico || []).slice(0, 5).map((b, i) => (
                              <TableRow key={i} className="border-white/5">
                                <TableCell className="text-white text-xs font-medium">Bico {b.bico}</TableCell>
                                <TableCell className="text-slate-300 text-xs text-right">{b.total_pendentes}</TableCell>
                                <TableCell className="text-slate-300 text-xs text-right">{formatBRL(b.valor)}</TableCell>
                              </TableRow>
                            ))}
                            {(!auditoriaPista.por_bico || auditoriaPista.por_bico.length === 0) && (
                              <TableRow className="border-white/5">
                                <TableCell colSpan={3} className="text-center text-slate-500 text-xs">Sem dados</TableCell>
                              </TableRow>
                            )}
                          </TableBody>
                        </Table>
                      </CardContent>
                    </Card>

                    <Card className="bg-slate-900/70 border-white/5">
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm text-white flex items-center gap-2">
                          <Clock className="size-4 text-amber-400" />
                          Por Turno
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <Table>
                          <TableHeader>
                            <TableRow className="border-white/5">
                              <TableHead className="text-slate-400 text-xs">Turno</TableHead>
                              <TableHead className="text-slate-400 text-xs text-right">Pend.</TableHead>
                              <TableHead className="text-slate-400 text-xs text-right">Alertas</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {(auditoriaPista.por_turno || []).map((t, i) => (
                              <TableRow key={i} className="border-white/5">
                                <TableCell className="text-white text-xs font-medium">{t.turno}</TableCell>
                                <TableCell className="text-slate-300 text-xs text-right">{t.total_pendentes}</TableCell>
                                <TableCell className="text-xs text-right">
                                  {t.alertas > 0 ? (
                                    <Badge variant="outline" className="bg-red-500/10 text-red-300 border-red-500/20 text-[9px]">
                                      {t.alertas}
                                    </Badge>
                                  ) : (
                                    <span className="text-emerald-300">0</span>
                                  )}
                                </TableCell>
                              </TableRow>
                            ))}
                            {(!auditoriaPista.por_turno || auditoriaPista.por_turno.length === 0) && (
                              <TableRow className="border-white/5">
                                <TableCell colSpan={3} className="text-center text-slate-500 text-xs">Sem dados</TableCell>
                              </TableRow>
                            )}
                          </TableBody>
                        </Table>
                      </CardContent>
                    </Card>
                  </div>
                </CardContent>
              </Card>
            </>
          )}

          <Card className="bg-slate-900 border-white/5">
            <CardHeader>
              <CardTitle className="text-white">Reconciliação por Meio de Pagamento</CardTitle>
              <CardDescription className="text-slate-400">
                Apurado vs apresentado por natureza
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow className="border-white/5 hover:bg-white/5">
                    <TableHead className="text-slate-300">Natureza</TableHead>
                    <TableHead className="text-slate-300 text-right">Apurado</TableHead>
                    <TableHead className="text-slate-300 text-right">Apresentado</TableHead>
                    <TableHead className="text-slate-300 text-right">Diferença</TableHead>
                    <TableHead className="text-slate-300 text-right">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(filteredReconciliation?.naturezas || []).map((row) => {
                    const diff = Number(row.diferenca || 0);
                    const status = diff === 0 ? "OK" : diff > 0 ? "SOBRA" : "FALTA";
                    return (
                      <TableRow key={row.natureza} className="border-white/5 hover:bg-white/5">
                        <TableCell className="text-white font-medium">{row.label}</TableCell>
                        <TableCell className="text-slate-300 text-right">
                          {formatBRL(row.valor_apurado)}
                        </TableCell>
                        <TableCell className="text-slate-300 text-right">
                          {formatBRL(row.valor_apresentado)}
                        </TableCell>
                        <TableCell
                          className={cn(
                            "text-right",
                            diff < 0 && "text-red-300",
                            diff > 0 && "text-emerald-300"
                          )}
                        >
                          {formatBRL(row.diferenca)}
                        </TableCell>
                        <TableCell className="text-right">
                          <Badge
                            variant="outline"
                            className={cn(
                              status === "OK" &&
                                "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
                              status === "SOBRA" &&
                                "bg-amber-500/10 text-amber-300 border-amber-500/20",
                              status === "FALTA" && "bg-red-500/10 text-red-300 border-red-500/20"
                            )}
                          >
                            {status}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="bg-slate-900 border-white/5">
              <CardHeader>
                <CardTitle className="text-white">Rombo por Operador & Turno</CardTitle>
                <CardDescription className="text-slate-400">
                  Divergência detalhada por caixa
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow className="border-white/5 hover:bg-white/5">
                      <TableHead className="text-slate-300">Operador</TableHead>
                      <TableHead className="text-slate-300">Turno</TableHead>
                      <TableHead className="text-slate-300 text-right">Dinheiro</TableHead>
                      <TableHead className="text-slate-300 text-right">Cheque</TableHead>
                      <TableHead className="text-slate-300 text-right">PIX</TableHead>
                      <TableHead className="text-slate-300 text-right">Cartão</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {operatorDetails.map((row) => (
                      <TableRow
                        key={`${row.funcionario_codigo}-${row.turno}`}
                        className="border-white/5 hover:bg-white/5"
                      >
                        <TableCell className="text-white font-medium">
                          {row.funcionario_nome}
                        </TableCell>
                        <TableCell className="text-slate-300">{row.turno}</TableCell>
                        <TableCell className="text-slate-300 text-right">
                          {formatBRL(row.valor_dinheiro)}
                        </TableCell>
                        <TableCell className="text-slate-300 text-right">
                          {formatBRL(row.valor_cheque)}
                        </TableCell>
                        <TableCell className="text-slate-300 text-right">
                          {formatBRL(row.valor_pix)}
                        </TableCell>
                        <TableCell className="text-slate-300 text-right">
                          {formatBRL(row.valor_cartao)}
                        </TableCell>
                      </TableRow>
                    ))}
                    {operatorDetails.length === 0 && (
                      <TableRow className="border-white/5">
                        <TableCell colSpan={6} className="text-center text-slate-400">
                          Nenhum detalhamento por operador disponível
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            <Card className="bg-slate-900 border-white/5">
              <CardHeader>
                <CardTitle className="text-white">Matriz de Anomalias</CardTitle>
                <CardDescription className="text-slate-400">
                  Filiais com despesas acima da média do grupo
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow className="border-white/5 hover:bg-white/5">
                      <TableHead className="text-slate-300">Filial</TableHead>
                      <TableHead className="text-slate-300 text-right">Despesa</TableHead>
                      <TableHead className="text-slate-300 text-right">Média Grupo</TableHead>
                      <TableHead className="text-slate-300 text-right">Desvio</TableHead>
                      <TableHead className="text-slate-300 text-right">Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {expensesByCompany.map((row) => {
                      const val = Number(row.valor || 0);
                      const deviation = val - avgExpense;
                      const above = deviation > 0;
                      return (
                        <TableRow
                          key={row.empresa_codigo}
                          className="border-white/5 hover:bg-white/5"
                        >
                          <TableCell className="text-white font-medium">{row.nome}</TableCell>
                          <TableCell className="text-slate-300 text-right">
                            {formatBRL(row.valor)}
                          </TableCell>
                          <TableCell className="text-slate-300 text-right">
                            {formatBRL(avgExpense)}
                          </TableCell>
                          <TableCell
                            className={cn(
                              "text-right",
                              above && "text-red-300",
                              !above && "text-emerald-300"
                            )}
                          >
                            {above ? "+" : ""}
                            {formatBRL(deviation)}
                          </TableCell>
                          <TableCell className="text-right">
                            <Badge
                              variant="outline"
                              className={cn(
                                above
                                  ? "bg-red-500/10 text-red-300 border-red-500/20"
                                  : "bg-emerald-500/10 text-emerald-300 border-emerald-500/20"
                              )}
                            >
                              {above ? "ANOMALIA" : "NORMAL"}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                    {expensesByCompany.length === 0 && (
                      <TableRow className="border-white/5">
                        <TableCell colSpan={5} className="text-center text-slate-400">
                          Nenhuma despesa disponível
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </ReportLayout>
  );
}
