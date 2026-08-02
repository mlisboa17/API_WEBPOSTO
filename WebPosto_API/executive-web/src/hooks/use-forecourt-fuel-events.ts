"use client";

import { useCallback, useEffect, useState } from "react";
import { apiService } from "@/lib/api";
import type { ForecourtFuelEvent } from "@/lib/forecourt-fuel-dots";

const MAX_PERIODO = 400; // rush acumulado — só eventos reais da API

/** Carrega abastecimentos do período + pendentes ao vivo para plotar na planta. */
export function useForecourtFuelEvents(
  stationId: number | undefined,
  start: string,
  end: string,
  enabled = true
) {
  const [events, setEvents] = useState<ForecourtFuelEvent[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!enabled || !stationId) {
      setEvents([]);
      return;
    }
    setLoading(true);
    try {
      const [supply, live] = await Promise.all([
        apiService.getFuelSupply(start, end, stationId),
        apiService.getPistaLive(stationId),
      ]);

      const periodo: ForecourtFuelEvent[] = (supply.abastecimentos || [])
        .filter((a) => !stationId || Number(a.empresa_codigo) === Number(stationId))
        .slice(-MAX_PERIODO)
        .map((a) => ({
          id: `p-${a.id}`,
          bico: Number(a.bico),
          produto: a.produto,
          litros: a.litros,
          valor: a.valor,
          dataHora: `${a.data || ""} ${a.hora || ""}`.trim(),
          status: "BAIXADO",
          fonte: "periodo" as const,
        }));

      const liveEvents: ForecourtFuelEvent[] = [];
      for (const fil of live.filiais || []) {
        if (Number(fil.empresaCodigo) !== Number(stationId)) continue;
        for (const ilha of fil.ilhas || []) {
          for (const bomba of ilha.bombas || []) {
            for (const b of bomba.bicos || []) {
              if (!b.idAbastecimento && !b.valorPendente && !b.litros) continue;
              liveEvents.push({
                id: `l-${b.idAbastecimento || `${b.bico}-${b.dataHoraT1}`}`,
                bico: Number(b.bico),
                bomba: Number(b.bomba),
                produto: b.produto,
                litros: b.litros,
                valor: b.valorPendente || b.valorUltimo,
                frentistaNome: b.frentistaNome,
                dataHora: b.dataHoraT1,
                status: b.status || "PENDENTE",
                fonte: "live",
              });
            }
          }
        }
      }

      // Live sobrescreve duplicata do mesmo idAbastecimento no período
      const byKey = new Map<string, ForecourtFuelEvent>();
      for (const e of periodo) byKey.set(String(e.id), e);
      for (const e of liveEvents) byKey.set(String(e.id), e);
      setEvents([...byKey.values()]);
    } catch {
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }, [enabled, stationId, start, end]);

  useEffect(() => {
    void load();
    if (!enabled) return;
    const id = window.setInterval(() => void load(), 30_000);
    return () => window.clearInterval(id);
  }, [load, enabled]);

  return { events, loading, reload: load };
}
