"use client";

import { useCallback, useEffect, useState } from "react";

import { FuelPanel } from "@/components/fuel-panel";
import { KpiCards } from "@/components/kpi-cards";
import { PostoBanner } from "@/components/posto-banner";
import { Button } from "@/components/ui/button";
import { fetchMetrics } from "@/lib/api";
import type { AdelaideMetrics, Periodo } from "@/types/metrics";
import { RefreshCwIcon } from "lucide-react";
import { RecifeClock } from "@/components/recife-clock";
import { cn } from "@/lib/utils";

const PERIODOS: { id: Periodo; label: string }[] = [
  { id: "hoje", label: "Hoje" },
  { id: "7d", label: "7 dias" },
  { id: "mensal", label: "Mensal" },
];

export function DashboardLive() {
  const [periodo, setPeriodo] = useState<Periodo>("hoje");
  const [data, setData] = useState<AdelaideMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const metrics = await fetchMetrics(periodo);
      setData(metrics);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao carregar métricas");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [periodo]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="@container/main flex flex-1 flex-col gap-4 py-4 md:gap-6 md:py-6">
      <PostoBanner data={data} loading={loading} />

      <p className="px-4 text-xs text-muted-foreground lg:px-6">
        Fuso <strong>America/Recife</strong> · <RecifeClock />
      </p>

      <div className="flex flex-wrap items-center gap-2 px-4 lg:px-6">
        <span className="text-sm font-medium text-muted-foreground">Período:</span>
        {PERIODOS.map((p) => (
          <Button
            key={p.id}
            size="sm"
            variant="ghost"
            className={cn(
              "rounded-full px-4",
              periodo === p.id ? "omie-tab-active" : "omie-tab",
            )}
            onClick={() => setPeriodo(p.id)}
          >
            {p.label}
          </Button>
        ))}
        <Button size="sm" variant="outline" onClick={load} disabled={loading}>
          <RefreshCwIcon className={loading ? "animate-spin" : ""} />
          Atualizar
        </Button>
        {error && <p className="text-sm text-destructive">{error}</p>}
      </div>

      <KpiCards data={data} loading={loading} />
      <FuelPanel data={data} loading={loading} />
    </div>
  );
}
