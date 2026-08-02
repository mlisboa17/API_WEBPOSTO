"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Receipt, Users, Wrench, AlertCircle } from "lucide-react";
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
import { matchesEmpresa, resolveEmpresaCodigo } from "@/utils/filial_normalizer";

const PERSONAL_KEYWORDS = [
  "pessoal",
  "salario",
  "folha",
  "encargo",
  "beneficio",
  "comissao",
  "hora extra",
  "fgts",
  "inss",
];
const OPERATIONAL_KEYWORDS = [
  "operacional",
  "energia",
  "agua",
  "manutencao",
  "frete",
  "seguranca",
  "taxa",
  "mdr",
  "imposto",
  "aluguel",
  "limpeza",
  "telefone",
  "internet",
];

function classifyCategory(category: string): "pessoal" | "operacional" | "outro" {
  const lower = category.toLowerCase();
  if (PERSONAL_KEYWORDS.some((k) => lower.includes(k))) return "pessoal";
  if (OPERATIONAL_KEYWORDS.some((k) => lower.includes(k))) return "operacional";
  return "outro";
}

type FastReport = ExecutiveReport & {
  fonte?: string;
  fromCache?: boolean;
  latencyMs?: number;
};

export default function ExpensesReportPage() {
  const [report, setReport] = useState<FastReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { selectedFilial, isConsolidated, periodDates, filialLabel } = useReportFilter();
  const empresaResolvida = resolveEmpresaCodigo(isConsolidated ? null : selectedFilial);

  const fetchReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiService.getExpensesDreReport(
        periodDates.start,
        periodDates.end,
        empresaResolvida
      );
      setReport(data);
    } catch (err) {
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

  const formatNumber = (val: string | number) => {
    try {
      return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(Number(val || 0));
    } catch {
      return "0";
    }
  };

  const {
    categories,
    autoClassified,
    totalRevenue,
    totalPessoal,
    totalOperacional,
    totalExpenses,
    personnelImpact,
    remainingUnclassified,
    dreByCompany,
  } = useMemo(() => {
    const allCategories = report?.bloco_6_despesas?.por_categoria || [];
    const facts =
      report?.bloco_6_despesas?.auto_classificadas?.length
        ? report.bloco_6_despesas.auto_classificadas
        : report?.bloco_5_dre?.despesas_auto_classificadas || [];
    const allDreLines = report?.bloco_5_dre?.departamentos_confirmados || [];

    const filteredAutoClassified = isConsolidated
      ? facts
      : facts.filter((a) => matchesEmpresa(a.company_code, selectedFilial));

    const filteredDreLines = isConsolidated
      ? allDreLines
      : allDreLines.filter((d) => matchesEmpresa(d.empresa_codigo, selectedFilial));

    // Receita real da pista (API já filtra por filial) — sem hack /3
    const fuel = Number(report?.bloco_1_combustiveis?.resumo?.total_valor || 0);
    const conv = Number(report?.bloco_4_conveniencia?.receita_total || 0);
    const revenue = fuel + conv;

    let pessoal = 0;
    let operacional = 0;
    let outros = 0;
    for (const row of allCategories) {
      const type = classifyCategory(row.categoria);
      const val = Number(row.valor || 0);
      if (type === "pessoal") pessoal += val;
      else if (type === "operacional") operacional += val;
      else outros += val;
    }

    const totalFromCats = pessoal + operacional + outros;
    const totalApi = Number(report?.bloco_6_despesas?.total_despesas_gerenciais || 0);
    const total = totalFromCats > 0 ? totalFromCats : totalApi;
    const impact = revenue > 0 ? (pessoal / revenue) * 100 : 0;
    const unclassified =
      report?.bloco_5_dre?.resumo_auto_classificacao?.remanescentes_nao_classificadas || 0;

    const dreMap = new Map<
      string,
      { empresa_codigo: number; nome: string; departamentos: string[]; amount: number }
    >();
    for (const line of filteredDreLines) {
      const key = String(line.empresa_codigo);
      const cur = dreMap.get(key) || {
        empresa_codigo: Number(line.empresa_codigo),
        nome: line.nome,
        departamentos: [] as string[],
        amount: 0,
      };
      if (!cur.departamentos.includes(line.departamento)) cur.departamentos.push(line.departamento);
      cur.amount += Number(line.confirmed_dre_amount || 0);
      dreMap.set(key, cur);
    }

    return {
      categories: allCategories,
      autoClassified: filteredAutoClassified,
      totalRevenue: revenue,
      totalPessoal: pessoal,
      totalOperacional: operacional,
      totalExpenses: total,
      personnelImpact: impact,
      remainingUnclassified: unclassified,
      dreByCompany: Array.from(dreMap.values()),
    };
  }, [report, selectedFilial, isConsolidated]);

  useEffect(() => {
    if (loading) return;
    if (totalExpenses > 0 || totalRevenue > 0) return;
    console.warn(
      `[DRE & Despesas] Filial: ${filialLabel} (${selectedFilial}) | ID: ${
        empresaResolvida ?? "TODAS"
      }`
    );
  }, [loading, totalExpenses, totalRevenue, filialLabel, selectedFilial, empresaResolvida]);

  const renderSkeleton = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28 bg-slate-900" />
        ))}
      </div>
      <Skeleton className="h-48 bg-slate-900" />
      <Skeleton className="h-64 bg-slate-900" />
    </div>
  );

  return (
    <ReportLayout
      title="DRE & Despesas Classificadas"
      subtitle="Visão tabular de pessoal vs operacional e impacto sobre receita"
      loading={loading && !report}
    >
      <div className="mb-6">
        <ReportFilterBar />
      </div>

      {loading && !report ? (
        renderSkeleton()
      ) : error && !report ? (
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-4 text-red-200">
          {error}
        </div>
      ) : (
        <div
          key={`exp-${empresaResolvida ?? "all"}-${periodDates.start}-${periodDates.end}`}
          className={cn("space-y-6", loading && "opacity-70 transition-opacity")}
        >
          {(report?.fonte || report?.latencyMs != null || error) && (
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
              {report?.fonte && (
                <Badge className="bg-emerald-500/15 text-emerald-300 border-emerald-500/30 text-[10px]">
                  {report.fonte}
                  {report.fromCache ? " · local" : ""}
                </Badge>
              )}
              {report?.latencyMs != null && (
                <span className="font-mono">{Number(report.latencyMs).toFixed(1)} ms</span>
              )}
              {loading && <span className="text-cyan-400">Atualizando…</span>}
              {error && <span className="text-amber-400">{error}</span>}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card className="bg-slate-900 border-white/5">
              <CardContent className="p-6">
                <div className="flex items-center gap-3">
                  <div className="grid size-10 place-items-center rounded-lg bg-blue-500/10">
                    <Receipt className="size-5 text-blue-400" />
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <p className="text-sm text-slate-400">Total Despesas</p>
                      <InfoTooltip content="Soma de todas as despesas registradas no período, incluindo custos de pessoal, operacionais e outras categorias." />
                    </div>
                    <p className="text-xl font-bold text-white">{formatBRL(totalExpenses)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="bg-slate-900 border-white/5">
              <CardContent className="p-6">
                <div className="flex items-center gap-3">
                  <div className="grid size-10 place-items-center rounded-lg bg-purple-500/10">
                    <Users className="size-5 text-purple-400" />
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <p className="text-sm text-slate-400">Despesas Pessoal</p>
                      <InfoTooltip content="Custos com recursos humanos: salários, folha de pagamento, encargos trabalhistas (FGTS, INSS), benefícios e comissões." />
                    </div>
                    <p className="text-xl font-bold text-white">{formatBRL(totalPessoal)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="bg-slate-900 border-white/5">
              <CardContent className="p-6">
                <div className="flex items-center gap-3">
                  <div className="grid size-10 place-items-center rounded-lg bg-amber-500/10">
                    <Wrench className="size-5 text-amber-400" />
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <p className="text-sm text-slate-400">Despesas Operacionais</p>
                      <InfoTooltip content="Custos de funcionamento do posto: energia, água, manutenção, frete, segurança, taxas/MDR, aluguel e telecomunicações." />
                    </div>
                    <p className="text-xl font-bold text-white">{formatBRL(totalOperacional)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card className="bg-slate-900 border-white/5">
              <CardContent className="p-6">
                <div className="flex items-center gap-3">
                  <div className="grid size-10 place-items-center rounded-lg bg-red-500/10">
                    <AlertCircle className="size-5 text-red-400" />
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <p className="text-sm text-slate-400">Pendentes Classificação</p>
                      <InfoTooltip content="Despesas que ainda não foram categorizadas automaticamente e requerem revisão manual da gestão." />
                    </div>
                    <p className="text-xl font-bold text-white">
                      {formatNumber(remainingUnclassified)}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card className="bg-slate-900 border-white/5">
            <CardHeader>
              <CardTitle className="text-white">
                Impacto do Custo de Pessoal sobre Receita Bruta
              </CardTitle>
              <CardDescription className="text-slate-400">
                Receita bruta pista (período/filial): {formatBRL(totalRevenue)}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-slate-300">Custo de pessoal / receita bruta</span>
                <span
                  className={cn("font-bold", personnelImpact > 20 ? "text-red-400" : "text-white")}
                >
                  {personnelImpact.toFixed(1)}%
                </span>
              </div>
              <div className="h-3 w-full rounded-full bg-slate-800 overflow-hidden">
                <div
                  className={cn(
                    "h-full rounded-full transition-all",
                    personnelImpact > 20 ? "bg-red-500" : "bg-blue-500"
                  )}
                  style={{ width: `${Math.min(personnelImpact, 100)}%` }}
                />
              </div>
              <p className="text-xs text-slate-500">
                {personnelImpact > 20
                  ? "Impacto elevado: custo de pessoal consome mais de 20% da receita bruta."
                  : "Impacto dentro da faixa operacional saudável."}
              </p>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="bg-slate-900 border-white/5">
              <CardHeader>
                <CardTitle className="text-white">Despesas por Categoria</CardTitle>
                <CardDescription className="text-slate-400">
                  Classificadas em Pessoal ou Operacional
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow className="border-white/5 hover:bg-white/5">
                      <TableHead className="text-slate-300">Categoria</TableHead>
                      <TableHead className="text-slate-300">Natureza</TableHead>
                      <TableHead className="text-slate-300 text-right">Valor</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {categories.map((row) => {
                      const type = classifyCategory(row.categoria);
                      return (
                        <TableRow key={row.categoria} className="border-white/5 hover:bg-white/5">
                          <TableCell className="text-white font-medium">{row.categoria}</TableCell>
                          <TableCell>
                            <Badge
                              variant="outline"
                              className={cn(
                                type === "pessoal" &&
                                  "bg-purple-500/10 text-purple-300 border-purple-500/20",
                                type === "operacional" &&
                                  "bg-amber-500/10 text-amber-300 border-amber-500/20",
                                type === "outro" &&
                                  "bg-slate-500/10 text-slate-300 border-slate-500/20"
                              )}
                            >
                              {type === "pessoal"
                                ? "Pessoal"
                                : type === "operacional"
                                  ? "Operacional"
                                  : "Outro"}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-slate-300 text-right">
                            {formatBRL(row.valor)}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                    {categories.length === 0 && (
                      <TableRow className="border-white/5">
                        <TableCell colSpan={3} className="text-center text-slate-400">
                          Nenhuma categoria disponível
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            <Card className="bg-slate-900 border-white/5">
              <CardHeader>
                <CardTitle className="text-white">DRE por Filial</CardTitle>
                <CardDescription className="text-slate-400">
                  Departamentos confirmados e valores DRE
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow className="border-white/5 hover:bg-white/5">
                      <TableHead className="text-slate-300">Filial</TableHead>
                      <TableHead className="text-slate-300">Departamentos</TableHead>
                      <TableHead className="text-slate-300 text-right">Valor DRE</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {dreByCompany.map((row) => (
                      <TableRow key={row.empresa_codigo} className="border-white/5 hover:bg-white/5">
                        <TableCell className="text-white font-medium">{row.nome}</TableCell>
                        <TableCell className="text-slate-300">
                          {row.departamentos.join(", ")}
                        </TableCell>
                        <TableCell className="text-slate-300 text-right">
                          {formatBRL(row.amount)}
                        </TableCell>
                      </TableRow>
                    ))}
                    {dreByCompany.length === 0 && (
                      <TableRow className="border-white/5">
                        <TableCell colSpan={3} className="text-center text-slate-400">
                          Nenhuma linha DRE confirmada
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>

          <Card className="bg-slate-900 border-white/5">
            <CardHeader>
              <CardTitle className="text-white">Despesas Auto-classificadas</CardTitle>
              <CardDescription className="text-slate-400">
                Total classificadas:{" "}
                {report?.bloco_5_dre?.resumo_auto_classificacao?.total_classificadas ||
                  autoClassified.length}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow className="border-white/5 hover:bg-white/5">
                    <TableHead className="text-slate-300">Filial</TableHead>
                    <TableHead className="text-slate-300">Data</TableHead>
                    <TableHead className="text-slate-300">Categoria</TableHead>
                    <TableHead className="text-slate-300 text-right">Valor</TableHead>
                    <TableHead className="text-slate-300">Texto</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {autoClassified.slice(0, 20).map((row, idx) => (
                    <TableRow
                      key={`${row.fact_id}-${idx}`}
                      className="border-white/5 hover:bg-white/5"
                    >
                      <TableCell className="text-white font-medium">{row.company_name}</TableCell>
                      <TableCell className="text-slate-300">{row.date}</TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className="bg-blue-500/10 text-blue-300 border-blue-500/20"
                        >
                          {row.category}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-slate-300 text-right">
                        {formatBRL(row.amount)}
                      </TableCell>
                      <TableCell className="text-slate-300 max-w-xs truncate" title={row.text}>
                        {row.text}
                      </TableCell>
                    </TableRow>
                  ))}
                  {autoClassified.length === 0 && (
                    <TableRow className="border-white/5">
                      <TableCell colSpan={5} className="text-center text-slate-400">
                        Nenhuma despesa auto-classificada
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
