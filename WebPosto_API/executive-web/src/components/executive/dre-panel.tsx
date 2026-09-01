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
import {
  buildDelta,
  formatDeltaPct,
  formatDeltaRs,
  type DeltaBlock,
} from "@/lib/dre-variance";
import { formatPctRl, verticalPct } from "@/lib/dre-analytics";

export type DreSegment =
  | "consolidado"
  | "combustiveis"
  | "produtos_pista"
  | "conveniencia";

interface DrePanelProps {
  lines: DreLine[];
  onInspectPending: () => void;
  pendingCount: number;
  /** Regime contábil ativo na DRE (competência vs caixa) */
  regime?: "competencia" | "caixa";
  compareLabel?: string;
  compareSummary?: {
    fat: number;
    cpv: number;
    margem: number;
    desp: number;
    resultado: number;
  };
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
  regime = "competencia",
  compareLabel = "M-1",
  compareSummary,
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

  const deltas = useMemo(() => {
    if (!compareSummary) return null;
    return {
      fat: buildDelta(summary.fat, compareSummary.fat),
      cpv: buildDelta(summary.cpv, compareSummary.cpv),
      margem: buildDelta(summary.margem, compareSummary.margem),
      desp: buildDelta(summary.desp, compareSummary.desp),
      resultado: buildDelta(summary.resultado, compareSummary.resultado),
    };
  }, [summary, compareSummary]);

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-lg font-semibold text-white">DRE por Unidade de Negócio</h3>
          <Badge
            variant="outline"
            className={cn(
              "text-[10px]",
              regime === "caixa"
                ? "border-amber-500/30 text-amber-200"
                : "border-cyan-500/30 text-cyan-200"
            )}
          >
            {regime === "caixa" ? "🏦 Regime de Caixa" : "📄 Competência"}
          </Badge>
          <Badge variant="outline" className="text-[10px] border-sky-500/30 text-sky-200">
            vs {compareLabel}
          </Badge>
        </div>
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
        <KpiMini
          label="Faturamento"
          value={formatBRL(summary.fat)}
          tone="text-white"
          delta={deltas?.fat}
          compareLabel={compareLabel}
          formatBRL={formatBRL}
          emphasize
        />
        <KpiMini
          label="CPV"
          value={formatBRL(summary.cpv)}
          tone="text-violet-300"
          delta={deltas?.cpv}
          compareLabel={compareLabel}
          formatBRL={formatBRL}
          invert
        />
        <KpiMini
          label="Margem Bruta / Resultado Bruto"
          value={formatBRL(summary.margem)}
          tone="text-emerald-300"
          delta={deltas?.margem}
          compareLabel={compareLabel}
          formatBRL={formatBRL}
          emphasize
        />
        <KpiMini
          label="Despesas Diretas"
          value={formatBRL(summary.desp)}
          tone="text-amber-300"
          delta={deltas?.desp}
          compareLabel={compareLabel}
          formatBRL={formatBRL}
          invert
        />
        <KpiMini
          label="Resultado Líquido"
          value={formatBRL(summary.resultado)}
          tone={summary.resultado < 0 ? "text-rose-300" : "text-sky-200"}
          delta={deltas?.resultado}
          compareLabel={compareLabel}
          formatBRL={formatBRL}
          emphasize
        />
      </div>

      {deltas && compareSummary ? (
        <div className="rounded-md border border-slate-800 bg-slate-950/40 overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent border-slate-800">
                <TableHead className="text-slate-300">Linha DRE</TableHead>
                <TableHead className="text-right text-slate-300">Atual (R$)</TableHead>
                <TableHead className="text-right text-slate-300">% RL</TableHead>
                <TableHead className="text-right text-slate-300">
                  Comparativo {compareLabel} (R$)
                </TableHead>
                <TableHead className="text-right text-slate-300">Δ R$</TableHead>
                <TableHead className="text-right text-slate-300">Δ %</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(
                [
                  ["Receita / Faturamento", deltas.fat, false, true],
                  ["CPV", deltas.cpv, true, false],
                  ["Margem Bruta (Resultado Bruto)", deltas.margem, false, true],
                  ["Despesas", deltas.desp, true, false],
                  ["Resultado Líquido", deltas.resultado, false, true],
                ] as const
              ).map(([label, d, invert, emphasize]) => (
                <CompareRow
                  key={label}
                  label={label}
                  delta={d}
                  invert={invert}
                  emphasize={emphasize}
                  formatBRL={formatBRL}
                  receitaLiquida={summary.fat}
                />
              ))}
            </TableBody>
          </Table>
        </div>
      ) : null}

      <div className="rounded-md border border-slate-800 bg-slate-900/50">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent border-slate-800">
              <TableHead className="text-slate-300">Unidade</TableHead>
              <TableHead className="text-slate-300">Departamento</TableHead>
              <TableHead className="text-right text-slate-300">Faturamento</TableHead>
              <TableHead className="text-right text-slate-300">% RL</TableHead>
              <TableHead className="text-right text-slate-300">Margem Bruta</TableHead>
              <TableHead className="text-right text-slate-300">% RL</TableHead>
              <TableHead className="text-right text-slate-300">Despesas</TableHead>
              <TableHead className="text-right text-slate-300">% RL</TableHead>
              <TableHead className="text-right text-slate-300">Resultado</TableHead>
              <TableHead className="text-right text-slate-300">% RL</TableHead>
              <TableHead className="text-center text-slate-300">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredLines.length === 0 ? (
              <TableRow>
                <TableCell colSpan={11} className="text-center py-8 text-slate-300">
                  {segment === "consolidado"
                    ? "Nenhum dado disponível para o período selecionado."
                    : "Sem linhas DRE para esta unidade — KPIs acima usam composição setorial."}
                </TableCell>
              </TableRow>
            ) : (
              filteredLines.map((line, idx) => {
                const rlBase = summary.fat > 0 ? summary.fat : 1;
                return (
                  <TableRow
                    key={`${line.companyName}-${line.department}-${idx}`}
                    className="border-slate-800"
                  >
                    <TableCell className="font-medium text-white">{line.companyName}</TableCell>
                    <TableCell className="capitalize text-slate-200">
                      {getDepartmentLabel(line.department)}
                    </TableCell>
                    <TableCell className="text-right text-white">{formatBRL(line.revenue)}</TableCell>
                    <TableCell className="text-right font-mono text-slate-400 text-xs">
                      {formatPctRl(verticalPct(line.revenue, rlBase))}
                    </TableCell>
                    <TableCell className="text-right text-emerald-400">
                      {formatBRL(line.grossMargin)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-slate-400 text-xs">
                      {formatPctRl(verticalPct(line.grossMargin, rlBase))}
                    </TableCell>
                    <TableCell className="text-right text-rose-400">
                      {formatBRL(line.expenses)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-slate-400 text-xs">
                      {formatPctRl(verticalPct(line.expenses, rlBase))}
                    </TableCell>
                    <TableCell
                      className={cn(
                        "text-right text-lg font-bold tabular-nums",
                        line.operatingResult >= 0 ? "text-emerald-300" : "text-rose-300"
                      )}
                    >
                      {formatBRL(line.operatingResult)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-slate-400 text-xs">
                      {formatPctRl(verticalPct(line.operatingResult, rlBase))}
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge variant="outline" className={getStatusColor(line.status)}>
                        {line.status}
                      </Badge>
                    </TableCell>
                  </TableRow>
                );
              })
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
  delta,
  compareLabel,
  formatBRL,
  invert,
  emphasize,
}: {
  label: string;
  value: string;
  tone: string;
  delta?: DeltaBlock;
  compareLabel?: string;
  formatBRL?: (v: number) => string;
  invert?: boolean;
  emphasize?: boolean;
}) {
  const bad =
    delta?.deltaPct != null &&
    (invert ? delta.deltaPct > 0 : delta.deltaPct < 0);
  return (
    <div
      className={cn(
        "rounded-lg border bg-slate-950/50 px-3 py-2",
        delta?.anomaly ? "border-amber-500/35" : "border-slate-800",
        emphasize && "border-cyan-500/25 bg-slate-950/80 shadow-[inset_0_0_0_1px_rgba(34,211,238,0.08)]"
      )}
    >
      <p className="text-[10px] uppercase tracking-wider text-slate-300 font-bold">{label}</p>
      <p
        className={cn(
          "font-mono font-bold mt-1 tabular-nums",
          emphasize ? "text-lg leading-tight" : "text-sm",
          tone
        )}
      >
        {value}
      </p>
      {delta && formatBRL ? (
        <p
          className={cn(
            "text-[10px] font-mono mt-1",
            delta.anomaly
              ? bad
                ? "text-rose-300"
                : "text-amber-200"
              : "text-slate-400"
          )}
        >
          {formatDeltaRs(delta.deltaRs, formatBRL)} · {formatDeltaPct(delta.deltaPct)}
          <span className="text-slate-500"> vs {compareLabel}</span>
          {delta.anomaly ? " ⚠️" : ""}
        </p>
      ) : null}
    </div>
  );
}

function CompareRow({
  label,
  delta,
  invert,
  emphasize,
  formatBRL,
  receitaLiquida,
}: {
  label: string;
  delta: DeltaBlock;
  invert?: boolean;
  emphasize?: boolean;
  formatBRL: (v: number) => string;
  receitaLiquida: number;
}) {
  const bad =
    delta.deltaPct != null && (invert ? delta.deltaPct > 0 : delta.deltaPct < 0);
  return (
    <TableRow
      className={cn(
        "border-slate-800",
        delta.anomaly && "bg-amber-500/5",
        emphasize && "bg-white/[0.02]"
      )}
    >
      <TableCell
        className={cn(
          "text-slate-200 font-medium",
          emphasize && "text-white text-base font-bold"
        )}
      >
        {label}
        {delta.anomaly ? (
          <Badge className="ml-2 bg-amber-500/15 text-amber-200 border-amber-500/30 text-[10px]">
            {delta.deltaPct != null && delta.deltaPct > 0
              ? `⚠️ +${Math.abs(delta.deltaPct).toFixed(0)}%`
              : `🔴 ${formatDeltaPct(delta.deltaPct)}`}
          </Badge>
        ) : null}
      </TableCell>
      <TableCell
        className={cn(
          "text-right font-mono text-white tabular-nums",
          emphasize && "text-lg font-bold"
        )}
      >
        {formatBRL(delta.current)}
      </TableCell>
      <TableCell className="text-right font-mono text-cyan-300/90 text-xs">
        {formatPctRl(verticalPct(delta.current, receitaLiquida))}
      </TableCell>
      <TableCell className="text-right font-mono text-slate-300">
        {formatBRL(delta.previous)}
      </TableCell>
      <TableCell
        className={cn(
          "text-right font-mono",
          bad ? "text-rose-300" : "text-emerald-300"
        )}
      >
        {formatDeltaRs(delta.deltaRs, formatBRL)}
      </TableCell>
      <TableCell
        className={cn(
          "text-right font-mono font-semibold",
          bad ? "text-rose-300" : "text-emerald-300"
        )}
      >
        {formatDeltaPct(delta.deltaPct)}
      </TableCell>
    </TableRow>
  );
}
