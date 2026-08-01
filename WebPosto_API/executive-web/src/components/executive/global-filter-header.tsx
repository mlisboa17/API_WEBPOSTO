"use client";

import React, { useState } from "react";
import { Building2, Calendar, MapPin, CalendarRange } from "lucide-react";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useGlobalFilter, FILIAIS, PERIOD_OPTIONS, PeriodOption } from "@/contexts/global-filter-context";
import { cn } from "@/lib/utils";

interface GlobalFilterHeaderProps {
  className?: string;
  showTitle?: boolean;
  title?: string;
  subtitle?: string;
}

export function GlobalFilterHeader({
  className,
  showTitle = false,
  title,
  subtitle,
}: GlobalFilterHeaderProps) {
  const {
    selectedFilial,
    setSelectedFilial,
    selectedPeriod,
    setSelectedPeriod,
    customStartDate,
    customEndDate,
    setCustomDates,
    filialLabel,
    periodLabel,
    isConsolidated,
  } = useGlobalFilter();

  const [tempStart, setTempStart] = useState(customStartDate);
  const [tempEnd, setTempEnd] = useState(customEndDate);

  const filialOptions = FILIAIS.map((f) => ({
    value: f.empresaCodigo.toString(),
    label: f.nome,
  }));

  const periodOptions = PERIOD_OPTIONS.map((p) => ({
    value: p.value,
    label: p.label,
  }));

  const handlePeriodChange = (val: string) => {
    setSelectedPeriod(val as PeriodOption);
  };

  const handleApplyCustomDates = () => {
    if (tempStart && tempEnd) {
      setCustomDates(tempStart, tempEnd);
    }
  };

  return (
    <div className={cn("space-y-4", className)}>
      {showTitle && title && (
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">{title}</h1>
          {subtitle && <p className="text-slate-400 text-sm">{subtitle}</p>}
        </div>
      )}

      <div className="flex flex-col gap-3 p-3 rounded-lg bg-slate-900/50 border border-white/5">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <div className="grid size-8 place-items-center rounded-md bg-blue-500/10 shrink-0">
              <Building2 size={16} className="text-blue-400" />
            </div>
            <Select
              value={selectedFilial.toString()}
              onChange={(val) => setSelectedFilial(Number(val))}
              options={filialOptions}
              placeholder="Selecione a filial"
              className="flex-1 min-w-[200px]"
            />
          </div>

          <div className="flex items-center gap-2">
            <div className="grid size-8 place-items-center rounded-md bg-amber-500/10 shrink-0">
              <Calendar size={16} className="text-amber-400" />
            </div>
            <Select
              value={selectedPeriod}
              onChange={handlePeriodChange}
              options={periodOptions}
              placeholder="Selecione o período"
              className="min-w-[160px]"
            />
          </div>

          <div className="flex items-center gap-2 sm:ml-auto">
            <MapPin size={14} className="text-slate-500" />
            <span className="text-xs text-slate-500">Exibindo:</span>
            <Badge
              variant="outline"
              className={cn(
                "text-xs font-medium",
                isConsolidated
                  ? "bg-blue-500/10 text-blue-300 border-blue-500/20"
                  : "bg-purple-500/10 text-purple-300 border-purple-500/20"
              )}
            >
              {filialLabel}
            </Badge>
            <Badge variant="outline" className="text-xs bg-slate-800 text-slate-300 border-white/10">
              {periodLabel}
            </Badge>
          </div>
        </div>

        {selectedPeriod === "custom" && (
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 pt-3 border-t border-white/5">
            <div className="flex items-center gap-2">
              <CalendarRange size={14} className="text-slate-500" />
              <span className="text-xs text-slate-400">Intervalo:</span>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={tempStart}
                onChange={(e) => setTempStart(e.target.value)}
                className="px-2 py-1.5 text-sm rounded-md bg-slate-800 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              />
              <span className="text-slate-500">até</span>
              <input
                type="date"
                value={tempEnd}
                onChange={(e) => setTempEnd(e.target.value)}
                className="px-2 py-1.5 text-sm rounded-md bg-slate-800 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              />
              <Button size="sm" onClick={handleApplyCustomDates} className="ml-2">
                Aplicar
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function CompactFilterBar({ className }: { className?: string }) {
  const {
    selectedFilial,
    setSelectedFilial,
    selectedPeriod,
    setSelectedPeriod,
    filialShortLabel,
    isConsolidated,
  } = useGlobalFilter();

  const filialOptions = FILIAIS.map((f) => ({
    value: f.empresaCodigo.toString(),
    label: f.nomeAbreviado,
  }));

  const periodOptions = PERIOD_OPTIONS.map((p) => ({
    value: p.value,
    label: p.label,
  }));

  return (
    <div className={cn("flex items-center gap-2 flex-wrap", className)}>
      <Select
        value={selectedFilial.toString()}
        onChange={(val) => setSelectedFilial(Number(val))}
        options={filialOptions}
        className="w-[140px]"
      />
      <Select
        value={selectedPeriod}
        onChange={(val) => setSelectedPeriod(val as PeriodOption)}
        options={periodOptions}
        className="w-[140px]"
      />
      <Badge
        variant="outline"
        className={cn(
          "text-xs",
          isConsolidated
            ? "bg-blue-500/10 text-blue-300 border-blue-500/20"
            : "bg-purple-500/10 text-purple-300 border-purple-500/20"
        )}
      >
        {filialShortLabel}
      </Badge>
    </div>
  );
}
