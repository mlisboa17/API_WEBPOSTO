"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Droplet, Fuel, TrendingUp, Building2 } from "lucide-react";
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
import { matchesEmpresa, resolveEmpresaCodigo } from "@/utils/filial_normalizer";

export default function FuelReportPage() {
  const [report, setReport] = useState<ExecutiveReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const {
    selectedFilial,
    isConsolidated,
    periodDates,
    filialLabel,
  } = useReportFilter();

  const empresaResolvida = resolveEmpresaCodigo(isConsolidated ? null : selectedFilial);

  const fetchReport = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiService.getExecutiveConsolidatedReport(
        periodDates.start,
        periodDates.end,
        empresaResolvida ?? undefined
      );
      setReport(data);
      setError(null);
    } catch (err) {
      setReport(null);
      setError(err instanceof Error ? err.message : "Erro ao carregar");
    } finally {
      setLoading(false);
    }
  }, [periodDates.start, periodDates.end, empresaResolvida]);

  useEffect(() => {
    void fetchReport();
  }, [fetchReport]);

  const formatBRL = (val: string | number) => {
    try {
      return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(
        Number(val || 0)
      );
    } catch {
      return "R$ 0,00";
    }
  };

  /** Volumetria sempre com 3 casas decimais (ex.: 1.234,567 L). */
  const formatLitros = (val: string | number) => {
    try {
      return new Intl.NumberFormat("pt-BR", {
        minimumFractionDigits: 3,
        maximumFractionDigits: 3,
      }).format(Number(val || 0));
    } catch {
      return "0,000";
    }
  };

  const formatInt = (val: string | number) => {
    try {
      return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(Number(val || 0));
    } catch {
      return "0";
    }
  };

  const { byProduct, byFilial, totalLitros, totalValor, filiaisAtivas, margensFiltradas } =
    useMemo(() => {
      const allProducts = report?.bloco_1_combustiveis.resumo.por_produto || [];
      const allFiliais = report?.bloco_1_combustiveis.resumo.por_filial || [];
      const allMargens = report?.bloco_3_margens.faturamento_por_litro || [];

      const filteredProducts = isConsolidated
        ? allProducts
        : allProducts.filter((p) => matchesEmpresa(p.empresa_codigo, selectedFilial));

      const filteredFiliais = isConsolidated
        ? allFiliais
        : allFiliais.filter((f) => matchesEmpresa(f.empresa_codigo, selectedFilial));

      const filteredMargens = isConsolidated
        ? allMargens
        : allMargens.filter((m) => matchesEmpresa(m.empresa_codigo, selectedFilial));

      const productMap = new Map<string, { litros: number; valor: number; transacoes: number }>();
      for (const row of filteredProducts) {
        const cur = productMap.get(row.produto) || { litros: 0, valor: 0, transacoes: 0 };
        cur.litros += Number(row.litros || 0);
        cur.valor += Number(row.valor || 0);
        cur.transacoes += Number(row.transacoes || 0);
        productMap.set(row.produto, cur);
      }

      const filialMap = new Map<
        string,
        { empresa_codigo: number; nome: string; litros: number; valor: number; transacoes: number }
      >();
      for (const row of filteredFiliais) {
        const code = Number(row.empresa_codigo);
        const cur = filialMap.get(String(code)) || {
          empresa_codigo: code,
          nome: row.nome_filial,
          litros: 0,
          valor: 0,
          transacoes: 0,
        };
        cur.litros += Number(row.litros || 0);
        cur.valor += Number(row.valor || 0);
        cur.transacoes += Number(row.transacoes || 0);
        filialMap.set(String(code), cur);
      }

      const byProductArr = Array.from(productMap.entries()).map(([produto, agg]) => ({
        produto,
        ...agg,
      }));

      const byFilialArr = Array.from(filialMap.values()).sort((a, b) => b.litros - a.litros);

      // Prefer totals from API when already filtered server-side; else aggregate.
      const apiLitros = Number(report?.bloco_1_combustiveis.resumo.total_litros || 0);
      const apiValor = Number(report?.bloco_1_combustiveis.resumo.total_valor || 0);
      const totLitros =
        !isConsolidated && apiLitros > 0
          ? apiLitros
          : byFilialArr.reduce((s, f) => s + f.litros, 0) ||
            byProductArr.reduce((s, p) => s + p.litros, 0);
      const totValor =
        !isConsolidated && apiValor > 0
          ? apiValor
          : byFilialArr.reduce((s, f) => s + f.valor, 0) ||
            byProductArr.reduce((s, p) => s + p.valor, 0);

      return {
        byProduct: byProductArr,
        byFilial: byFilialArr,
        totalLitros: totLitros,
        totalValor: totValor,
        filiaisAtivas: byFilialArr.length,
        margensFiltradas: filteredMargens,
      };
    }, [report, selectedFilial, isConsolidated]);

  useEffect(() => {
    if (loading) return;
    if (totalLitros > 0 || totalValor > 0) return;
    console.warn(
      `[Pista & Volumetria] Filial buscada: ${filialLabel} (${selectedFilial}) | ID resolvido: ${
        empresaResolvida ?? "TODAS"
      }`
    );
  }, [
    loading,
    totalLitros,
    totalValor,
    filialLabel,
    selectedFilial,
    empresaResolvida,
  ]);

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
      title="Relatório de Pista & Volumetria"
      subtitle="Volume e faturamento por produto e filial"
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
        <div
          key={`fuel-${empresaResolvida ?? "all"}-${periodDates.start}-${periodDates.end}`}
          className="space-y-6"
        >
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card className="bg-slate-900 border-white/5">
              <CardContent className="p-6">
                <div className="flex items-center gap-3">
                  <div className="grid size-10 place-items-center rounded-lg bg-blue-500/10">
                    <Droplet className="size-5 text-blue-400" />
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <p className="text-sm text-slate-400">Volume Total</p>
                      <InfoTooltip content="Soma de todos os litros vendidos na pista no período selecionado, incluindo Gasolina Comum, Aditivada, Etanol e Diesel." />
                    </div>
                    <p className="text-xl font-bold text-white">{formatLitros(totalLitros)} L</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="bg-slate-900 border-white/5">
              <CardContent className="p-6">
                <div className="flex items-center gap-3">
                  <div className="grid size-10 place-items-center rounded-lg bg-emerald-500/10">
                    <Fuel className="size-5 text-emerald-400" />
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <p className="text-sm text-slate-400">Faturamento Pista</p>
                      <InfoTooltip content="Receita bruta total da venda de combustíveis. Valor capturado direto do registro de cada abastecimento." />
                    </div>
                    <p className="text-xl font-bold text-white">{formatBRL(totalValor)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="bg-slate-900 border-white/5">
              <CardContent className="p-6">
                <div className="flex items-center gap-3">
                  <div className="grid size-10 place-items-center rounded-lg bg-amber-500/10">
                    <TrendingUp className="size-5 text-amber-400" />
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <p className="text-sm text-slate-400">Ticket Médio</p>
                      <InfoTooltip content="Preço médio por litro vendido. Calculado dividindo o faturamento total pelo volume total em litros." />
                    </div>
                    <p className="text-xl font-bold text-white">
                      {formatBRL(totalLitros > 0 ? totalValor / totalLitros : 0)}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="bg-slate-900 border-white/5">
              <CardContent className="p-6">
                <div className="flex items-center gap-3">
                  <div className="grid size-10 place-items-center rounded-lg bg-purple-500/10">
                    <Building2 className="size-5 text-purple-400" />
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <p className="text-sm text-slate-400">Filiais Ativas</p>
                      <InfoTooltip content="Quantidade de postos com movimentação de combustível no período selecionado." />
                    </div>
                    <p className="text-xl font-bold text-white">{filiaisAtivas}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card className="bg-slate-900 border-white/5">
            <CardHeader>
              <CardTitle className="text-white">Volume por Produto</CardTitle>
              <CardDescription className="text-slate-400">
                Agrupado por tipo de combustível
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow className="border-white/5 hover:bg-white/5">
                    <TableHead className="text-slate-300">Produto</TableHead>
                    <TableHead className="text-slate-300 text-right">Litros</TableHead>
                    <TableHead className="text-slate-300 text-right">Faturamento</TableHead>
                    <TableHead className="text-slate-300 text-right">Transações</TableHead>
                    <TableHead className="text-slate-300 text-right">Participação</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {byProduct.map((row) => {
                    const pct = totalLitros > 0 ? (row.litros / totalLitros) * 100 : 0;
                    return (
                      <TableRow key={row.produto} className="border-white/5 hover:bg-white/5">
                        <TableCell className="text-white font-medium">{row.produto}</TableCell>
                        <TableCell className="text-slate-300 text-right">
                          {formatLitros(row.litros)} L
                        </TableCell>
                        <TableCell className="text-slate-300 text-right">
                          {formatBRL(row.valor)}
                        </TableCell>
                        <TableCell className="text-slate-300 text-right">
                          {formatInt(row.transacoes)}
                        </TableCell>
                        <TableCell className="text-right">
                          <Badge
                            variant="outline"
                            className="bg-blue-500/10 text-blue-300 border-blue-500/20"
                          >
                            {pct.toFixed(1)}%
                          </Badge>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                  {byProduct.length === 0 && (
                    <TableRow className="border-white/5">
                      <TableCell colSpan={5} className="text-center text-slate-400">
                        Nenhum dado de combustível disponível
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {isConsolidated && (
            <Card className="bg-slate-900 border-white/5">
              <CardHeader>
                <CardTitle className="text-white">Ranking por Filial</CardTitle>
                <CardDescription className="text-slate-400">
                  Filiais ordenadas por volume de vendas
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow className="border-white/5 hover:bg-white/5">
                      <TableHead className="text-slate-300">Filial</TableHead>
                      <TableHead className="text-slate-300 text-right">Litros</TableHead>
                      <TableHead className="text-slate-300 text-right">Faturamento</TableHead>
                      <TableHead className="text-slate-300 text-right">Transações</TableHead>
                      <TableHead className="text-slate-300 text-right">Participação</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {byFilial.map((row, index) => {
                      const pct = totalLitros > 0 ? (row.litros / totalLitros) * 100 : 0;
                      return (
                        <TableRow
                          key={row.empresa_codigo}
                          className="border-white/5 hover:bg-white/5"
                        >
                          <TableCell className="text-white font-medium">
                            <span className="inline-block w-6 text-slate-500">{index + 1}.</span>{" "}
                            {row.nome}
                          </TableCell>
                          <TableCell className="text-slate-300 text-right">
                            {formatLitros(row.litros)} L
                          </TableCell>
                          <TableCell className="text-slate-300 text-right">
                            {formatBRL(row.valor)}
                          </TableCell>
                          <TableCell className="text-slate-300 text-right">
                            {formatInt(row.transacoes)}
                          </TableCell>
                          <TableCell className="text-right">
                            <Badge
                              variant="outline"
                              className="bg-blue-500/10 text-blue-300 border-blue-500/20"
                            >
                              {pct.toFixed(1)}%
                            </Badge>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}

          <Card className="bg-slate-900 border-white/5">
            <CardHeader>
              <CardTitle className="text-white">Margem por Litro</CardTitle>
              <CardDescription className="text-slate-400">
                Receita por litro por filial (Bloco 3)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow className="border-white/5 hover:bg-white/5">
                    <TableHead className="text-slate-300">Filial</TableHead>
                    <TableHead className="text-slate-300 text-right">Litros</TableHead>
                    <TableHead className="text-slate-300 text-right">Faturamento</TableHead>
                    <TableHead className="text-slate-300 text-right">R$/L</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {margensFiltradas.map((row) => (
                    <TableRow key={row.empresa_codigo} className="border-white/5 hover:bg-white/5">
                      <TableCell className="text-white font-medium">{row.nome}</TableCell>
                      <TableCell className="text-slate-300 text-right">
                        {formatLitros(row.litros)} L
                      </TableCell>
                      <TableCell className="text-slate-300 text-right">
                        {formatBRL(row.valor)}
                      </TableCell>
                      <TableCell className="text-right">
                        <Badge
                          variant="outline"
                          className="bg-emerald-500/10 text-emerald-300 border-emerald-500/20"
                        >
                          {formatBRL(row.receita_por_litro)}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                  {margensFiltradas.length === 0 && (
                    <TableRow className="border-white/5">
                      <TableCell colSpan={4} className="text-center text-slate-400">
                        Nenhum dado de margem disponível
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      )}
    </ReportLayout>
  );
}
