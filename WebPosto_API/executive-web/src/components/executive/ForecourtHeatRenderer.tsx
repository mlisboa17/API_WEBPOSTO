"use client";

/**
 * Compat: HEATMAP-01 consolidado em ForecourtHeatOverlay.
 * Mantém o nome antigo para imports existentes.
 */

export {
  ForecourtHeatOverlay as ForecourtHeatRenderer,
  heatHoverAt,
  type HeatMode,
  type HeatSource,
  type HeatCellHover,
} from "@/components/executive/ForecourtHeatOverlay";
