"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { 
  Truck, 
  RefreshCcw, 
  TrendingUp,
  AlertTriangle,
  ShieldCheck
} from "lucide-react";
import { 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  Legend,
  Cell,
  ComposedChart,
  Line
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { GlobalFilterHeader } from "@/components/executive/global-filter-header";
import { PurchaseOrderAssistant } from "@/components/executive/purchase-order-assistant";
import { useGlobalFilter } from "@/contexts/global-filter-context";
import { apiService } from "@/lib/api";
import { cn } from "@/lib/utils";
import { InactiveModuleBanner } from "@/components/executive/inactive-module-banner";

interface LogisticsSupplier {
  fornecedor: string;
  custo_frete_medio_rs_litro: number;
  markup_logistico_pct: number;
  delta_fob_cif_rs_litro: number;
  total_litros_comprados: number;
  filial?: string;
  base_operacional?: string;
}

interface LogisticsData {
  custo_frete_efetivo_total_rs: number;
  frete_medio_grupo_rs_litro: number;
  custo_oportunidade_frete_total_rs: number;
  eficiencia_por_fornecedor: LogisticsSupplier[];
  fonte?: string;
  notas_com_frete?: number;
  detalhe_fonte?: string | null;
}

interface ChartRow {
  name: string;
  fullName: string;
  frete: number;
  markup: number;
  delta: number;
  litros: number;
}

export default function LogisticsDashboardPage() {
  const [data, setData] = useState<LogisticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const {
    selectedFilial,
    isConsolidated,
    periodDates,
    periodLabel,
    filialShortLabel,
  } = useGlobalFilter();

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const result = await apiService.getLogisticsEfficiency(
        periodDates.start,
        periodDates.end,
        isConsolidated ? undefined : selectedFilial
      ) as LogisticsData;
      setData(result);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erro ao carregar logística";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [periodDates.start, periodDates.end, selectedFilial, isConsolidated]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const suppliers = useMemo(
    () => data?.eficiencia_por_fornecedor || [],
    [data]
  );
  const totalFreight = data?.custo_frete_efetivo_total_rs || 0;
  const avgFreight = data?.frete_medio_grupo_rs_litro || 0;
  const opportunityCost = data?.custo_oportunidade_frete_total_rs || 0;
  const hasData = suppliers.length > 0 || (data?.notas_com_frete || 0) > 0;
  const fonteLabel = data?.fonte || "Dado Real - Fonte NF webPosto";

  const chartData: ChartRow[] = useMemo(() => {
    return suppliers.map((s) => ({
      name: s.fornecedor.split(' ')[0],
      fullName: s.fornecedor,
      frete: s.custo_frete_medio_rs_litro,
      markup: s.markup_logistico_pct,
      delta: s.delta_fob_cif_rs_litro,
      litros: s.total_litros_comprados
    }));
  }, [suppliers]);

  const formatBRL = (val: number) =>
    new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);

  return (
    <div className="p-4 lg:p-8 max-w-[1600px] mx-auto space-y-6 opacity-50 pointer-events-none select-none">
      <InactiveModuleBanner
        className="pointer-events-auto opacity-100"
        title="Logística de Frete indisponível"
        description="Módulo em desenvolvimento. A prévia visual permanece para referência — botões e atualizações estão desabilitados."
      />
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className="bg-slate-800 text-slate-400 border-slate-700">S54</Badge>
            <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Logistics</span>
          </div>
          <h1 className="text-3xl font-bold text-slate-500 tracking-tight">Eficiência Logística</h1>
          <p className="text-slate-500 text-sm">
            Custo real de frete por litro (NF de entrada) • {periodLabel}
          </p>
          <Badge
            variant="outline"
            className="mt-2 border-emerald-500/40 bg-emerald-500/10 text-emerald-300 text-[10px] font-semibold"
          >
            {fonteLabel}
          </Badge>
        </div>
        <Button 
          size="sm" 
          onClick={fetchData} 
          disabled={loading}
          className="bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20 hover:text-cyan-200"
        >
          <RefreshCcw size={14} className={cn("mr-2 text-cyan-400", loading && "animate-spin")} /> Atualizar
        </Button>
      </header>

      <GlobalFilterHeader />

      <PurchaseOrderAssistant
        empresaCodigo={isConsolidated ? undefined : selectedFilial}
        filialLabel={isConsolidated ? "Selecione uma filial" : filialShortLabel}
      />

      {loading ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[1, 2, 3].map(i => <Skeleton key={i} className="h-28 w-full" />)}
          </div>
          <Skeleton className="h-[400px] w-full" />
          <Skeleton className="h-[300px] w-full" />
        </div>
      ) : error ? (
        <div className="p-8 text-center">
          <h2 className="text-xl text-red-500 font-bold mb-2">{error}</h2>
          <Button onClick={fetchData} className="bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20">Tentar Novamente</Button>
        </div>
      ) : !hasData ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="grid size-16 place-items-center rounded-full bg-slate-800 mb-4">
            <AlertTriangle size={32} className="text-slate-300" />
          </div>
          <h3 className="text-lg font-medium text-white mb-2">Sem Registro de Frete no Período</h3>
          <p className="text-sm text-slate-300 max-w-md">
            Nenhuma NF de entrada com <span className="text-white font-medium">valorFrete</span> e
            volumetria de carreta no período. Amplie o filtro de datas ou confira o cadastro de compras.
          </p>
        </div>
      ) : (
        <div className="space-y-6 animate-in fade-in duration-500">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <KpiCard 
              icon={<Truck className="text-blue-500" />}
              title="Custo de Frete Total"
              value={totalFreight > 0 ? formatBRL(totalFreight) : "R$ 0,00"}
              subValue={`${data?.notas_com_frete || 0} NF(s) com frete destacado`}
              status={null}
              trend={null}
            />
            <KpiCard 
              icon={<TrendingUp className="text-sky-300" />}
              title="Frete Médio (R$/L)"
              value={avgFreight > 0 ? `R$ ${avgFreight.toFixed(4)}/L` : "R$ 0,0000/L"}
              subValue="valorFrete ÷ litros descarregados"
              status={null}
              trend={null}
            />
            <KpiCard 
              icon={<AlertTriangle className={opportunityCost > 0 ? "text-red-500" : "text-green-500"} />}
              title="Custo de Oportunidade"
              value={formatBRL(opportunityCost)}
              subValue={opportunityCost > 0 ? "CIF acima do FOB histórico" : "Frete otimizado"}
              status={opportunityCost > 0 ? 'negative' : 'positive'}
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="lg:col-span-2 border-slate-800 bg-slate-900/90">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Truck size={18} className="text-blue-500" />
                  Frete Médio por Fornecedor (R$/L)
                </CardTitle>
                <CardDescription>
                  Calculado com frete destacado na NF e litros da carreta • {data?.detalhe_fonte || "webPosto"}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[350px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={chartData} margin={{ top: 20, right: 20, bottom: 20, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.1} />
                      <XAxis dataKey="name" fontSize={11} tick={{fill: '#94a3b8'}} axisLine={false} tickLine={false} />
                      <YAxis yAxisId="left" fontSize={11} tick={{fill: '#94a3b8'}} axisLine={false} tickLine={false} label={{ value: 'R$/L', angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 10 }} />
                      <YAxis yAxisId="right" orientation="right" fontSize={11} tick={{fill: '#94a3b8'}} axisLine={false} tickLine={false} label={{ value: 'Markup %', angle: 90, position: 'insideRight', fill: '#64748b', fontSize: 10 }} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                        // eslint-disable-next-line @typescript-eslint/no-explicit-any
                        formatter={(value: any, name: any) => {
                          const val = value ?? 0;
                          const label = String(name);
                          if (label === 'frete') return [`R$ ${Number(val).toFixed(4)}`, 'Frete Médio'];
                          if (label === 'markup') return [`${Number(val).toFixed(2)}%`, 'Markup'];
                          if (label === 'delta') return [`R$ ${Number(val).toFixed(4)}`, 'Delta FOB x CIF'];
                          return [String(val), label];
                        }}
                      />
                      <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                      <Bar yAxisId="left" dataKey="frete" name="Frete Médio (R$/L)" fill="#3b82f6" radius={[4, 4, 0, 0]} barSize={50}>
                        {chartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.delta > 0 ? '#f43f5e' : '#3b82f6'} />
                        ))}
                      </Bar>
                      <Line yAxisId="right" type="monotone" dataKey="markup" name="Markup %" stroke="#f59e0b" strokeWidth={2} dot={{ r: 4 }} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-800 bg-slate-900/90">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <AlertTriangle size={18} className="text-red-500" />
                  Oportunidade de Redução
                </CardTitle>
                <CardDescription>Fornecedores com CIF acima do FOB</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {suppliers.filter(s => s.delta_fob_cif_rs_litro > 0).length === 0 ? (
                  <div className="py-10 text-center">
                    <div className="inline-flex p-3 rounded-full bg-green-500/10 text-green-500 mb-3">
                      <ShieldCheck size={24} />
                    </div>
                    <p className="text-sm text-slate-400">Nenhum fornecedor com CIF acima do FOB histórico.</p>
                  </div>
                ) : (
                  suppliers
                    .filter(s => s.delta_fob_cif_rs_litro > 0)
                    .sort((a, b) => b.delta_fob_cif_rs_litro - a.delta_fob_cif_rs_litro)
                    .map((s, idx) => (
                      <div key={idx} className="p-3 rounded-lg border border-slate-800 bg-white/5">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-bold text-white">{s.fornecedor}</span>
                          <Badge variant="outline" className="text-red-500 border-red-500/20 text-[10px]">
                            +{s.delta_fob_cif_rs_litro.toFixed(4)}/L
                          </Badge>
                        </div>
                        <p className="text-[10px] text-slate-400">
                          {s.total_litros_comprados.toLocaleString()} L comprados | Markup: {s.markup_logistico_pct.toFixed(2)}%
                        </p>
                      </div>
                    ))
                )}
              </CardContent>
            </Card>
          </div>

          <Card className="border-slate-800 bg-slate-900/90">
            <CardHeader>
              <CardTitle className="text-lg">Detalhamento por Distribuidora</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="rounded-md border border-slate-800 overflow-hidden">
                <Table>
                  <TableHeader className="bg-white/5">
                    <TableRow className="border-slate-800 hover:bg-transparent">
                      <TableHead>Fornecedor</TableHead>
                      <TableHead className="text-right">Total Litros</TableHead>
                      <TableHead className="text-right">Frete Médio R$/L</TableHead>
                      <TableHead className="text-right">Markup Logístico</TableHead>
                      <TableHead className="text-right">Delta FOB x CIF</TableHead>
                      <TableHead className="text-center">Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {suppliers.map((s, idx) => (
                      <TableRow key={idx} className="border-slate-800">
                        <TableCell className="font-medium text-xs">{s.fornecedor}</TableCell>
                        <TableCell className="text-right text-xs font-mono">{s.total_litros_comprados.toLocaleString()} L</TableCell>
                        <TableCell className="text-right text-xs font-mono">R$ {s.custo_frete_medio_rs_litro.toFixed(4)}</TableCell>
                        <TableCell className="text-right text-xs font-mono">{s.markup_logistico_pct.toFixed(2)}%</TableCell>
                        <TableCell className={cn("text-right text-xs font-mono font-bold", s.delta_fob_cif_rs_litro > 0 ? "text-red-500" : "text-green-500")}>
                          R$ {s.delta_fob_cif_rs_litro.toFixed(4)}
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge variant="outline" className={cn(
                            "text-[10px]",
                            s.delta_fob_cif_rs_litro > 0 ? "text-red-500 border-red-500/20" : "text-green-500 border-green-500/20"
                          )}>
                            {s.delta_fob_cif_rs_litro > 0 ? "CIF ALTO" : "EFICIENTE"}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

function KpiCard({ icon, title, value, subValue, status }: { icon: React.ReactNode; title: string; value: string; subValue: string; status: 'positive' | 'negative' | null | undefined; trend?: null }) {
  return (
    <Card className={cn(
      "border-l-4 p-4",
      status === 'negative' ? "border-red-500/30 bg-red-500/5" : "border-slate-800 bg-slate-900/90"
    )}>
      <div className="flex items-start gap-4">
        <div className="p-2.5 rounded-lg bg-white/5">{icon}</div>
        <div className="flex-1">
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-300">{title}</p>
          <p className="text-2xl font-bold text-white mt-1 font-mono">{value}</p>
          <p className="text-[11px] text-slate-300 mt-0.5">{subValue}</p>
        </div>
      </div>
    </Card>
  );
}
