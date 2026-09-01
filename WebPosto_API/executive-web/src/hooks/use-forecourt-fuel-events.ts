"use client";

import { useCallback, useEffect, useState } from "react";
import { apiService } from "@/lib/api";
import type { ForecourtFuelEvent } from "@/lib/forecourt-fuel-dots";

const MAX_PERIODO = 400;

/** Carrega abastecimentos + T_bico (intelligence) para o heatmap. */
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
      const [supply, liveFeed, pistaLive, intel] = await Promise.all([
        apiService.getFuelSupply(start, end, stationId),
        apiService.getLiveFeed(stationId, "faturamento", 60),
        apiService.getPistaLive(stationId),
        apiService.getPistaIntelligence(stationId),
      ]);

      /** Mapa bico → T_bico médio (frentista no último atendimento). */
      const tByBico = new Map<number, number>();
      for (const f of intel.frentistas || []) {
        const bico = Number(f.ultimo_bico || 0);
        const t = Number(f.t_bico_media_min || 0);
        if (bico > 0 && t > 0) {
          const prev = tByBico.get(bico);
          tByBico.set(bico, prev == null ? t : Math.max(prev, t));
        }
      }
      // Fallback: média do posto em todos os bicos com eventos se não houver por frentista
      const postoT = Number(intel.tbico?.media_min || 0);

      const periodo: ForecourtFuelEvent[] = (supply.abastecimentos || [])
        .filter((a) => !stationId || Number(a.empresa_codigo) === Number(stationId))
        .slice(-MAX_PERIODO)
        .map((a) => {
          const bico = Number(a.bico);
          return {
            id: `p-${a.id}`,
            bico,
            produto: a.produto,
            litros: a.litros,
            valor: a.valor,
            dataHora: `${a.data || ""} ${a.hora || ""}`.trim(),
            status: "BAIXADO",
            fonte: "periodo" as const,
            tBicoMin: tByBico.get(bico) ?? (postoT > 0 ? postoT : undefined),
          };
        });

      const feedEvents: ForecourtFuelEvent[] = (liveFeed.stream || [])
        .filter((s) => !stationId || Number(s.empresa_codigo) === Number(stationId))
        .map((s) => {
          const bico = Number(s.bico);
          return {
            id: `f-${s.id}`,
            bico,
            produto: s.produto,
            litros: s.litros,
            valor: s.valor,
            frentistaNome: s.frentista_nome,
            dataHora: s.data_hora || s.hora,
            status: s.status || "PAGO",
            fonte: "live" as const,
            tBicoMin: tByBico.get(bico) ?? (postoT > 0 ? postoT : undefined),
          };
        });

      const liveEvents: ForecourtFuelEvent[] = [];
      for (const fil of pistaLive.filiais || []) {
        if (Number(fil.empresaCodigo) !== Number(stationId)) continue;
        for (const ilha of fil.ilhas || []) {
          for (const bomba of ilha.bombas || []) {
            for (const b of bomba.bicos || []) {
              if (!b.idAbastecimento && !b.valorPendente && !b.litros) continue;
              const bico = Number(b.bico);
              const ret = Number(b.tempoRetencaoMinutos || 0);
              liveEvents.push({
                id: `l-${b.idAbastecimento || `${b.bico}-${b.dataHoraT1}`}`,
                bico,
                bomba: Number(b.bomba),
                produto: b.produto,
                litros: b.litros,
                valor: b.valorPendente || b.valorUltimo,
                frentistaNome: b.frentistaNome,
                dataHora: b.dataHoraT1,
                status: b.status || "PENDENTE",
                fonte: "live",
                retencaoMin: ret > 0 ? ret : undefined,
                tBicoMin: tByBico.get(bico) ?? (postoT > 0 ? postoT : undefined),
              });
            }
          }
        }
      }

      // Seeds virtuais nos últimos bicos da intelligence (garante mancha mesmo sem stream)
      const intelSeeds: ForecourtFuelEvent[] = [];
      for (const f of intel.frentistas || []) {
        const bico = Number(f.ultimo_bico || 0);
        if (bico <= 0) continue;
        intelSeeds.push({
          id: `i-${f.frentista_id ?? f.nome_frentista}-${bico}`,
          bico,
          litros: 35,
          frentistaNome: f.nome_frentista,
          dataHora: f.ultimo_data_hora || new Date().toISOString(),
          status: "PAGO",
          fonte: "intelligence",
          tBicoMin: Number(f.t_bico_media_min || postoT || 0) || undefined,
        });
      }

      const byKey = new Map<string, ForecourtFuelEvent>();
      for (const e of periodo) byKey.set(`bico:${e.bico}:${e.dataHora}`, e);
      for (const e of feedEvents) byKey.set(`bico:${e.bico}:${e.dataHora}`, e);
      for (const e of liveEvents) byKey.set(`bico:${e.bico}:${e.dataHora}`, e);
      for (const e of intelSeeds) {
        const k = `intel:${e.bico}`;
        if (!byKey.has(k)) byKey.set(k, e);
      }
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
    const id = window.setInterval(() => void load(), 15_000);
    return () => window.clearInterval(id);
  }, [load, enabled]);

  return { events, loading, reload: load };
}
