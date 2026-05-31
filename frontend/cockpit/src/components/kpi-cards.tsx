"use client";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { fmtBRL, fmtLitros } from "@/lib/format";
import type { AdelaideMetrics } from "@/types/metrics";
import {
  CircleDollarSignIcon,
  DropletsIcon,
  FuelIcon,
  ReceiptIcon,
  TrendingUpIcon,
} from "lucide-react";

interface KpiCardsProps {
  data?: AdelaideMetrics | null;
  loading?: boolean;
}

const cards = [
  {
    key: "faturamento",
    label: "Produtos não combustíveis",
    icon: CircleDollarSignIcon,
    getValue: (d: AdelaideMetrics) => fmtBRL(Number(d.faturamento_nao_combustivel)),
    foot: "Vendas no período",
  },
  {
    key: "galonagem",
    label: "Galonagem total",
    icon: FuelIcon,
    getValue: (d: AdelaideMetrics) => fmtLitros(Number(d.galonagem_total)),
    foot: (d: AdelaideMetrics) =>
      `${d.qtd_abastecimentos.toLocaleString("pt-BR")} abastecimentos`,
  },
  {
    key: "credito",
    label: "Crédito recuperável",
    icon: TrendingUpIcon,
    getValue: (d: AdelaideMetrics) => fmtBRL(Number(d.credito_recuperavel)),
    foot: "Estimativa fiscal · PIS/COFINS",
  },
  {
    key: "despesas",
    label: "Despesas de caixa",
    icon: ReceiptIcon,
    getValue: (d: AdelaideMetrics) => fmtBRL(Number(d.despesas_caixa)),
    foot: "Movimentações no caixa",
  },
] as const;

export function KpiCards({ data, loading }: KpiCardsProps) {
  return (
    <div className="grid grid-cols-1 gap-4 px-4 lg:px-6 @xl/main:grid-cols-2 @5xl/main:grid-cols-4">
      {cards.map(({ key, label, icon: Icon, getValue, foot }) => (
        <Card key={key} className="omie-card">
          <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
            <div className="space-y-1">
              <CardDescription className="text-xs font-medium uppercase tracking-wide">
                {label}
              </CardDescription>
              <CardTitle className="text-2xl font-bold tabular-nums @[250px]/card:text-3xl">
                {loading ? <Skeleton className="h-9 w-36" /> : data ? getValue(data) : "—"}
              </CardTitle>
            </div>
            <div className="omie-kpi-icon">
              <Icon className="size-5" />
            </div>
          </CardHeader>
          <CardFooter className="flex items-center justify-between text-sm text-muted-foreground">
            {loading ? (
              <Skeleton className="h-4 w-48" />
            ) : data ? (
              typeof foot === "function" ? foot(data) : foot
            ) : (
              "Aguardando API"
            )}
            {data?.dados_reais && !loading && (
              <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-500">
                <DropletsIcon className="size-3" />
                Live
              </Badge>
            )}
          </CardFooter>
        </Card>
      ))}
    </div>
  );
}
