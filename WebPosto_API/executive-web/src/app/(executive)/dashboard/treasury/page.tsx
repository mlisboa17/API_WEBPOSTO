"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { 
  Landmark, 
  RefreshCcw, 
  ArrowRightLeft, 
  ShieldAlert,
  ShieldCheck,
  Timer
} from "lucide-react";
import { 
  BarChart,
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  Legend,
  ReferenceLine
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { GlobalFilterHeader } from "@/components/executive/global-filter-header";
import { useGlobalFilter } from "@/contexts/global-filter-context";
import { apiService } from "@/lib/api";
import { cn } from "@/lib/utils";

interface UnitLiquidity {
  unit_id: number;
  unit_name: string;
  saldo_bancario_rs: number;
  contas_a_pagar_48h_rs: number;
  necessidade_imediata_rs: number;
}

interface SweepSuggestion {
  origem_unit_id: number;
  origem_name: string;
  destino_unit_id: number;
  destino_name: string;
  valor_sugerido_rs: number;
  justificativa: string;
}

interface TreasuryData {
  saldo_consolidado_disponivel_rs: number;
  exposicao_cheque_especial_total_rs: number;
  aging_disponibilidade_caixa_dias: number;
  liquidez_por_unidade: UnitLiquidity[];
  sugestoes_sweep: SweepSuggestion[];
}

interface ChartRow {
  name: string;
  saldo: number;
  cp48h: number;
  necessidade: number;
}

export default function TreasuryDashboardPage() {
  const [data, setData] = useState<TreasuryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { selectedFilial, isConsolidated, periodLabel } = useGlobalFilter();

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const result = await apiService.getTreasuryConsolidation(
        isConsolidated ? undefined : selectedFilial
      ) as TreasuryData;
      setData(result);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erro ao carregar tesouraria";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [selectedFilial, isConsolidated]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const liquidity = useMemo(() => data?.liquidez_por_unidade || [], [data]);
  const sweep = useMemo(() => data?.sugestoes_sweep || [], [data]);
  const consolidatedBalance = data?.saldo_consolidado_disponivel_rs || 0;
  const overdraftExposure = data?.exposicao_cheque_especial_total_rs || 0;
  const agingDays = data?.aging_disponibilidade_caixa_dias || 0;

  const chartData: ChartRow[] = useMemo(() => {
    return liquidity.map((unit) => ({
      name: unit.unit_name.split(' ').slice(0, 2).join(' '),
      saldo: unit.saldo_bancario_rs,
      cp48h: unit.contas_a_pagar_48h_rs,
      necessidade: unit.necessidade_imediata_rs
    }));
  }, [liquidity]);

  const formatBRL = (val: number) =>
    new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);

  return (
    <div className="p-4 lg:p-8 max-w-[1600px] mx-auto space-y-6">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className="bg-blue-500/10 text-blue-400 border-blue-500/20">S54</Badge>
            <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Treasury</span>
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Tesouraria & Cash Pooling</h1>
          <p className="text-slate-400 text-sm">
            Consolidação de saldo, exposição a cheque especial e sugestões de sweep • {periodLabel}
          </p>
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
      ) : (
        <div className="space-y-6 animate-in fade-in duration-500">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <KpiCard 
              icon={<Landmark className={consolidatedBalance >= 0 ? "text-green-500" : "text-red-500"} />}
              title="Saldo Consolidado Disponível"
              value={formatBRL(consolidatedBalance)}
              subValue="Saldo líquido do grupo"
              status={consolidatedBalance >= 0 ? 'positive' : 'negative'}
            />
            <KpiCard 
              icon={<ShieldAlert className={overdraftExposure > 0 ? "text-red-500" : "text-green-500"} />}
              title="Exposição a Cheque Especial"
              value={formatBRL(overdraftExposure)}
              subValue={overdraftExposure > 0 ? "Ação imediata recomendada" : "Sem risco identificado"}
              status={overdraftExposure > 0 ? 'negative' : 'positive'}
            />
            <KpiCard 
              icon={<Timer className={agingDays < 7 ? "text-green-500" : agingDays < 15 ? "text-yellow-500" : "text-red-500"} />}
              title="Aging de Disponibilidade"
              value={`${agingDays.toFixed(1)} dias`}
              subValue="Cobertura de caixa do grupo"
              status={agingDays < 7 ? 'positive' : agingDays < 15 ? 'warning' : 'negative'}
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="lg:col-span-2 border-white/5 bg-slate-900/40">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Landmark size={18} className="text-blue-500" />
                  Liquidez por Unidade vs CP 48h
                </CardTitle>
                <CardDescription>Saldo bancário disponível em comparação com contas a pagar nos próximos 2 dias</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[350px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} margin={{ top: 20, right: 20, bottom: 20, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.1} />
                      <XAxis dataKey="name" fontSize={11} tick={{fill: '#94a3b8'}} axisLine={false} tickLine={false} />
                      <YAxis fontSize={11} tick={{fill: '#94a3b8'}} axisLine={false} tickLine={false} tickFormatter={(val) => `R$${val/1000}k`} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                        // eslint-disable-next-line @typescript-eslint/no-explicit-any
                        formatter={(value: any, name: any) => [formatBRL(Number(value)), String(name)]}
                      />
                      <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                      <ReferenceLine y={0} stroke="#ffffff" strokeOpacity={0.2} />
                      <Bar dataKey="saldo" name="Saldo Disponível" stackId="a" fill="#10b981" radius={[4, 4, 0, 0]} barSize={50} />
                      <Bar dataKey="cp48h" name="CP 48h" stackId="b" fill="#f43f5e" radius={[4, 4, 0, 0]} barSize={50} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card className="border-white/5 bg-slate-900/40">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <ArrowRightLeft size={18} className="text-yellow-500" />
                  Sugestões de Sweep
                </CardTitle>
                <CardDescription>Transferências intragrupo para otimizar caixa</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {sweep.length === 0 ? (
                  <div className="py-10 text-center">
                    <div className="inline-flex p-3 rounded-full bg-green-500/10 text-green-500 mb-3">
                      <ShieldCheck size={24} />
                    </div>
                    <p className="text-sm text-slate-400">Não há necessidade de sweep no momento.</p>
                  </div>
                ) : (
                  sweep.map((s, idx) => (
                    <div key={idx} className="p-4 rounded-lg border border-yellow-500/20 bg-yellow-500/5">
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-xs font-bold text-white">{s.origem_name}</span>
                        <ArrowRightLeft size={14} className="text-yellow-500" />
                        <span className="text-xs font-bold text-white">{s.destino_name}</span>
                      </div>
                      <div className="text-center mb-3">
                        <span className="text-2xl font-bold text-yellow-500">{formatBRL(s.valor_sugerido_rs)}</span>
                      </div>
                      <p className="text-[10px] text-slate-400 leading-relaxed bg-slate-900/50 p-2 rounded">
                        {s.justificativa}
                      </p>
                      <Button size="sm" className="w-full mt-3 bg-yellow-500/20 text-yellow-500 hover:bg-yellow-500/30 border border-yellow-500/20">
                        Executar Sweep
                      </Button>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </div>

          <Card className="border-white/5 bg-slate-900/40">
            <CardHeader>
              <CardTitle className="text-lg">Detalhamento de Liquidez por Unidade</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="rounded-md border border-white/5 overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left border-b border-white/5 bg-white/5">
                        <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase">Unidade</th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase text-right">Saldo Bancário</th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase text-right">CP 48h</th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase text-right">Necessidade Imediata</th>
                        <th className="px-4 py-3 text-xs font-bold text-slate-500 uppercase text-center">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {liquidity.map((unit, idx) => {
                        const isDeficit = unit.necessidade_imediata_rs > 0;
                        return (
                          <tr key={idx} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                            <td className="px-4 py-3 font-medium text-xs">{unit.unit_name}</td>
                            <td className="px-4 py-3 text-right font-mono text-xs text-green-500">{formatBRL(unit.saldo_bancario_rs)}</td>
                            <td className="px-4 py-3 text-right font-mono text-xs text-red-500">{formatBRL(unit.contas_a_pagar_48h_rs)}</td>
                            <td className={cn("px-4 py-3 text-right font-mono text-xs font-bold", isDeficit ? "text-red-500" : "text-green-500")}>
                              {formatBRL(unit.necessidade_imediata_rs)}
                            </td>
                            <td className="px-4 py-3 text-center">
                              <Badge variant="outline" className={cn(
                                "text-[10px]",
                                isDeficit ? "text-red-500 border-red-500/20" : "text-green-500 border-green-500/20"
                              )}>
                                {isDeficit ? "DEFICIT" : "SUPERÁVIT"}
                              </Badge>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

function KpiCard({ icon, title, value, subValue, status }: { icon: React.ReactNode; title: string; value: string; subValue: string; status: 'positive' | 'negative' | 'warning' }) {
  const borderColor = {
    positive: 'border-green-500/30',
    negative: 'border-red-500/30',
    warning: 'border-yellow-500/30'
  }[status];

  return (
    <Card className={cn("border-l-4 p-4 bg-slate-900/40", borderColor)}>
      <div className="flex items-start gap-4">
        <div className="p-2.5 rounded-lg bg-white/5">{icon}</div>
        <div className="flex-1">
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{title}</p>
          <p className="text-2xl font-bold text-white mt-1">{value}</p>
          <p className="text-[11px] text-slate-400 mt-0.5">{subValue}</p>
        </div>
      </div>
    </Card>
  );
}
