"use client";

import { useState, useEffect, useCallback } from "react";
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
  Fuel,
  TrendingDown,
  RefreshCcw,
  Package,
} from "lucide-react";
import { cn } from "@/lib/utils";

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

const STATUS_CONFIG = {
  OK: {
    color: "bg-emerald-500/20 border-emerald-500/30 text-emerald-300",
    icon: Fuel,
    label: "Saudável",
  },
  ATENCAO: {
    color: "bg-amber-500/20 border-amber-500/30 text-amber-300",
    icon: Clock,
    label: "Atenção",
  },
  COMPRA_URGENTE: {
    color: "bg-red-500/20 border-red-500/30 text-red-300",
    icon: AlertTriangle,
    label: "Risco de Ruptura - Pedir Carreta",
  },
};

function formatNumber(value: number, decimals: number = 0): string {
  return value.toLocaleString("pt-BR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function TankPredictionCard({ prediction }: { prediction: TankPrediction }) {
  const config = STATUS_CONFIG[prediction.status_alerta] || STATUS_CONFIG.OK;
  const StatusIcon = config.icon;

  const occupancyColor =
    prediction.ocupacao_percentual > 70
      ? "text-emerald-400"
      : prediction.ocupacao_percentual > 30
      ? "text-amber-400"
      : "text-red-400";

  return (
    <Card className="bg-slate-800/50 border-slate-700/50">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium text-slate-200">
            {prediction.produto_nome}
          </CardTitle>
          <Badge variant="outline" className={cn("text-[10px] max-w-[200px] text-center", config.color)}>
            <StatusIcon size={12} className="mr-1 shrink-0" />
            {prediction.alerta_label || config.label}
          </Badge>
        </div>
        <p className="text-xs text-slate-300">{prediction.tipo_combustivel}</p>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <p className="text-xs text-slate-300">Estoque Atual</p>
            <p className="text-lg font-bold text-white">
              {formatNumber(prediction.estoque_atual_litros)} L
            </p>
            <p className={cn("text-xs", occupancyColor)}>
              {prediction.ocupacao_percentual.toFixed(1)}% da capacidade
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-300">Autonomia (Dias)</p>
            <p
              className={cn(
                "text-lg font-bold",
                prediction.autonomia_dias_restantes < 1.5
                  ? "text-rose-400"
                  : prediction.autonomia_dias_restantes < 3
                  ? "text-amber-400"
                  : "text-emerald-400"
              )}
            >
              {prediction.autonomia_dias_restantes.toFixed(1)} dias
            </p>
            <p className="text-xs text-slate-300">
              Média 7d: {formatNumber(prediction.consumo_medio_diario)} L/dia
            </p>
          </div>
        </div>

        <div className="border-t border-slate-700/50 pt-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-xs text-slate-400">Consumo Diario</p>
              <p className="text-sm font-medium text-slate-200">
                {formatNumber(prediction.consumo_medio_diario)} L/dia
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-400">Capacidade</p>
              <p className="text-sm font-medium text-slate-200">
                {formatNumber(prediction.capacidade_tanque)} L
              </p>
            </div>
          </div>
        </div>

        {prediction.sugestao_compra_litros > 0 && (
          <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <ShoppingCart size={14} className="text-cyan-400" />
              <span className="text-xs font-medium text-cyan-300">
                Sugestao de Compra
              </span>
            </div>
            <p className="text-xl font-bold text-cyan-300">
              {formatNumber(prediction.sugestao_compra_litros)} L
            </p>
            <p className="text-xs text-cyan-400/70">
              Para {prediction.dias_cobertura_desejado} dias de cobertura
            </p>
          </div>
        )}

        {prediction.observacoes.length > 0 && (
          <div className="text-xs text-slate-500 italic">
            {prediction.observacoes.join("; ")}
          </div>
        )}
      </CardContent>
    </Card>
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

  const fetchPrediction = useCallback(async () => {
    console.log("[InventoryPrediction] Iniciando fetch...", { empresaCodigo, diasCobertura, leadTimeHoras });
    setLoading(true);
    setError(null);
    try {
      const result = await apiService.getInventoryPrediction(
        empresaCodigo,
        parseInt(diasCobertura),
        leadTimeHoras
      );
      console.log("[InventoryPrediction] Resposta recebida:", result);
      setData(result);
      if (!result.success) {
        setError(result.observacoes.join("; ") || "Erro ao buscar previsao");
      }
    } catch (err) {
      console.error("[InventoryPrediction] Erro no fetch:", err);
      setError("Erro ao conectar com o servidor");
    } finally {
      setLoading(false);
    }
  }, [empresaCodigo, diasCobertura, leadTimeHoras]);

  useEffect(() => {
    fetchPrediction();
  }, [fetchPrediction]);

  if (loading) {
    return (
      <Card className="bg-slate-800/50 border-slate-700/50">
        <CardHeader>
          <div className="flex items-center justify-between">
            <Skeleton className="h-6 w-48 bg-slate-700" />
            <Skeleton className="h-9 w-32 bg-slate-700" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-64 bg-slate-700" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error && !data) {
    return (
      <Card className="bg-slate-800/50 border-slate-700/50">
        <CardContent className="py-8 text-center">
          <AlertTriangle className="mx-auto h-12 w-12 text-amber-500 mb-4" />
          <p className="text-slate-300 mb-4">{error}</p>
          <Button
            onClick={fetchPrediction}
            className="bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20"
          >
            Tentar Novamente
          </Button>
        </CardContent>
      </Card>
    );
  }

  const urgentCount = data?.tanques_urgentes || 0;
  const alertCount = data?.tanques_com_alerta || 0;

  return (
    <Card className="bg-slate-800/50 border-slate-700/50">
      <CardHeader className="pb-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-2">
            <Package className="h-5 w-5 text-cyan-400" />
            <CardTitle className="text-lg text-slate-100">
              Previsao de Estoque & Sugestao de Compras
              {empresaNome ? ` — ${empresaNome}` : ` — Filial ${empresaCodigo}`}
            </CardTitle>
            <InfoTooltip content="Calculo preditivo de run-out baseado no consumo medio historico. Sugere volume de compra para manter a meta de cobertura em dias." />
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Meta de Cobertura:</span>
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
              onClick={fetchPrediction}
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

        {(urgentCount > 0 || alertCount > 0) && (
          <div className="flex items-center gap-3 mt-3">
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
                {alertCount - urgentCount} em atencao
              </Badge>
            )}
            {data?.total_sugestao_compra_litros && data.total_sugestao_compra_litros > 0 && (
              <Badge
                variant="outline"
                className="bg-cyan-500/20 border-cyan-500/30 text-cyan-300"
              >
                <ShoppingCart size={12} className="mr-1" />
                Total sugerido: {formatNumber(data.total_sugestao_compra_litros)} L
              </Badge>
            )}
          </div>
        )}
      </CardHeader>

      <CardContent>
        {data?.predicoes && data.predicoes.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {data.predicoes.map((prediction) => (
              <TankPredictionCard 
                key={`${prediction.produto_codigo}-${prediction.tipo_combustivel}`} 
                prediction={prediction} 
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <TrendingDown className="mx-auto h-12 w-12 text-slate-500 mb-4" />
            <p className="text-slate-400">
              Nenhum tanque encontrado para esta filial
            </p>
          </div>
        )}

        {data?.observacoes && data.observacoes.length > 0 && (
          <div className="mt-4 text-xs text-slate-500">
            {data.observacoes.join(" | ")}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
