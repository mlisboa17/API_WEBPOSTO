"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCcw, Sprout } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Forecourt2DCanvas } from "@/components/executive/Forecourt2DCanvas";
import { useGlobalFilter } from "@/contexts/global-filter-context";
import { useForecourtFuelEvents } from "@/hooks/use-forecourt-fuel-events";
import { apiService } from "@/lib/api";
import type { ForecourtLayout } from "@/types/api";
import { cn } from "@/lib/utils";

/** Casa Caiada = 5555 (piloto FORECOURT-CONFIG). 74014 = Real/Doze. */
const STATION_OPTIONS = [
  { id: 5555, label: "Casa Caiada" },
  { id: 11495, label: "VIP" },
  { id: 74014, label: "Real / Doze" },
] as const;

type Props = {
  empresaCodigo?: number;
};

export function ForecourtPlantPanel({ empresaCodigo }: Props) {
  const { periodDates } = useGlobalFilter();
  const [stationId, setStationId] = useState<number>(empresaCodigo || 5555);
  const [layout, setLayout] = useState<ForecourtLayout | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { events: fuelEvents, reload: reloadFuel } = useForecourtFuelEvents(
    stationId,
    periodDates.start,
    periodDates.end,
    true
  );

  useEffect(() => {
    if (empresaCodigo) setStationId(empresaCodigo);
  }, [empresaCodigo]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const active = await apiService.getForecourtActiveLayout(stationId);
      setLayout(active);
      if (!active) {
        setError(
          "Nenhum layout ACTIVE para este posto. Use Seed Casa Caiada (posto 5555) ou configure na aba Configuração da Pista."
        );
      }
      void reloadFuel();
    } catch (err) {
      setLayout(null);
      setError(err instanceof Error ? err.message : "Falha ao carregar planta");
    } finally {
      setLoading(false);
    }
  }, [stationId, reloadFuel]);

  useEffect(() => {
    void load();
  }, [load]);

  const seedCasa = async () => {
    setLoading(true);
    setError(null);
    try {
      const seeded = await apiService.seedForecourtCasaCaiada(false);
      setStationId(5555);
      setLayout(seeded);
      void reloadFuel();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha no seed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <label className="text-xs text-slate-500">Posto</label>
        <select
          className="bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded-md px-2 py-1.5"
          value={stationId}
          onChange={(e) => setStationId(Number(e.target.value))}
        >
          {STATION_OPTIONS.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label} ({s.id})
            </option>
          ))}
        </select>
        <Button
          size="sm"
          variant="outline"
          className="border-slate-600"
          onClick={() => void load()}
        >
          <RefreshCcw size={14} className={cn("mr-1.5", loading && "animate-spin")} />
          Atualizar
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="border-amber-600/50 text-amber-200"
          onClick={() => void seedCasa()}
        >
          <Sprout size={14} className="mr-1.5" />
          Seed Casa Caiada
        </Button>
      </div>

      {loading && !layout ? (
        <Skeleton className="h-[420px] bg-slate-900" />
      ) : error && !layout ? (
        <Card className="border-amber-500/30 bg-amber-500/5 p-6 text-amber-100 text-sm">
          {error}
        </Card>
      ) : layout ? (
        <Forecourt2DCanvas layout={layout} fuelEvents={fuelEvents} />
      ) : null}
    </div>
  );
}
