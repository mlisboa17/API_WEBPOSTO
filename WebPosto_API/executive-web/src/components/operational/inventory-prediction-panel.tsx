"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { InfoTooltip } from "@/components/ui/info-tooltip";
import { apiService } from "@/lib/api";
import { TankPrediction, InventoryPredictionResponse } from "@/types/api";
import {
  AlertTriangle,
  ShoppingCart,
  Clock,
  RefreshCcw,
  Package,
  TrendingDown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { empresaNomeOperacional } from "@/utils/filial_normalizer";
import { TankMonitorCard, isGnvProduct } from "@/components/operational/tank-monitor-card";

interface InventoryPredictionPanelProps {
  empresaCodigo: number;
  empresaNome?: string;
}

const COVERAGE_OPTIONS = [
  { value: "1", label: "1 Dia" },
  { value: "2", label: "2 Dias" },
  { value: "3", label: "3 Dias" },
  { value: "5", label: "5 Dias" },
  { value: "7", label: "7 Dias" },
  { value: "10", label: "10 Dias" },
];

function formatNumber(value: number, decimals: number = 0): string {
  return value.toLocaleString("pt-BR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function normalizePrediction(p: TankPrediction): TankPrediction {
  const gnv =
    isGnvProduct(p.produto_nome) ||
    isGnvProduct(p.tipo_combustivel) ||
    String(p.produto_codigo) === "99" ||
    String(p.produto_codigo) === "099";
  if (!gnv) return p;
  return {
    ...p,
    status_alerta: "OK",
    alerta_label: "GNV canalizado — sem carreta",
    sugestao_compra_litros: 0,
    observacoes: [
      ...(p.observacoes || []),
      "GNV excluído de alerta Pedir Carreta / sugestão em litros",
    ],
  };
}

function TankPredictionCard({
  prediction,
  empresaCodigo,
}: {
  prediction: TankPrediction;
  empresaCodigo: number;
}) {
  const gnv =
    isGnvProduct(prediction.produto_nome) ||
    isGnvProduct(prediction.tipo_combustivel);
  const title = `Tanque — ${prediction.produto_nome || prediction.tipo_combustivel}`;

  return (
    <TankMonitorCard
      title={title}
      fuelLabel={prediction.tipo_combustivel}
      currentLiters={prediction.estoque_atual_litros}
      capacityLiters={prediction.capacidade_tanque}
      autonomiaDias={prediction.autonomia_dias_restantes}
      consumoMedioDiario={prediction.consumo_medio_diario}
      alertLevel={prediction.status_alerta}
      alertLabel={prediction.alerta_label}
      isGnv={gnv}
      tankId={prediction.produto_codigo}
      empresaCodigo={empresaCodigo}
      sugestaoCompraLitros={prediction.sugestao_compra_litros}
      diasCobertura={prediction.dias_cobertura_desejado || 3}
      measuredAt={prediction.data_hora_medidor}
      footer={
        !gnv && prediction.sugestao_compra_litros > 0 ? (
          <div className="rounded-lg border border-cyan-500/30 bg-cyan-500/10 p-3">
            <div className="flex items-center gap-2 mb-1">
              <ShoppingCart size={14} className="text-cyan-400 shrink-0" />
              <span className="text-xs font-medium text-cyan-300">
                Sugestão de Compra
              </span>
            </div>
            <p className="text-xl font-bold font-mono text-cyan-300 leading-none">
              {formatNumber(prediction.sugestao_compra_litros)} L
            </p>
            <p className="text-xs text-cyan-400/80 mt-1">
              Para {prediction.dias_cobertura_desejado} dias de cobertura
            </p>
          </div>
        ) : gnv ? (
          <p className="text-[11px] text-sky-300/90 leading-relaxed">
            Combustível gasoso canalizado — monitoramento por vazão/pressão, sem
            ruptura de carreta em litros.
          </p>
        ) : null
      }
    />
  );
}

export function InventoryPredictionPanel({
  empresaCodigo,
  empresaNome,
}: InventoryPredictionPanelProps) {
  const [diasCobertura, setDiasCobertura] = useState<string>("3");
  const [leadTimeHoras] = useState<number>(24);
  const [data, setData] = useState<InventoryPredictionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const filialNome =
    empresaNome && !/^filial\s*\d+/i.test(empresaNome)
      ? empresaNome
      : empresaNomeOperacional(empresaCodigo);

  const fetchPrediction = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiService.getInventoryPrediction(
        empresaCodigo,
        parseInt(diasCobertura),
        leadTimeHoras
      );
      setData(result);
      if (!result.success) {
        setError(result.observacoes.join("; ") || "Erro ao buscar previsão");
      }
    } catch {
      setError("Erro ao conectar com o servidor");
    } finally {
      setLoading(false);
    }
  }, [empresaCodigo, diasCobertura, leadTimeHoras]);

  useEffect(() => {
    void fetchPrediction();
  }, [fetchPrediction]);

  const predicoes = useMemo(
    () => (data?.predicoes || []).map(normalizePrediction),
    [data?.predicoes]
  );

  const liquidPredictions = useMemo(
    () =>
      predicoes.filter(
        (p) =>
          !isGnvProduct(p.produto_nome) && !isGnvProduct(p.tipo_combustivel)
      ),
    [predicoes]
  );
  const gnvPredictions = useMemo(
    () =>
      predicoes.filter(
        (p) =>
          isGnvProduct(p.produto_nome) || isGnvProduct(p.tipo_combustivel)
      ),
    [predicoes]
  );

  const urgentCount = liquidPredictions.filter(
    (p) => p.status_alerta === "COMPRA_URGENTE"
  ).length;
  const alertCount = liquidPredictions.filter(
    (p) => p.status_alerta === "ATENCAO" || p.status_alerta === "COMPRA_URGENTE"
  ).length;
  const totalSugestao = liquidPredictions.reduce(
    (s, p) => s + (p.sugestao_compra_litros || 0),
    0
  );

  if (loading) {
    return (
      <Card className="border-slate-800 bg-slate-900/90">
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <Skeleton className="h-6 w-56 bg-slate-800" />
            <Skeleton className="h-9 w-28 bg-slate-800" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-72 bg-slate-800" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error && !data) {
    return (
      <Card className="border-slate-800 bg-slate-900/90">
        <CardContent className="py-8 text-center space-y-3">
          <AlertTriangle className="mx-auto h-10 w-10 text-amber-500" />
          <p className="text-slate-300">{error}</p>
          <Button
            onClick={() => void fetchPrediction()}
            className="bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20"
          >
            Tentar Novamente
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-slate-800 bg-slate-900/90">
      <CardHeader className="pb-4 space-y-3">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div className="space-y-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <Package className="h-5 w-5 text-cyan-400 shrink-0" />
              <CardTitle className="text-lg text-white leading-snug">
                Previsão de Estoque & Sugestão de Compras
              </CardTitle>
              <InfoTooltip content="Cálculo preditivo de run-out com base no consumo médio histórico. GNV canalizado não gera alerta de carreta." />
            </div>
            <p className="text-sm font-semibold text-cyan-300/90 pl-7">
              {filialNome}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 whitespace-nowrap">
                Meta de Cobertura:
              </span>
              <Select
                value={diasCobertura}
                onChange={setDiasCobertura}
                options={COVERAGE_OPTIONS}
                className="w-28"
              />
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void fetchPrediction()}
              disabled={loading}
              className="bg-cyan-500/10 border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20 hover:text-cyan-200"
            >
              <RefreshCcw
                size={14}
                className={cn("mr-2 text-cyan-400", loading && "animate-spin")}
              />
              Atualizar
            </Button>
          </div>
        </div>

        {(urgentCount > 0 || alertCount > 0 || totalSugestao > 0) && (
          <div className="flex flex-wrap items-center gap-2">
            {urgentCount > 0 && (
              <Badge
                variant="outline"
                className="bg-red-500/20 border-red-500/30 text-red-300"
              >
                <AlertTriangle size={12} className="mr-1" />
                {urgentCount} compra(s) urgente(s)
              </Badge>
            )}
            {alertCount > urgentCount && (
              <Badge
                variant="outline"
                className="bg-amber-500/20 border-amber-500/30 text-amber-300"
              >
                <Clock size={12} className="mr-1" />
                {alertCount - urgentCount} em atenção
              </Badge>
            )}
            {totalSugestao > 0 && (
              <Badge
                variant="outline"
                className="bg-cyan-500/20 border-cyan-500/30 text-cyan-300"
              >
                <ShoppingCart size={12} className="mr-1" />
                Total sugerido: {formatNumber(totalSugestao)} L
              </Badge>
            )}
          </div>
        )}
      </CardHeader>

      <CardContent className="space-y-6">
        {liquidPredictions.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {liquidPredictions.map((prediction) => (
              <TankPredictionCard
                key={`${prediction.produto_codigo}-${prediction.tipo_combustivel}`}
                prediction={prediction}
                empresaCodigo={empresaCodigo}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <TrendingDown className="mx-auto h-10 w-10 text-slate-500 mb-3" />
            <p className="text-slate-400">
              Nenhum tanque líquido encontrado para {filialNome}
            </p>
          </div>
        )}

        {gnvPredictions.length > 0 ? (
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-sky-400/90">
              GNV — Vazão / Canalizado (fora da regra de carreta)
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {gnvPredictions.map((prediction) => (
                <TankPredictionCard
                  key={`gnv-${prediction.produto_codigo}-${prediction.tipo_combustivel}`}
                  prediction={prediction}
                  empresaCodigo={empresaCodigo}
                />
              ))}
            </div>
          </div>
        ) : null}

        {data?.observacoes && data.observacoes.length > 0 && (
          <div className="text-xs text-slate-500 leading-relaxed">
            {data.observacoes.join(" | ")}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
