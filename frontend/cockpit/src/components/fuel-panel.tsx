"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { fmtBRL, fmtLitrosPreciso } from "@/lib/format";
import type { AdelaideMetrics } from "@/types/metrics";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";

const chartConfig = {
  litros: { label: "Litros", color: "hsl(var(--chart-1))" },
};

export function FuelPanel({
  data,
  loading,
}: {
  data?: AdelaideMetrics | null;
  loading?: boolean;
}) {
  const rows = (data?.combustiveis ?? []).map((c) => ({
    nome: c.nome ?? c.codigo ?? "Combustível",
    litros: Number(c.litros ?? c.quantidade ?? 0),
    valor: Number(c.valor ?? 0),
  }));

  return (
    <div className="grid gap-4 px-4 lg:grid-cols-2 lg:px-6">
      <Card className="omie-card">
        <CardHeader>
          <CardTitle>Galonagem por combustível</CardTitle>
          <CardDescription>Indicadores do período selecionado</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <Skeleton className="h-[280px] w-full" />
          ) : rows.length === 0 ? (
            <p className="text-sm text-muted-foreground">Sem dados de combustível.</p>
          ) : (
            <ChartContainer config={chartConfig} className="h-[280px] w-full">
              <BarChart data={rows} margin={{ left: 8, right: 8, top: 8 }}>
                <CartesianGrid vertical={false} strokeDasharray="3 3" opacity={0.2} />
                <XAxis
                  dataKey="nome"
                  tickLine={false}
                  axisLine={false}
                  fontSize={11}
                  interval={0}
                  angle={-12}
                  textAnchor="end"
                  height={56}
                />
                <YAxis tickLine={false} axisLine={false} width={48} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Bar dataKey="litros" fill="var(--color-litros)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ChartContainer>
          )}
        </CardContent>
      </Card>

      <Card className="omie-card">
        <CardHeader>
          <CardTitle>Detalhamento</CardTitle>
          <CardDescription>Conferência com relatório do posto</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <Skeleton className="h-[280px] w-full" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Combustível</TableHead>
                  <TableHead className="text-right">Litros</TableHead>
                  <TableHead className="text-right">Valor</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((row) => (
                  <TableRow key={row.nome}>
                    <TableCell className="font-medium">{row.nome}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {fmtLitrosPreciso(row.litros)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {fmtBRL(row.valor)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
