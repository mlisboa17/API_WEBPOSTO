"use client";

import React, { createContext, useContext, useState, useMemo } from "react";

export interface Filial {
  empresaCodigo: number;
  nome: string;
}

export const FILIAIS: Filial[] = [
  { empresaCodigo: 0, nome: "Todas as Filiais (Consolidado Grupo Lisboa)" },
  { empresaCodigo: 5555, nome: "AP Casa Caiada" },
  { empresaCodigo: 6666, nome: "Posto VIP" },
  { empresaCodigo: 7777, nome: "Posto Real / Doze" },
];

export type PeriodOption = "7d" | "today" | "month";

export const PERIOD_OPTIONS: { value: PeriodOption; label: string }[] = [
  { value: "7d", label: "Últimos 7 Dias" },
  { value: "today", label: "Hoje" },
  { value: "month", label: "Mês Atual" },
];

interface ReportFilterContextType {
  selectedFilial: number;
  setSelectedFilial: (codigo: number) => void;
  selectedPeriod: PeriodOption;
  setSelectedPeriod: (period: PeriodOption) => void;
  filialLabel: string;
  periodLabel: string;
  isConsolidated: boolean;
  periodDates: { start: string; end: string };
}

const ReportFilterContext = createContext<ReportFilterContextType | undefined>(undefined);

function getDateRange(period: PeriodOption): { start: string; end: string } {
  const today = new Date();
  const formatDate = (d: Date) => d.toISOString().split("T")[0];

  switch (period) {
    case "today":
      return { start: formatDate(today), end: formatDate(today) };
    case "month": {
      const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
      return { start: formatDate(firstDay), end: formatDate(today) };
    }
    case "7d":
    default: {
      const weekAgo = new Date(today);
      weekAgo.setDate(weekAgo.getDate() - 6);
      return { start: formatDate(weekAgo), end: formatDate(today) };
    }
  }
}

export function ReportFilterProvider({ children }: { children: React.ReactNode }) {
  const [selectedFilial, setSelectedFilial] = useState<number>(0);
  const [selectedPeriod, setSelectedPeriod] = useState<PeriodOption>("7d");

  const filialLabel = useMemo(() => {
    const filial = FILIAIS.find((f) => f.empresaCodigo === selectedFilial);
    return filial?.nome || "Todas as Filiais";
  }, [selectedFilial]);

  const periodLabel = useMemo(() => {
    const period = PERIOD_OPTIONS.find((p) => p.value === selectedPeriod);
    return period?.label || "Últimos 7 Dias";
  }, [selectedPeriod]);

  const isConsolidated = selectedFilial === 0;

  const periodDates = useMemo(() => getDateRange(selectedPeriod), [selectedPeriod]);

  const value = useMemo(
    () => ({
      selectedFilial,
      setSelectedFilial,
      selectedPeriod,
      setSelectedPeriod,
      filialLabel,
      periodLabel,
      isConsolidated,
      periodDates,
    }),
    [selectedFilial, selectedPeriod, filialLabel, periodLabel, isConsolidated, periodDates]
  );

  return (
    <ReportFilterContext.Provider value={value}>
      {children}
    </ReportFilterContext.Provider>
  );
}

export function useReportFilter() {
  const context = useContext(ReportFilterContext);
  if (context === undefined) {
    throw new Error("useReportFilter must be used within a ReportFilterProvider");
  }
  return context;
}
