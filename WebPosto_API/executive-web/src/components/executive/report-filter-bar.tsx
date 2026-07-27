"use client";

import React from "react";
import { Building2, Calendar } from "lucide-react";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { useReportFilter, FILIAIS, PERIOD_OPTIONS } from "@/contexts/report-filter-context";
import { cn } from "@/lib/utils";

interface ReportFilterBarProps {
  className?: string;
}

export function ReportFilterBar({ className }: ReportFilterBarProps) {
  const {
    selectedFilial,
    setSelectedFilial,
    selectedPeriod,
    setSelectedPeriod,
    filialLabel,
    isConsolidated,
  } = useReportFilter();

  const filialOptions = FILIAIS.map((f) => ({
    value: f.empresaCodigo.toString(),
    label: f.nome,
  }));

  const periodOptions = PERIOD_OPTIONS.map((p) => ({
    value: p.value,
    label: p.label,
  }));

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex items-center gap-2 flex-1">
          <Building2 size={16} className="text-slate-400 shrink-0" />
          <Select
            value={selectedFilial.toString()}
            onChange={(val) => setSelectedFilial(Number(val))}
            options={filialOptions}
            placeholder="Selecione a filial"
            className="flex-1 min-w-[240px]"
          />
        </div>

        <div className="flex items-center gap-2">
          <Calendar size={16} className="text-slate-400 shrink-0" />
          <Select
            value={selectedPeriod}
            onChange={(val) => setSelectedPeriod(val as "7d" | "today" | "month")}
            options={periodOptions}
            placeholder="Selecione o período"
            className="min-w-[160px]"
          />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-xs text-slate-500">Visualizando:</span>
        <Badge
          variant="outline"
          className={cn(
            "text-xs",
            isConsolidated
              ? "bg-blue-500/10 text-blue-300 border-blue-500/20"
              : "bg-purple-500/10 text-purple-300 border-purple-500/20"
          )}
        >
          {filialLabel}
        </Badge>
      </div>
    </div>
  );
}
