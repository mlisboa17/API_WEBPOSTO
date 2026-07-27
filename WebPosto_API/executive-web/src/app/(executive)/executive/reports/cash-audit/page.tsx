"use client";

import React, { useEffect, useState, useCallback, useMemo } from "react";
import { Wallet, AlertTriangle, Receipt, TrendingDown, Building2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiService } from "@/lib/api";
import { ExecutiveReport } from "@/types/api";
import { ReportLayout } from "@/components/executive/report-layout";
import { cn } from "@/lib/utils";

export default function CashAuditReportPage() {
  const [report, setReport] = useState<ExecutiveReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchReport = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiService.getExecutiveConsolidatedReport();
      setReport(data);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erro ao carregar relatório";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  const formatBRL = (val: string) => {
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
  const paymentDetails = report?.bloco_9_anomalias.detalhamento_pagamento || [];
  const operatorDetails = report?.bloco_9_anomalias.rombo_por_operador_turno || [];
  const expensesByCompany = report?.bloco_6_despesas.por_empresa || [];

  const avgExpense = useMemo(() => {
    if (expensesByCompany.length === 0) return 0;
    return expensesByCompany.reduce((acc, cur) => acc + Number(cur.valor || 0), 0) / expensesByCompany.length;
  }, [expensesByCompany]);

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
                    <p className="text-sm text-slate-400">Valor Apurado</p>
                    <p className="text-xl font-bold text-white">{formatBRL(reconciliation?.valor_apurado || "0")}</p>
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
                    <p className="text-sm text-slate-400">Valor Apresentado</p>
                    <p className="text-xl font-bold text-white">{formatBRL(reconciliation?.valor_apresentado || "0")}</p>
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
                    <p className="text-sm text-slate-400">Divergente</p>
                    <p className="text-xl font-bold text-white">{formatBRL(reconciliation?.valor_divergente || "0")}</p>
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
                    <p className="text-sm text-slate-400">Pendente</p>
                    <p className="text-xl font-bold text-white">{formatBRL(reconciliation?.valor_pendente || "0")}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

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
                  {(reconciliation?.naturezas || []).map((row) => {
                    const diff = Number(row.diferenca || 0);
                    const status = diff === 0 ? "OK" : diff > 0 ? "SOBRA" : "FALTA";
                    return (
                      <TableRow key={row.natureza} className="border-white/5 hover:bg-white/5">
                        <TableCell className="text-white font-medium">{row.label}</TableCell>
                        <TableCell className="text-slate-300 text-right">{formatBRL(row.valor_apurado)}</TableCell>
                        <TableCell className="text-slate-300 text-right">{formatBRL(row.valor_apresentado)}</TableCell>
                        <TableCell className={cn("text-right", diff < 0 && "text-red-300", diff > 0 && "text-emerald-300")}>
                          {formatBRL(row.diferenca)}
                        </TableCell>
                        <TableCell className="text-right">
                          <Badge
                            variant="outline"
                            className={cn(
                              status === "OK" && "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
                              status === "SOBRA" && "bg-amber-500/10 text-amber-300 border-amber-500/20",
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
                      <TableRow key={`${row.funcionario_codigo}-${row.turno}`} className="border-white/5 hover:bg-white/5">
                        <TableCell className="text-white font-medium">{row.funcionario_nome}</TableCell>
                        <TableCell className="text-slate-300">{row.turno}</TableCell>
                        <TableCell className="text-slate-300 text-right">{formatBRL(row.valor_dinheiro)}</TableCell>
                        <TableCell className="text-slate-300 text-right">{formatBRL(row.valor_cheque)}</TableCell>
                        <TableCell className="text-slate-300 text-right">{formatBRL(row.valor_pix)}</TableCell>
                        <TableCell className="text-slate-300 text-right">{formatBRL(row.valor_cartao)}</TableCell>
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
                        <TableRow key={row.empresa_codigo} className="border-white/5 hover:bg-white/5">
                          <TableCell className="text-white font-medium">{row.nome}</TableCell>
                          <TableCell className="text-slate-300 text-right">{formatBRL(row.valor)}</TableCell>
                          <TableCell className="text-slate-300 text-right">{formatBRL(avgExpense.toString())}</TableCell>
                          <TableCell className={cn("text-right", above && "text-red-300", !above && "text-emerald-300")}>
                            {above ? "+" : ""}
                            {formatBRL(deviation.toString())}
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
