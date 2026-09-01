"use client";

import React, { createContext, useContext, useMemo, useSyncExternalStore, useCallback } from "react";

export interface Filial {
  empresaCodigo: number;
  nome: string;
  nomeAbreviado: string;
}

export const FILIAIS: Filial[] = [
  { empresaCodigo: 0, nome: "Todas as Filiais (Consolidado Grupo Lisboa)", nomeAbreviado: "Consolidado" },
  { empresaCodigo: 5555, nome: "AP CASA CAIADA", nomeAbreviado: "Casa Caiada" },
  { empresaCodigo: 11495, nome: "POSTO VIP", nomeAbreviado: "VIP" },
  { empresaCodigo: 74014, nome: "POSTO REAL / DOZE", nomeAbreviado: "Real" },
];

export type PeriodOption = "7d" | "today" | "yesterday" | "month" | "custom";

export const PERIOD_OPTIONS: { value: PeriodOption; label: string }[] = [
  { value: "yesterday", label: "Ontem (D-1)" },
  { value: "today", label: "Hoje" },
  { value: "7d", label: "Últimos 7 Dias" },
  { value: "month", label: "Mês Atual" },
  { value: "custom", label: "Personalizado" },
];

const STORAGE_KEY_FILIAL = "logos_selected_filial";
const STORAGE_KEY_PERIOD = "logos_selected_period";
const STORAGE_KEY_CUSTOM_START = "logos_custom_start";
const STORAGE_KEY_CUSTOM_END = "logos_custom_end";

interface GlobalFilterContextType {
  selectedFilial: number;
  setSelectedFilial: (codigo: number) => void;
  selectedPeriod: PeriodOption;
  setSelectedPeriod: (period: PeriodOption) => void;
  customStartDate: string;
  customEndDate: string;
  setCustomDates: (start: string, end: string) => void;
  filialLabel: string;
  filialShortLabel: string;
  periodLabel: string;
  isConsolidated: boolean;
  periodDates: { start: string; end: string };
  getApiParams: () => { empresaCodigo?: number; dataInicial: string; dataFinal: string };
}

const GlobalFilterContext = createContext<GlobalFilterContextType | undefined>(undefined);

/** YYYY-MM-DD em calendário local (evita shift UTC do toISOString). */
function formatDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function getYesterdayISO(): string {
  return formatDate(new Date(Date.now() - 86400000));
}

function getDefaultCustomDates(): { start: string; end: string } {
  const yesterday = getYesterdayISO();
  return { start: yesterday, end: yesterday };
}

function getDateRange(period: PeriodOption, customStart?: string, customEnd?: string): { start: string; end: string } {
  const today = new Date();

  switch (period) {
    case "yesterday": {
      const y = getYesterdayISO();
      return { start: y, end: y };
    }
    case "today":
      return { start: formatDate(today), end: formatDate(today) };
    case "month": {
      const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
      return { start: formatDate(firstDay), end: formatDate(today) };
    }
    case "custom": {
      const defaults = getDefaultCustomDates();
      return { start: customStart || defaults.start, end: customEnd || defaults.end };
    }
    case "7d":
    default: {
      const weekAgo = new Date(today);
      weekAgo.setDate(weekAgo.getDate() - 6);
      return { start: formatDate(weekAgo), end: formatDate(today) };
    }
  }
}

type FilterState = {
  selectedFilial: number;
  selectedPeriod: PeriodOption;
  customStartDate: string;
  customEndDate: string;
};

const defaultCustom = getDefaultCustomDates();
const DEFAULT_STATE: FilterState = { 
  selectedFilial: 0, 
  selectedPeriod: "yesterday",
  customStartDate: defaultCustom.start,
  customEndDate: defaultCustom.end,
};
let listeners: Array<() => void> = [];
let cachedState: FilterState | null = null;

function getSnapshotClient(): FilterState {
  if (cachedState) return cachedState;
  try {
    const filial = localStorage.getItem(STORAGE_KEY_FILIAL);
    const period = localStorage.getItem(STORAGE_KEY_PERIOD);
    const customStart = localStorage.getItem(STORAGE_KEY_CUSTOM_START);
    const customEnd = localStorage.getItem(STORAGE_KEY_CUSTOM_END);
    const defaults = getDefaultCustomDates();
    cachedState = {
      selectedFilial: filial ? JSON.parse(filial) : 0,
      selectedPeriod: period ? (JSON.parse(period) as PeriodOption) : "yesterday",
      customStartDate: customStart || defaults.start,
      customEndDate: customEnd || defaults.end,
    };
    return cachedState;
  } catch {
    return DEFAULT_STATE;
  }
}

function getSnapshotServer(): FilterState {
  return DEFAULT_STATE;
}

function subscribe(listener: () => void): () => void {
  listeners = [...listeners, listener];
  return () => {
    listeners = listeners.filter((l) => l !== listener);
  };
}

function setFilterState(update: Partial<FilterState>): void {
  const current = getSnapshotClient();
  const next = { ...current, ...update };
  cachedState = next;
  try {
    if (update.selectedFilial !== undefined) {
      localStorage.setItem(STORAGE_KEY_FILIAL, JSON.stringify(update.selectedFilial));
    }
    if (update.selectedPeriod !== undefined) {
      localStorage.setItem(STORAGE_KEY_PERIOD, JSON.stringify(update.selectedPeriod));
    }
    if (update.customStartDate !== undefined) {
      localStorage.setItem(STORAGE_KEY_CUSTOM_START, update.customStartDate);
    }
    if (update.customEndDate !== undefined) {
      localStorage.setItem(STORAGE_KEY_CUSTOM_END, update.customEndDate);
    }
  } catch {
    // Ignore storage errors
  }
  listeners.forEach((listener) => listener());
}

export function GlobalFilterProvider({ children }: { children: React.ReactNode }) {
  const state = useSyncExternalStore(subscribe, getSnapshotClient, getSnapshotServer);

  const setSelectedFilial = useCallback((codigo: number) => {
    setFilterState({ selectedFilial: codigo });
  }, []);

  const setSelectedPeriod = useCallback((period: PeriodOption) => {
    setFilterState({ selectedPeriod: period });
  }, []);

  const setCustomDates = useCallback((start: string, end: string) => {
    setFilterState({ customStartDate: start, customEndDate: end, selectedPeriod: "custom" });
  }, []);

  const filialLabel = useMemo(() => {
    const filial = FILIAIS.find((f) => f.empresaCodigo === state.selectedFilial);
    return filial?.nome || "Todas as Filiais";
  }, [state.selectedFilial]);

  const filialShortLabel = useMemo(() => {
    const filial = FILIAIS.find((f) => f.empresaCodigo === state.selectedFilial);
    return filial?.nomeAbreviado || "Consolidado";
  }, [state.selectedFilial]);

  const periodLabel = useMemo(() => {
    if (state.selectedPeriod === "custom") {
      return `${state.customStartDate} a ${state.customEndDate}`;
    }
    const period = PERIOD_OPTIONS.find((p) => p.value === state.selectedPeriod);
    return period?.label || "Ontem (D-1)";
  }, [state.selectedPeriod, state.customStartDate, state.customEndDate]);

  const isConsolidated = state.selectedFilial === 0;

  const periodDates = useMemo(
    () => getDateRange(state.selectedPeriod, state.customStartDate, state.customEndDate),
    [state.selectedPeriod, state.customStartDate, state.customEndDate]
  );

  const getApiParams = useCallback(() => {
    const params: { empresaCodigo?: number; dataInicial: string; dataFinal: string } = {
      dataInicial: periodDates.start,
      dataFinal: periodDates.end,
    };
    if (!isConsolidated) {
      params.empresaCodigo = state.selectedFilial;
    }
    return params;
  }, [periodDates, state.selectedFilial, isConsolidated]);

  const value = useMemo(
    () => ({
      selectedFilial: state.selectedFilial,
      setSelectedFilial,
      selectedPeriod: state.selectedPeriod,
      setSelectedPeriod,
      customStartDate: state.customStartDate,
      customEndDate: state.customEndDate,
      setCustomDates,
      filialLabel,
      filialShortLabel,
      periodLabel,
      isConsolidated,
      periodDates,
      getApiParams,
    }),
    [
      state.selectedFilial,
      state.selectedPeriod,
      state.customStartDate,
      state.customEndDate,
      setSelectedFilial,
      setSelectedPeriod,
      setCustomDates,
      filialLabel,
      filialShortLabel,
      periodLabel,
      isConsolidated,
      periodDates,
      getApiParams,
    ]
  );

  return <GlobalFilterContext.Provider value={value}>{children}</GlobalFilterContext.Provider>;
}

export function useGlobalFilter() {
  const context = useContext(GlobalFilterContext);
  if (context === undefined) {
    throw new Error("useGlobalFilter must be used within a GlobalFilterProvider");
  }
  return context;
}

export { useGlobalFilter as useReportFilter };
