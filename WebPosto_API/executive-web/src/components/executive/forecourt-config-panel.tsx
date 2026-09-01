"use client";

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  AlertTriangle,
  Fuel,
  LayoutGrid,
  MapPin,
  RefreshCcw,
  Save,
  Sprout,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { apiService } from "@/lib/api";
import { Forecourt2DCanvas } from "@/components/executive/Forecourt2DCanvas";
import type { ForecourtLayout, ForecourtNozzleLink, ForecourtPosition } from "@/types/api";
import { cn } from "@/lib/utils";

const STATION_OPTIONS = [
  { id: 5555, label: "Casa Caiada" },
  { id: 11495, label: "VIP" },
  { id: 74014, label: "Real / Doze" },
] as const;

type Props = {
  empresaCodigo?: number;
};

function padBico(n: number) {
  return String(n).padStart(3, "0");
}

function summaryFrom(layout: ForecourtLayout | null) {
  if (!layout) {
    return {
      name: "—",
      version: "—",
      status: "—",
      mapping_status: "—",
      mapping_note: "",
      qtd_zonas: 0,
      qtd_ilhas: 0,
      qtd_ilhas_liquidos: 0,
      qtd_equip_gnv: 0,
      qtd_bombas: 0,
      qtd_bombas_liquidos: 0,
      qtd_posicoes: 0,
      qtd_posicoes_liquidos: 0,
      qtd_bicos: 0,
    };
  }
  const base = layout.summary
    ? { ...layout.summary }
    : (() => {
        const pumps = new Set(layout.positions.map((p) => p.pump_id));
        const bicos = new Set(
          layout.positions.flatMap((p) => p.nozzles.map((n) => n.nozzle_id))
        );
        const liq = layout.islands.filter((i) => i.zone_code === "ZONE_LIQUIDOS");
        const gnv = layout.islands.filter((i) => i.zone_code === "ZONE_GNV");
        return {
          qtd_zonas: layout.zones?.length || 0,
          qtd_ilhas: layout.islands.length,
          qtd_ilhas_liquidos: liq.length,
          qtd_equip_gnv: gnv.length,
          qtd_bombas: pumps.size,
          qtd_bombas_liquidos: liq.length,
          qtd_posicoes: layout.positions.length,
          qtd_posicoes_liquidos: layout.positions.filter((p) =>
            liq.some((i) => i.code === p.island_code)
          ).length,
          qtd_bicos: bicos.size,
        };
      })();
  return {
    ...base,
    name: layout.name,
    version: layout.version,
    status: layout.status,
    mapping_status: layout.mapping_status,
    mapping_note: layout.mapping_note || layout.summary?.mapping_note || "",
  };
}

export function ForecourtConfigPanel({ empresaCodigo }: Props) {
  const [stationId, setStationId] = useState<number>(empresaCodigo || 5555);
  const [layout, setLayout] = useState<ForecourtLayout | null>(null);
  const [draftPositions, setDraftPositions] = useState<ForecourtPosition[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  useEffect(() => {
    if (empresaCodigo) setStationId(empresaCodigo);
  }, [empresaCodigo]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setInfo(null);
    try {
      const active = await apiService.getForecourtActiveLayout(stationId);
      setLayout(active);
      setDraftPositions(active?.positions ? structuredClone(active.positions) : []);
      if (!active) setInfo("Nenhum layout ACTIVE para este posto.");
    } catch (err) {
      setLayout(null);
      setDraftPositions([]);
      setError(err instanceof Error ? err.message : "Falha ao carregar layout");
    } finally {
      setLoading(false);
    }
  }, [stationId]);

  useEffect(() => {
    void load();
  }, [load]);

  const summary = useMemo(() => summaryFrom(layout), [layout]);
  const provisional = (layout?.mapping_status || "").toUpperCase() === "PROVISIONAL";
  const dirty = useMemo(
    () => JSON.stringify(draftPositions) !== JSON.stringify(layout?.positions || []),
    [draftPositions, layout?.positions]
  );

  const moveNozzle = (nozzleId: number, toPositionCode: string) => {
    setDraftPositions((prev) => {
      const next = structuredClone(prev);
      let moved: ForecourtNozzleLink | null = null;
      for (const p of next) {
        const idx = p.nozzles.findIndex((n) => n.nozzle_id === nozzleId);
        if (idx >= 0) {
          moved = { ...p.nozzles[idx], active: p.nozzles[idx].active ?? true };
          p.nozzles.splice(idx, 1);
          break;
        }
      }
      if (!moved) return prev;
      const target = next.find((p) => p.code === toPositionCode);
      if (!target) return prev;
      if (!target.nozzles.some((n) => n.nozzle_id === nozzleId)) {
        target.nozzles.push(moved);
      }
      return next;
    });
  };

  const save = async () => {
    if (!layout?.id) return;
    setSaving(true);
    setError(null);
    setInfo(null);
    try {
      const updated = await apiService.updateForecourtLayout(layout.id, {
        positions: draftPositions,
      });
      setLayout(updated);
      setDraftPositions(structuredClone(updated.positions));
      setInfo("Layout salvo — alteração apenas de dados (sem mudança de código).");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao salvar");
    } finally {
      setSaving(false);
    }
  };

  const seedCasa = async () => {
    setSeeding(true);
    setError(null);
    setInfo(null);
    try {
      const seeded = await apiService.seedForecourtCasaCaiada(false);
      setStationId(5555);
      setLayout(seeded);
      setDraftPositions(structuredClone(seeded.positions));
      setInfo(
        seeded.seeded
          ? `Piloto ${seeded.seed_id || "Casa Caiada V1"} criado e ativado.`
          : `Piloto já existente reutilizado (${seeded.id}).`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha no seed");
    } finally {
      setSeeding(false);
    }
  };

  const seedReal = async (force = false) => {
    setSeeding(true);
    setError(null);
    setInfo(null);
    try {
      const seeded = await apiService.seedForecourtPostoReal(force);
      setStationId(74014);
      setLayout(seeded);
      setDraftPositions(structuredClone(seeded.positions || []));
      setInfo(
        seeded.seeded
          ? `Piloto ${seeded.seed_id || "Posto Real V1"} criado e ativado.`
          : `Piloto Real reutilizado (${seeded.id}). Use force se a geometria T estiver desatualizada.`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha no seed Real");
    } finally {
      setSeeding(false);
    }
  };

  const mappingNote =
    (layout?.mapping_note || summary.mapping_note || "").trim() ||
    "Associação física pendente de validação";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
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
          <Button size="sm" variant="outline" className="border-slate-600" onClick={() => void load()}>
            <RefreshCcw size={14} className={cn("mr-1.5", loading && "animate-spin")} />
            Atualizar
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="border-amber-600/50 text-amber-200"
            disabled={seeding}
            onClick={() => void seedCasa()}
          >
            <Sprout size={14} className="mr-1.5" />
            Seed Casa Caiada
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="border-emerald-600/50 text-emerald-200"
            disabled={seeding}
            onClick={() => void seedReal(false)}
          >
            <Sprout size={14} className="mr-1.5" />
            Seed Posto Real
          </Button>
        </div>
        <Button
          size="sm"
          disabled={!dirty || saving || !layout}
          onClick={() => void save()}
          className="bg-sky-600 hover:bg-sky-500"
        >
          <Save size={14} className="mr-1.5" />
          {saving ? "Salvando…" : "Salvar vínculos"}
        </Button>
      </div>

      {provisional && (
        <div className="rounded-md border border-amber-500/50 bg-amber-500/10 px-4 py-3 flex items-start gap-2">
          <AlertTriangle className="text-amber-300 shrink-0 mt-0.5" size={18} />
          <div>
            <Badge className="bg-amber-500/20 text-amber-200 border-amber-500/40 mb-1">
              MAPEAMENTO PROVISÓRIO
            </Badge>
            <p className="text-sm text-amber-100/90 leading-snug">{mappingNote}</p>
          </div>
        </div>
      )}

      {error && (
        <Card className="border-red-500/30 bg-red-500/5 p-4 text-red-300 text-sm">{error}</Card>
      )}
      {info && (
        <Card className="border-sky-500/30 bg-sky-500/5 p-3 text-sky-200 text-sm">{info}</Card>
      )}

      {loading && !layout ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-20 bg-slate-900" />
          ))}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
            <Kpi label="Layout" value={String(summary.name)} icon={<LayoutGrid size={14} />} />
            <Kpi label="Status" value={String(summary.status)} />
            <Kpi
              label="Mapping"
              value={String(summary.mapping_status)}
              tone={provisional ? "amber" : "emerald"}
            />
            <Kpi label="Zonas" value={String(summary.qtd_zonas ?? layout?.zones?.length ?? 0)} />
            <Kpi
              label="Ilhas líquidos"
              value={String(
                summary.qtd_ilhas_liquidos ??
                  layout?.islands.filter((i) => i.zone_code === "ZONE_LIQUIDOS").length ??
                  0
              )}
            />
            <Kpi
              label="Bombas líquidos"
              value={String(summary.qtd_bombas_liquidos ?? summary.qtd_bombas)}
              icon={<Fuel size={14} />}
            />
            <Kpi
              label="Posições líquidos"
              value={String(summary.qtd_posicoes_liquidos ?? summary.qtd_posicoes)}
              icon={<MapPin size={14} />}
            />
            <Kpi
              label="Equip. GNV"
              value={String(
                summary.qtd_equip_gnv ??
                  layout?.islands.filter((i) => i.zone_code === "ZONE_GNV").length ??
                  0
              )}
            />
            <Kpi label="Bicos" value={String(summary.qtd_bicos)} />
            <Kpi label="Versão" value={`v${summary.version}`} />
          </div>

          {layout && (
            <div className="space-y-4">
              <Card className="border-slate-800 bg-slate-950/50">
                <CardHeader className="py-3 px-4">
                  <CardTitle className="text-sm text-slate-200">
                    Planta operacional 2D
                  </CardTitle>
                </CardHeader>
                <CardContent className="px-4 pb-4">
                  <Forecourt2DCanvas
                    layout={{ ...layout, positions: draftPositions }}
                  />
                </CardContent>
              </Card>

              <Card className="border-slate-800 bg-slate-950/50">
                <CardHeader className="py-3 px-4">
                  <CardTitle className="text-sm text-slate-200">
                    Ilhas · Posições · Bicos
                  </CardTitle>
                </CardHeader>
                <CardContent className="px-4 pb-4 space-y-4 max-h-[420px] overflow-auto">
                  {layout.islands.map((isl) => (
                    <div key={isl.code} className="space-y-2">
                      <p className="text-xs uppercase tracking-wide text-slate-500">
                        {isl.code} · x={isl.x} y={isl.y}
                      </p>
                      {draftPositions
                        .filter((p) => p.island_code === isl.code)
                        .map((pos) => (
                          <div
                            key={pos.code}
                            className="rounded-md border border-slate-800 bg-slate-900/60 p-3 space-y-2"
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div>
                                <p className="text-sm text-slate-100 font-medium">{pos.code}</p>
                                <p className="text-xs text-slate-500">
                                  {pos.pump_name || `Bomba ${pos.pump_id}`} · {pos.orientation} · (
                                  {pos.x}, {pos.y})
                                </p>
                              </div>
                              <Badge
                                variant="outline"
                                className={
                                  pos.orientation === "AVENIDA"
                                    ? "border-sky-500/40 text-sky-300"
                                    : "border-violet-500/40 text-violet-300"
                                }
                              >
                                {pos.orientation}
                              </Badge>
                            </div>
                            <div className="flex flex-wrap gap-2">
                              {pos.nozzles.map((n) => (
                                <div
                                  key={n.nozzle_id}
                                  className="flex items-center gap-1 rounded border border-slate-700 bg-slate-950 px-2 py-1"
                                >
                                  <span className="text-xs text-slate-200 font-mono">
                                    {padBico(n.nozzle_id)}
                                    {n.label ? ` · ${n.label.replace(/^\d+\s*/, "")}` : ""}
                                  </span>
                                  {draftPositions
                                    .filter((p) => p.code !== pos.code && p.pump_id === pos.pump_id)
                                    .map((alt) => (
                                      <button
                                        key={alt.code}
                                        type="button"
                                        className="text-[10px] text-amber-300 hover:underline ml-1"
                                        title={`Mover para ${alt.code}`}
                                        onClick={() => moveNozzle(n.nozzle_id, alt.code)}
                                      >
                                        → {alt.orientation.slice(0, 3)}
                                      </button>
                                    ))}
                                </div>
                              ))}
                              {pos.nozzles.length === 0 && (
                                <span className="text-xs text-slate-600">Sem bicos</span>
                              )}
                            </div>
                          </div>
                        ))}
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Kpi({
  label,
  value,
  icon,
  tone,
}: {
  label: string;
  value: string;
  icon?: ReactNode;
  tone?: "amber" | "emerald";
}) {
  return (
    <Card className="border-slate-800 bg-slate-950/50">
      <CardContent className="p-3">
        <p className="text-[11px] uppercase tracking-wide text-slate-500 flex items-center gap-1">
          {icon}
          {label}
        </p>
        <p
          className={cn(
            "text-lg font-semibold mt-1 truncate",
            tone === "amber" && "text-amber-300",
            tone === "emerald" && "text-emerald-300",
            !tone && "text-slate-100"
          )}
        >
          {value}
        </p>
      </CardContent>
    </Card>
  );
}
