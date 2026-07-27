"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Droplet, Wallet, Receipt, FileText, Download, RefreshCcw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { apiService } from "@/lib/api";
import { ExecutiveReport } from "@/types/api";
import { cn } from "@/lib/utils";

const REPORT_CARDS = [
  {
    title: "Pista & Volumetria",
    description: "Volume (L) e faturamento por produto e filial",
    href: "/executive/reports/fuel",
    icon: Droplet,
    color: "text-blue-400",
    bg: "bg-blue-500/10",
  },
  {
    title: "Auditoria de Caixa",
    description: "Rombo por operador, turno e meio de pagamento",
    href: "/executive/reports/cash-audit",
    icon: Wallet,
    color: "text-amber-400",
    bg: "bg-amber-500/10",
  },
  {
    title: "DRE & Despesas",
    description: "Despesas de pessoal vs operacionais por filial",
    href: "/executive/reports/expenses",
    icon: Receipt,
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
  },
];

export default function ReportsCenterPage() {
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
    let active = true;
    apiService.getExecutiveConsolidatedReport()
      .then((data) => { if (active) { setReport(data); setError(null); } })
      .catch((err) => { if (active) { setError(err instanceof Error ? err.message : "Erro ao carregar"); } })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const downloadMarkdown = async () => {
    try {
      const markdown = await apiService.getExecutiveConsolidatedReportMarkdown();
      const blob = new Blob([markdown], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `relatorio_executivo_sprint55_${new Date().toISOString().split("T")[0]}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erro ao exportar Markdown";
      setError(message);
    }
  };

  const printPdf = () => {
    window.print();
  };

  const formatBRL = (val: string) => {
    try {
      return new Intl.NumberFormat("pt-BR", {
        style: "currency",
        currency: "BRL",
      }).format(Number(val || 0));
    } catch {
      return "R$ 0,00";
    }
  };

  const formatNumber = (val: string) => {
    try {
      return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 }).format(
        Number(val || 0)
      );
    } catch {
      return "0";
    }
  };

  return (
    <div className="p-4 lg:p-8 max-w-[1600px] mx-auto space-y-6">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Central de Relatórios Executivos</h1>
          <p className="text-slate-400 text-sm">Sprint 55 — Dados reais da integração WebPosto</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={downloadMarkdown}
            disabled={loading || !report}
            className="bg-slate-900 border-white/5 hover:bg-white/5"
          >
            <FileText size={14} className="mr-2" /> Markdown
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={printPdf}
            disabled={loading || !report}
            className="bg-slate-900 border-white/5 hover:bg-white/5"
          >
            <Download size={14} className="mr-2" /> PDF
          </Button>
          <Button size="sm" onClick={fetchReport} disabled={loading}>
            <RefreshCcw size={14} className={cn("mr-2", loading && "animate-spin")} /> Atualizar
          </Button>
        </div>
      </header>

      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-4 text-red-200">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {loading ? (
          <>
            <Skeleton className="h-32 bg-slate-900" />
            <Skeleton className="h-32 bg-slate-900" />
            <Skeleton className="h-32 bg-slate-900" />
          </>
        ) : (
          <>
            <Card className="bg-slate-900 border-white/5">
              <CardContent className="p-6">
                <p className="text-sm text-slate-400">Volume Total</p>
                <p className="text-2xl font-bold text-white mt-1">
                  {formatNumber(report?.bloco_1_combustiveis.resumo.total_litros || "0")} L
                </p>
              </CardContent>
            </Card>
            <Card className="bg-slate-900 border-white/5">
              <CardContent className="p-6">
                <p className="text-sm text-slate-400">Faturamento Pista</p>
                <p className="text-2xl font-bold text-white mt-1">
                  {formatBRL(report?.bloco_1_combustiveis.resumo.total_valor || "0")}
                </p>
              </CardContent>
            </Card>
            <Card className="bg-slate-900 border-white/5">
              <CardContent className="p-6">
                <p className="text-sm text-slate-400">Divergência de Caixa</p>
                <p className="text-2xl font-bold text-white mt-1">
                  {formatBRL(report?.bloco_9_anomalias.divergencias_caixa.valor_divergente || "0")}
                </p>
              </CardContent>
            </Card>
          </>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {REPORT_CARDS.map((item) => {
          const Icon = item.icon;
          return (
            <Link key={item.href} href={item.href} className="group">
              <Card className="bg-slate-900 border-white/5 transition hover:bg-white/[0.02] h-full">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className={cn("grid size-10 place-items-center rounded-lg", item.bg)}>
                      <Icon className={cn("size-5", item.color)} />
                    </div>
                    <Badge variant="outline" className="bg-slate-950 border-white/10 text-slate-300">
                      Disponível
                    </Badge>
                  </div>
                  <CardTitle className="text-lg text-white mt-3">{item.title}</CardTitle>
                  <CardDescription className="text-slate-400">{item.description}</CardDescription>
                </CardHeader>
              </Card>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
