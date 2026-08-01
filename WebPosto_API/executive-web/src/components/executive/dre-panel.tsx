"use client";

import { useMemo, useState } from "react";
import { DreLine } from "@/types/api";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export type DreSegment =
  | "consolidado"
  | "combustiveis"
  | "produtos_pista"
  | "conveniencia";

interface DrePanelProps {
  lines: DreLine[];
  onInspectPending: () => void;
  pendingCount: number;
  /** KPIs opcionais da composição setorial para recalcular a visão por UN */
  sectorKpis?: {
    combustiveis: { fat: number; margem: number; cpv?: number };
    produtos_pista: { fat: number; margem: number; cpv?: number };
    conveniencia: { fat: number; margem: number; cpv?: number };
  };
}

const SEGMENTS: { id: DreSegment; label: string }[] = [
  { id: "consolidado", label: "Visão Consolidada" },
  { id: "combustiveis", label: "Pista / Combustíveis" },
  { id: "produtos_pista", label: "Produtos de Pista" },
  { id: "conveniencia", label: "Conveniência" },
];

const DEPT_MAP: Record<Exclude<DreSegment, "consolidado">, DreLine["department"][]> = {
  combustiveis: ["combustiveis"],
  produtos_pista: ["lubrificantes"],
  conveniencia: ["conveniencia"],
};

export function DrePanel({
  lines,
  onInspectPending,
  pendingCount,
  sectorKpis,
}: DrePanelProps) {
  const [segment, setSegment] = useState<DreSegment>("consolidado");

  const formatBRL = (val: number) =>
    new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(val);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "ESTAVEL":
        return "bg-green-500/10 text-green-500 border-green-500/20";
      case "ALERTA":
        return "bg-yellow-500/10 text-yellow-500 border-yellow-500/20";
      case "CRITICO":
        return "bg-red-500/10 text-red-500 border-red-500/20";
      default:
        return "";
    }
  };

  const getDepartmentLabel = (dept: string) => {
    const labels: Record<string, string> = {
      combustiveis: "Combustíveis",
      conveniencia: "Conveniência",
      lubrificantes: "Produtos de Pista",
      outros: "Outros",
    };
    return labels[dept] || dept;
  };

  const filteredLines = useMemo(() => {
    if (segment === "consolidado") return lines;
    const depts = DEPT_MAP[segment];
    return lines.filter((l) => depts.includes(l.department));
  }, [lines, segment]);

  const summary = useMemo(() => {
    if (segment !== "consolidado" && sectorKpis) {
      const s = sectorKpis[segment];
      const fat = s.fat;
      const margem = s.margem;
      const cpv = s.cpv ?? Math.max(0, fat - margem);
      const desp = filteredLines.reduce((a, l) => a + (l.expenses || 0), 0);
      return {
        fat,
        cpv,
        margem,
        desp,
        resultado: margem - desp,
      };
    }
    const fat = filteredLines.reduce((a, l) => a + (l.revenue || 0), 0);
    const cpv = filteredLines.reduce((a, l) => a + (l.cost || 0), 0);
    const margem = filteredLines.reduce((a, l) => a + (l.grossMargin || 0), 0);
    const desp = filteredLines.reduce((a, l) => a + (l.expenses || 0), 0);
    return { fat, cpv, margem, desp, resultado: margem - desp };
  }, [filteredLines, segment, sectorKpis]);

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <h3 className="text-lg font-semibold text-white">DRE por Unidade de Negócio</h3>
        {pendingCount > 0 && (
          <Button
            variant="outline"
            size="sm"
            className="text-yellow-500 border-yellow-500/20 hover:bg-yellow-500/10 gap-2"
            onClick={onInspectPending}
          >
            <AlertCircle size={14} />
            {pendingCount} Despesas Pendentes
          </Button>
        )}
      </div>

      <div className="flex flex-wrap gap-1 p-1 rounded-lg border border-slate-800 bg-slate-950/50 w-fit">
        {SEGMENTS.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => setSegment(s.id)}
            className={cn(
              "px-3 py-1.5 rounded-md text-xs font-semibold transition-colors",
              segment === s.id
                ? "bg-sky-500/20 text-sky-200 border border-sky-500/40"
                : "text-slate-300 hover:text-white hover:bg-white/5"
            )}
          >
            {s.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-2">
        <KpiMini label="Faturamento" value={formatBRL(summary.fat)} tone="text-white" />
        <KpiMini label="CPV" value={formatBRL(summary.cpv)} tone="text-violet-300" />
        <KpiMini label="Margem Bruta" value={formatBRL(summary.margem)} tone="text-emerald-400" />
        <KpiMini label="Despesas Diretas" value={formatBRL(summary.desp)} tone="text-amber-300" />
        <KpiMini
          label="Resultado"
          value={formatBRL(summary.resultado)}
          tone={summary.resultado < 0 ? "text-rose-400" : "text-sky-300"}
        />
      </div>

      <div className="rounded-md border border-slate-800 bg-slate-900/50">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent border-slate-800">
              <TableHead className="text-slate-300">Unidade</TableHead>
              <TableHead className="text-slate-300">Departamento</TableHead>
              <TableHead className="text-right text-slate-300">Faturamento</TableHead>
              <TableHead className="text-right text-slate-300">Margem Bruta</TableHead>
              <TableHead className="text-right text-slate-300">Despesas</TableHead>
              <TableHead className="text-right text-slate-300">Resultado</TableHead>
              <TableHead className="text-center text-slate-300">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredLines.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-slate-300">
                  {segment === "consolidado"
                    ? "Nenhum dado disponível para o período selecionado."
                    : "Sem linhas DRE para esta unidade — KPIs acima usam composição setorial."}
                </TableCell>
              </TableRow>
            ) : (
              filteredLines.map((line, idx) => (
                <TableRow
                  key={`${line.companyName}-${line.department}-${idx}`}
                  className="border-slate-800"
                >
                  <TableCell className="font-medium text-white">{line.companyName}</TableCell>
                  <TableCell className="capitalize text-slate-200">
                    {getDepartmentLabel(line.department)}
                  </TableCell>
                  <TableCell className="text-right text-white">{formatBRL(line.revenue)}</TableCell>
                  <TableCell className="text-right text-emerald-400">
                    {formatBRL(line.grossMargin)}
                  </TableCell>
                  <TableCell className="text-right text-rose-400">
                    {formatBRL(line.expenses)}
                  </TableCell>
                  <TableCell
                    className={cn(
                      "text-right font-bold",
                      line.operatingResult >= 0 ? "text-emerald-400" : "text-rose-400"
                    )}
                  >
                    {formatBRL(line.operatingResult)}
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge variant="outline" className={getStatusColor(line.status)}>
                      {line.status}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

function KpiMini({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: string;
}) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/50 px-3 py-2">
      <p className="text-[10px] uppercase tracking-wider text-slate-300 font-bold">{label}</p>
      <p className={cn("text-sm font-mono font-bold mt-1", tone)}>{value}</p>
    </div>
  );
}
