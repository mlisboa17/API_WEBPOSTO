"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { fetchAllAbastecimentos } from "@/lib/abastecimento-api";
import {
  aggregateAbastecimentos,
  presetRange,
  type AbastecimentoResumo,
} from "@/lib/abastecimento-aggregate";
import { fmtBRL, fmtLitrosPreciso } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RecifeClock } from "@/components/recife-clock";
import { cn } from "@/lib/utils";
import {
  DropletsIcon,
  FuelIcon,
  HashIcon,
  RefreshCwIcon,
  WalletIcon,
} from "lucide-react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";

const chartConfig = {
  litros: { label: "Litros", color: "hsl(var(--chart-1))" },
};

type Preset = "hoje" | "ontem" | "7d" | "custom";

export function AbastecimentoLive() {
  const [preset, setPreset] = useState<Preset>("hoje");
  const [dataInicial, setDataInicial] = useState(() => presetRange("hoje").inicio);
  const [dataFinal, setDataFinal] = useState(() => presetRange("hoje").fim);
  const [resumo, setResumo] = useState<AbastecimentoResumo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const applyPreset = (id: "hoje" | "ontem" | "7d") => {
    const { inicio, fim } = presetRange(id);
    setPreset(id);
    setDataInicial(inicio);
    setDataFinal(fim);
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rows = await fetchAllAbastecimentos(dataInicial, dataFinal);
      setResumo(aggregateAbastecimentos(rows));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao carregar abastecimentos");
      setResumo(null);
    } finally {
      setLoading(false);
    }
  }, [dataInicial, dataFinal]);

  useEffect(() => {
    load();
  }, [load]);

  const recentes = useMemo(() => {
    if (!resumo) return [];
    return [...resumo.registros]
      .sort((a, b) =>
        String(b.horaFiscal ?? "").localeCompare(String(a.horaFiscal ?? "")),
      )
      .slice(0, 25);
  }, [resumo]);

  const kpis = [
    {
      label: "Total litros",
      value: resumo ? fmtLitrosPreciso(resumo.totalLitros) : "—",
      icon: FuelIcon,
    },
    {
      label: "Valor total",
      value: resumo ? fmtBRL(resumo.totalValor) : "—",
      icon: WalletIcon,
    },
    {
      label: "Abastecimentos",
      value: resumo ? resumo.totalRegistros.toLocaleString("pt-BR") : "—",
      icon: HashIcon,
    },
    {
      label: "Combustíveis",
      value: resumo ? String(resumo.porCombustivel.length) : "—",
      icon: DropletsIcon,
    },
  ];

  return (
    <div className="flex flex-1 flex-col gap-4 py-4 md:gap-6 md:py-6">
      <Card className="omie-hero mx-4 lg:mx-6">
        <CardHeader className="pb-3">
          <CardTitle>Galonagem · WebPosto</CardTitle>
          <CardDescription>
            Fuso <strong>America/Recife</strong> · <RecifeClock /> · paginação{" "}
            <code className="text-xs">ultimoCodigo</code>
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <div className="flex flex-wrap gap-2">
            {(
              [
                ["hoje", "Hoje"],
                ["ontem", "Ontem"],
                ["7d", "7 dias"],
              ] as const
            ).map(([id, label]) => (
              <Button
                key={id}
                size="sm"
                variant="ghost"
                className={cn(
                  "rounded-full px-4",
                  preset === id ? "omie-tab-active" : "omie-tab",
                )}
                onClick={() => applyPreset(id)}
              >
                {label}
              </Button>
            ))}
          </div>
          <div className="grid gap-2">
            <Label htmlFor="di">Data inicial</Label>
            <Input
              id="di"
              type="date"
              value={dataInicial}
              className="w-40"
              onChange={(e) => {
                setPreset("custom");
                setDataInicial(e.target.value);
              }}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="df">Data final</Label>
            <Input
              id="df"
              type="date"
              value={dataFinal}
              className="w-40"
              onChange={(e) => {
                setPreset("custom");
                setDataFinal(e.target.value);
              }}
            />
          </div>
          <Button variant="outline" onClick={load} disabled={loading}>
            <RefreshCwIcon className={loading ? "animate-spin" : ""} />
            Atualizar
          </Button>
          {error && <p className="w-full text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 px-4 sm:grid-cols-2 lg:grid-cols-4 lg:px-6">
        {kpis.map(({ label, value, icon: Icon }) => (
          <Card key={label} className="omie-card">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardDescription className="text-xs font-medium uppercase tracking-wide">
                {label}
              </CardDescription>
              <div className="omie-kpi-icon">
                <Icon className="size-4" />
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <Skeleton className="h-8 w-32" />
              ) : (
                <p className="text-2xl font-bold tabular-nums">{value}</p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 px-4 lg:grid-cols-2 lg:px-6">
        <Card className="omie-card">
          <CardHeader>
            <CardTitle>Por combustível</CardTitle>
            <CardDescription>Conferência com relatório gerencial do posto</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Skeleton className="h-[260px] w-full" />
            ) : !resumo?.porCombustivel.length ? (
              <p className="text-sm text-muted-foreground">Nenhum registro no período.</p>
            ) : (
              <ChartContainer config={chartConfig} className="h-[260px] w-full">
                <BarChart data={resumo.porCombustivel} margin={{ top: 8, right: 8, left: 8 }}>
                  <CartesianGrid vertical={false} strokeDasharray="3 3" opacity={0.2} />
                  <XAxis
                    dataKey="nome"
                    tickLine={false}
                    axisLine={false}
                    fontSize={11}
                    interval={0}
                    angle={-15}
                    textAnchor="end"
                    height={52}
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
            <CardTitle>Resumo por produto</CardTitle>
            <CardDescription>
              {dataInicial === dataFinal ? dataInicial : `${dataInicial} → ${dataFinal}`}
            </CardDescription>
          </CardHeader>
          <CardContent className="max-h-[320px] overflow-auto">
            {loading ? (
              <Skeleton className="h-[260px] w-full" />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Combustível</TableHead>
                    <TableHead className="text-right">Litros</TableHead>
                    <TableHead className="text-right">Valor</TableHead>
                    <TableHead className="text-right">Qtd</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {resumo?.porCombustivel.map((row) => (
                    <TableRow key={row.codigo || row.nome}>
                      <TableCell className="font-medium">{row.nome}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {fmtLitrosPreciso(row.litros)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {fmtBRL(row.valor)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{row.qtd}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="omie-card mx-4 lg:mx-6">
        <CardHeader>
          <div className="flex items-center justify-between gap-2">
            <div>
              <CardTitle>Últimos abastecimentos</CardTitle>
              <CardDescription>25 registros mais recentes do período</CardDescription>
            </div>
            {resumo && !loading && (
              <Badge variant="secondary">Aferições excluídas</Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          {loading ? (
            <Skeleton className="h-48 w-full" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Data</TableHead>
                  <TableHead>Hora</TableHead>
                  <TableHead>Combustível</TableHead>
                  <TableHead>Bico</TableHead>
                  <TableHead className="text-right">Litros</TableHead>
                  <TableHead className="text-right">Valor</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentes.map((row, i) => (
                  <TableRow key={`${row.dataFiscal}-${row.horaFiscal}-${i}`}>
                    <TableCell>{row.dataFiscal ?? "—"}</TableCell>
                    <TableCell>{row.horaFiscal ?? "—"}</TableCell>
                    <TableCell>
                      {row.nomeProduto ??
                        resumo?.porCombustivel.find(
                          (p) => p.codigo === String(row.codigoProduto),
                        )?.nome ??
                        row.codigoProduto}
                    </TableCell>
                    <TableCell>{row.codigoBico ?? "—"}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {fmtLitrosPreciso(Number(row.quantidade ?? 0))}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {fmtBRL(
                        Number(row.valorTotal ?? 0) ||
                          Number(row.quantidade ?? 0) * Number(row.valorUnitario ?? 0),
                      )}
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
