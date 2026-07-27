"use client";

import React, { useEffect, useState, useMemo } from "react";
import { 
  TrendingUp, 
  Calendar, 
  RefreshCcw, 
  ShoppingCart, 
  Droplet
} from "lucide-react";
import { 
  ScatterChart, 
  Scatter, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  ZAxis,
  Cell
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { apiService } from "@/lib/api";
import { cn } from "@/lib/utils";

interface HourlyVolume {
  hora: number;
  litros: number;
  ticket_medio: number;
}

interface ElasticityPoint {
  data: string;
  preco_bomba_rs: number;
  volume_litros: number;
  margem_bruta_rs: number;
}

interface AffinityCombo {
  produtos: string[];
  frequencia_conjunta_pct: number;
  ticket_medio_combo: number;
  margem_contribuicao_total_rs: number;
  lift: number;
}

interface SalesAnalyticsData {
  heatmap: { data: Record<string, HourlyVolume[]> };
  elasticidade: ElasticityPoint[];
  coeficiente_elasticidade: number;
  cesta_afinidade: AffinityCombo[];
  taxa_conversao_pista_loja_pct: number;
}

const WEEK_DAYS = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

export default function SalesAnalyticsPage() {
  const [data, setData] = useState<SalesAnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const start = "2026-07-17";
      const end = "2026-07-23";
      const result = await apiService.getSalesAnalytics(start, end) as SalesAnalyticsData;
      setData(result);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erro ao carregar analytics";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    (async () => {
      await fetchData();
    })();
  }, []);

  const heatmapData = useMemo(() => {
    if (!data?.heatmap?.data) return [];
    return Object.entries(data.heatmap.data).flatMap(([day, hours]) => 
      hours.map((h) => ({ ...h, day: Number(day) }))
    );
  }, [data]);

  const maxVolume = useMemo(() => {
    if (heatmapData.length === 0) return 0;
    return Math.max(...heatmapData.map(d => d.litros));
  }, [heatmapData]);

  const elasticityData = useMemo(() => {
    if (!data?.elasticidade) return [];
    return data.elasticidade.map((point) => ({
      ...point,
      margem_rs: point.margem_bruta_rs,
      volume: point.volume_litros / 1000,
    }));
  }, [data]);

  const affinity = data?.cesta_afinidade || [];
  const conversionRate = data?.taxa_conversao_pista_loja_pct ?? 0;

  const getHeatColor = (volume: number) => {
    const intensity = maxVolume > 0 ? volume / maxVolume : 0;
    if (intensity > 0.8) return "bg-blue-500";
    if (intensity > 0.6) return "bg-blue-500/70";
    if (intensity > 0.4) return "bg-blue-400/50";
    if (intensity > 0.2) return "bg-blue-300/30";
    return "bg-blue-200/10";
  };

  const formatBRL = (val: number) =>
    new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);

  return (
    <div className="p-4 lg:p-8 max-w-[1600px] mx-auto space-y-6">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className="bg-blue-500/10 text-blue-400 border-blue-500/20">S54</Badge>
            <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Analytics</span>
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Vendas & Elasticidade</h1>
          <p className="text-slate-400 text-sm">Heatmap de galonagem, curva de elasticidade e cesta de afinidade</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="bg-slate-900 border-white/5">
            <Calendar size={14} className="mr-2" /> 17 a 23 Jul 2026
          </Button>
          <Button size="sm" onClick={fetchData} disabled={loading}>
            <RefreshCcw size={14} className={cn("mr-2", loading && "animate-spin")} /> Atualizar
          </Button>
        </div>
      </header>

      {loading ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[1, 2, 3].map(i => <Skeleton key={i} className="h-32 w-full" />)}
          </div>
          <Skeleton className="h-[400px] w-full" />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Skeleton className="h-[350px] w-full" />
            <Skeleton className="h-[350px] w-full" />
          </div>
        </div>
      ) : error ? (
        <div className="p-8 text-center">
          <h2 className="text-xl text-red-500 font-bold mb-2">{error}</h2>
          <Button onClick={fetchData}>Tentar Novamente</Button>
        </div>
      ) : (
        <div className="space-y-6 animate-in fade-in duration-500">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <KpiCard 
              icon={<Droplet className="text-blue-500" />}
              title="Volume Médio Diário"
              value="42.5k L"
              subValue="Gasolina/Aditivada/Álcool"
            />
            <KpiCard 
              icon={<TrendingUp className="text-green-500" />}
              title="Coeficiente de Elasticidade"
              value={data?.coeficiente_elasticidade ?? -1.25}
              subValue="Impacto preço x volume"
            />
            <KpiCard 
              icon={<ShoppingCart className="text-orange-500" />}
              title="Conversão Pista -> Loja"
              value={`${conversionRate.toFixed(1)}%`}
              subValue="Taxa de retenção de cliente"
            />
          </div>

          <Card className="border-white/5 bg-slate-900/40">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Droplet size={18} className="text-blue-500" />
                Heatmap de Galonagem
              </CardTitle>
              <CardDescription>Volume de litros por dia da semana e horário. Quanto mais azul, maior o pico.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <div className="min-w-[700px]">
                  <div className="grid grid-cols-[60px_repeat(24,_1fr)] gap-0.5">
                    <div className="text-[10px] font-bold text-slate-500 uppercase"></div>
                    {HOURS.map(h => (
                      <div key={h} className="text-[9px] text-center text-slate-500 font-mono">{h}h</div>
                    ))}
                    {WEEK_DAYS.map((day, dayIndex) => (
                      <React.Fragment key={day}>
                        <div className="text-[11px] font-bold text-slate-400 flex items-center justify-center h-8">{day}</div>
                        {HOURS.map(h => {
                          const point = heatmapData.find(d => d.day === dayIndex && d.hora === h);
                          const volume = point?.litros || 0;
                          const ticket = point?.ticket_medio || 0;
                          return (
                            <div
                              key={`${day}-${h}`}
                              title={`${day} ${h}h: ${volume.toFixed(0)} L | Ticket: ${formatBRL(ticket)}`}
                              className={cn(
                                "h-8 rounded-[2px] cursor-pointer transition-all hover:ring-1 hover:ring-white/50 relative group",
                                getHeatColor(volume)
                              )}
                            >
                              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-50 bg-slate-900 text-white text-[10px] p-2 rounded border border-white/10 whitespace-nowrap">
                                {day} {h}h: <strong>{volume.toFixed(0)} L</strong> | Ticket {formatBRL(ticket)}
                              </div>
                            </div>
                          );
                        })}
                      </React.Fragment>
                    ))}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-4 mt-4 justify-end">
                <span className="text-[10px] text-slate-500 uppercase">Baixo</span>
                <div className="flex gap-1">
                  <div className="w-4 h-4 bg-blue-200/10 rounded"></div>
                  <div className="w-4 h-4 bg-blue-300/30 rounded"></div>
                  <div className="w-4 h-4 bg-blue-400/50 rounded"></div>
                  <div className="w-4 h-4 bg-blue-500/70 rounded"></div>
                  <div className="w-4 h-4 bg-blue-500 rounded"></div>
                </div>
                <span className="text-[10px] text-slate-500 uppercase">Pico</span>
              </div>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="border-white/5 bg-slate-900/40">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <TrendingUp size={18} className="text-purple-500" />
                  Elasticidade: Preço x Volume x Margem
                </CardTitle>
                <CardDescription>Cada ponto representa um dia de observação. Tamanho = Margem Bruta.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[350px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.1} />
                      <XAxis 
                        type="number" 
                        dataKey="preco_bomba_rs" 
                        name="Preço" 
                        unit=" R$/L" 
                        fontSize={11}
                        tick={{fill: '#94a3b8'}}
                      />
                      <YAxis 
                        type="number" 
                        dataKey="volume" 
                        name="Volume" 
                        unit=" kL" 
                        fontSize={11}
                        tick={{fill: '#94a3b8'}}
                      />
                      <ZAxis type="number" dataKey="margem_bruta_rs" range={[50, 400]} />
                      <Tooltip 
                        cursor={{ strokeDasharray: '3 3' }}
                        contentStyle={{ backgroundColor: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                        // eslint-disable-next-line @typescript-eslint/no-explicit-any
                        formatter={(value: any, name: any) => {
                          const label = String(name);
                          if (label === 'volume') return [`${value} kL`, 'Volume'];
                          if (label === 'preco_bomba_rs') return [`R$ ${Number(value).toFixed(3)}`, 'Preço'];
                          if (label === 'margem_bruta_rs') return [formatBRL(Number(value)), 'Margem Bruta'];
                          return [String(value), label];
                        }}
                      />
                      <Scatter name="Observações" data={elasticityData} fill="#8b5cf6">
                        {elasticityData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.margem_bruta_rs > 0 ? '#8b5cf6' : '#ef4444'} />
                        ))}
                      </Scatter>
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card className="border-white/5 bg-slate-900/40">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <ShoppingCart size={18} className="text-orange-500" />
                  Cesta de Afinidade (Cross-Selling)
                </CardTitle>
                <CardDescription>Combinações mais lucrativas na conveniência, filtradas por margem total.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 max-h-[350px] overflow-y-auto pr-2">
                  {affinity.length === 0 ? (
                    <p className="text-sm text-slate-500 text-center py-10">Nenhuma cesta identificada.</p>
                  ) : (
                    affinity.map((combo, idx) => (
                      <div key={idx} className="p-3 rounded-lg border border-white/5 bg-white/5 hover:bg-white/10 transition-colors">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex flex-wrap gap-1">
                            {combo.produtos.map((p, i) => (
                              <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 font-medium">
                                {p}
                              </span>
                            ))}
                          </div>
                          <Badge variant="outline" className="text-green-500 border-green-500/20 text-[10px]">
                            +{(combo.lift || 1).toFixed(1)}x Lift
                          </Badge>
                        </div>
                        <div className="grid grid-cols-3 gap-2 text-[11px]">
                          <div className="text-slate-400">
                            <span className="block text-[9px] uppercase tracking-wider">Frequência</span>
                            <span className="font-bold text-white">{(combo.frequencia_conjunta_pct || 0).toFixed(1)}%</span>
                          </div>
                          <div className="text-slate-400">
                            <span className="block text-[9px] uppercase tracking-wider">Ticket Combo</span>
                            <span className="font-bold text-white">{formatBRL(combo.ticket_medio_combo || 0)}</span>
                          </div>
                          <div className="text-slate-400 text-right">
                            <span className="block text-[9px] uppercase tracking-wider">Margem Total</span>
                            <span className="font-bold text-green-500">{formatBRL(combo.margem_contribuicao_total_rs || 0)}</span>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}

function KpiCard({ icon, title, value, subValue }: { icon: React.ReactNode; title: string; value: string | number; subValue: string }) {
  return (
    <Card className="border-white/5 bg-slate-900/40 p-4">
      <div className="flex items-start gap-4">
        <div className="p-2.5 rounded-lg bg-white/5">{icon}</div>
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{title}</p>
          <p className="text-2xl font-bold text-white mt-1">{value}</p>
          <p className="text-[11px] text-slate-400 mt-0.5">{subValue}</p>
        </div>
      </div>
    </Card>
  );
}
