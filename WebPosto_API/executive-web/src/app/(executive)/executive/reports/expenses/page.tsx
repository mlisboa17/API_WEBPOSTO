"use client";

import React, { useEffect, useState, useMemo } from "react";
import { Receipt, Users, Wrench, AlertCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ReportFilterBar } from "@/components/executive/report-filter-bar";
import { useReportFilter } from "@/contexts/report-filter-context";
import { apiService } from "@/lib/api";
import { ExecutiveReport } from "@/types/api";
import { ReportLayout } from "@/components/executive/report-layout";
import { cn } from "@/lib/utils";

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

export default function ExpensesReportPage() {
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
        if (active) {
          setError(err instanceof Error ? err.message : "Erro ao carregar");
        }
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
    const allCategories = report?.bloco_6_despesas.por_categoria || [];
    const allAutoClassified = report?.bloco_6_despesas.auto_classificadas || [];
    const allDreLines = report?.bloco_5_dre.departamentos_confirmados || [];

    const filteredAutoClassified = isConsolidated
      ? allAutoClassified
      : allAutoClassified.filter((a) => a.company_code === selectedFilial);

    const filteredDreLines = isConsolidated
      ? allDreLines
      : allDreLines.filter((d) => d.empresa_codigo === selectedFilial);

    const fuel = Number(report?.bloco_1_combustiveis.resumo.total_valor || 0);
    const conv = Number(report?.bloco_4_conveniencia.receita_total || 0);
    const revenue = isConsolidated ? fuel + conv : (fuel + conv) / 3;

    let pessoal = 0;
    let operacional = 0;
    let outros = 0;
    for (const row of allCategories) {
      const type = classifyCategory(row.categoria);
      const val = Number(row.valor || 0);
      const adjustedVal = isConsolidated ? val : val / 3;
      if (type === "pessoal") pessoal += adjustedVal;
      else if (type === "operacional") operacional += adjustedVal;
      else outros += adjustedVal;
    }

    const total = pessoal + operacional + outros;
    const impact = revenue > 0 ? (pessoal / revenue) * 100 : 0;
    const unclassified =
      report?.bloco_5_dre.resumo_auto_classificacao.remanescentes_nao_classificadas || 0;

    const dreMap = new Map<
      string,
      { empresa_codigo: number; nome: string; departamentos: string[]; amount: number }
    >();
    for (const line of filteredDreLines) {
      const key = line.empresa_codigo.toString();
      const cur = dreMap.get(key) || {
        empresa_codigo: line.empresa_codigo,
        nome: line.nome,
        departamentos: [],
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
      remainingUnclassified: isConsolidated ? unclassified : Math.ceil(unclassified / 3),
      dreByCompany: Array.from(dreMap.values()),
    };
  }, [report, selectedFilial, isConsolidated]);

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
                    <Receipt className="size-5 text-blue-400" />
                  </div>
                  <div>
                    <p className="text-sm text-slate-400">Total Despesas</p>
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
                    <p className="text-sm text-slate-400">Despesas Pessoal</p>
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
                    <p className="text-sm text-slate-400">Despesas Operacionais</p>
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
                    <p className="text-sm text-slate-400">Pendentes Classificação</p>
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
                Receita bruta total: {formatBRL(totalRevenue)}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-slate-300">Custo de pessoal / receita bruta</span>
                <span className={cn("font-bold", personnelImpact > 20 ? "text-red-400" : "text-white")}>
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
                      const adjustedVal = isConsolidated
                        ? Number(row.valor || 0)
                        : Number(row.valor || 0) / 3;
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
                            {formatBRL(adjustedVal)}
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
                {report?.bloco_5_dre.resumo_auto_classificacao.total_classificadas || 0}
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
