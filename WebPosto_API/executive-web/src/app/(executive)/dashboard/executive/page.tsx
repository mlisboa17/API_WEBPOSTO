"use client";

import { useEffect, useState } from "react";
import { 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle, 
  Wallet, 
  Droplet, 
  RefreshCcw,
  BarChart3,
  Search
} from "lucide-react";
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer
} from "recharts";
import { apiService } from "@/lib/api";
import { DashboardBundle, DreLine } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { DrePanel } from "@/components/executive/dre-panel";
import { ExpenseClassificationModal } from "@/components/executive/expense-classification-modal";
import { Skeleton } from "@/components/ui/skeleton";

export default function ExecutiveDashboardPage() {
  const [data, setData] = useState<DashboardBundle | null>(null);
  const [dreLines, setDreLines] = useState<DreLine[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const start = "2026-07-17";
      const end = "2026-07-23";
      
      const [bundle, dre] = await Promise.all([
        apiService.getDashboardBundle(start, end),
        apiService.getCompleteDre(start, end)
      ]);

      setData(bundle);
      setDreLines(dre.lines || []);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erro ao carregar dashboard";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    (async () => {
      await fetchDashboardData();
    })();
  }, []);

  const handleResolveAlert = async (id: number) => {
    try {
      await apiService.resolveAlert(id, "Resolvido via Cockpit 30s");
      fetchDashboardData();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erro ao resolver alerta";
      alert("Erro ao resolver alerta: " + message);
    }
  };

  const formatBRL = (val: number | null | undefined) => {
    if (val === null || val === undefined) return "R$ 0,00";
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);
  };

  if (loading && !data) {
    return (
      <div className="p-8 space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-32 w-full" />)}
        </div>
        <Skeleton className="h-[400px] w-full" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 text-center flex flex-col items-center justify-center min-h-[60vh]">
        <AlertTriangle size={48} className="text-red-500 mb-4" />
        <h1 className="text-2xl font-bold text-white">Erro de Conectividade</h1>
        <p className="text-slate-400 mt-2 max-w-md">{error}</p>
        <Button onClick={fetchDashboardData} className="mt-6 gap-2">
          <RefreshCcw size={16} /> Tentar Novamente
        </Button>
      </div>
    );
  }

  const { synthesis, cash_cycle, active_alerts, top_risks, top_opportunities } = data;

  return (
    <div className="p-4 lg:p-8 max-w-[1600px] mx-auto space-y-6 animate-in fade-in duration-500">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className="bg-blue-500/10 text-blue-400 border-blue-500/20 px-2 py-0">
              LOGOS EXECUTIVE
            </Badge>
            <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">V5.3 Stable</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Cockpit do Presidente</h1>
          <p className="text-slate-400 text-sm">Visão 360º consolidada — {data.period.start} a {data.period.end}</p>
        </div>
        <div className="flex items-center gap-3">
           <div className="hidden md:flex flex-col items-end">
             <span className="text-[10px] text-slate-500 uppercase font-bold">Última Sincronização</span>
             <span className="text-xs font-medium text-green-500">{new Date(synthesis.generated_at).toLocaleTimeString()}</span>
           </div>
          <Button variant="outline" size="sm" onClick={fetchDashboardData} className="bg-slate-900/50 border-white/10 hover:bg-slate-800">
            <RefreshCcw size={14} className={cn("mr-2", loading && "animate-spin")} /> Atualizar
          </Button>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard 
          title="EBITDA Projetado" 
          value={formatBRL(synthesis.total_gross_margin)} 
          subValue={`${synthesis.gross_margin_pct?.toFixed(1) || '0.0'}% de Margem`}
          trend={12.5}
          icon={<TrendingUp className="text-green-500" />}
        />
        <KpiCard 
          title="Margem Combustível" 
          value={`${formatBRL(synthesis.fuel_margin_per_liter)}/L`} 
          subValue={`${synthesis.fuel_liters_sold?.toLocaleString() || '0'} Litros`}
          trend={-2.1}
          icon={<Droplet className="text-blue-500" />}
        />
        <KpiCard 
          title="Vácuo de Caixa" 
          value={formatBRL(cash_cycle.necessidade_capital_giro_rs)} 
          subValue={`${cash_cycle.vacuo_financeiro_dias?.toFixed(1) || '0.0'} dias de ciclo`}
          trend={cash_cycle.status === 'NORMAL' ? 0 : 5}
          status={cash_cycle.status}
          icon={<Wallet className="text-orange-500" />}
        />
        <KpiCard 
          title="Alertas Críticos" 
          value={active_alerts.filter(a => a.severity === 'CRITICAL').length.toString()} 
          subValue={`${active_alerts.length} alertas pendentes`}
          icon={<AlertTriangle className={cn(active_alerts.some(a => a.severity === 'CRITICAL') ? "text-red-500 animate-pulse" : "text-slate-500")} />}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 border-white/5 bg-slate-900/40 backdrop-blur-sm">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-xl font-bold flex items-center gap-2">
                  <BarChart3 className="text-blue-500" size={20} />
                  Performance Operacional
                </CardTitle>
                <CardDescription>DRE consolidada por departamento e unidade</CardDescription>
              </div>
              <Button variant="ghost" size="sm" className="text-blue-400 hover:text-blue-300 gap-1">
                Ver DRE Completa <Search size={14} />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <DrePanel 
              lines={dreLines} 
              onInspectPending={() => setIsModalOpen(true)} 
              pendingCount={synthesis.pending_expenses_count}
            />
          </CardContent>
        </Card>

        <Card className="lg:col-span-1 border-white/5 bg-slate-900/40 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-lg font-bold flex items-center gap-2">
              <AlertTriangle className="text-yellow-500" size={18} />
              Central de Alertas
            </CardTitle>
            <CardDescription>Ações prioritárias identificadas pela IA</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {active_alerts.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <div className="bg-green-500/10 p-3 rounded-full mb-3 text-green-500">
                  <RefreshCcw size={24} />
                </div>
                <p className="text-sm text-slate-400">Tudo sob controle.<br/>Nenhuma anomalia detectada.</p>
              </div>
            ) : (
              active_alerts.slice(0, 5).map((alert) => (
                <div key={alert.id} className="p-3 rounded-lg border border-white/5 bg-white/5 hover:bg-white/10 transition-colors space-y-2">
                  <div className="flex items-start justify-between">
                    <Badge variant={alert.severity === 'CRITICAL' ? 'destructive' : 'secondary'} className="text-[9px] px-1.5 py-0">
                      {alert.category}
                    </Badge>
                    <span className="text-[10px] text-slate-500">{new Date(alert.created_at).toLocaleDateString()}</span>
                  </div>
                  <h4 className="font-semibold text-xs text-white">{alert.title}</h4>
                  <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">{alert.description}</p>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="w-full text-blue-400 hover:text-blue-300 hover:bg-blue-500/10 h-7 text-[10px] font-bold uppercase tracking-tight"
                    onClick={() => handleResolveAlert(alert.id)}
                  >
                    Resolver Agora
                  </Button>
                </div>
              ))
            )}
            {active_alerts.length > 5 && (
              <Button variant="link" className="w-full text-xs text-slate-500" onClick={() => window.location.href='/executive/alerts'}>
                Ver todos os {active_alerts.length} alertas
              </Button>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="border-white/5 bg-slate-900/40">
          <CardHeader>
            <CardTitle className="text-lg font-bold flex items-center gap-2">
              <Droplet className="text-blue-500" size={18} />
              Variação de Tanques
            </CardTitle>
            <CardDescription>Térmica (Física) vs Desvio Real por Unidade (Litros)</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[280px] w-full mt-2">
               <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={[
                    { name: 'VIP', termica: -45.2, real: -120.5 },
                    { name: 'Caiada', termica: -30.1, real: -25.8 },
                    { name: 'Doze', termica: -60.4, real: -85.2 },
                    { name: 'Real', termica: -22.5, real: -12.3 },
                  ]} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} strokeOpacity={0.05} />
                    <XAxis dataKey="name" fontSize={11} axisLine={false} tickLine={false} tick={{fill: '#94a3b8'}} />
                    <YAxis fontSize={11} axisLine={false} tickLine={false} tick={{fill: '#94a3b8'}} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                      itemStyle={{ fontSize: '12px' }}
                    />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                    <Bar dataKey="termica" name="Física/Térmica" fill="#3b82f6" radius={[4, 4, 0, 0]} barSize={32} />
                    <Bar dataKey="real" name="Desvio Real" fill="#f43f5e" radius={[4, 4, 0, 0]} barSize={32} />
                  </BarChart>
               </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card className="border-white/5 bg-slate-900/40">
          <CardHeader>
            <CardTitle className="text-lg font-bold flex items-center gap-2">
              <Search className="text-purple-500" size={18} />
              Radar de Inteligência
            </CardTitle>
            <CardDescription>Mapeamento de riscos financeiros e ganhos potenciais</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6">
             <div className="space-y-3">
               <h5 className="text-[10px] font-bold uppercase tracking-widest text-red-500 border-b border-red-500/10 pb-1">Riscos Prioritários</h5>
               {top_risks.map((risk, i) => (
                 <div key={i} className="group flex items-center justify-between p-2.5 rounded-lg bg-red-500/5 border border-red-500/10 hover:bg-red-500/10 transition-colors">
                   <span className="text-xs text-slate-300">{risk.title}</span>
                   <span className="text-xs font-mono font-bold text-red-500">{formatBRL(risk.impact_rs)}</span>
                 </div>
               ))}
             </div>
             <div className="space-y-3">
               <h5 className="text-[10px] font-bold uppercase tracking-widest text-green-500 border-b border-green-500/10 pb-1">Oportunidades de Ganho</h5>
               {top_opportunities.map((opp, i) => (
                 <div key={i} className="group flex items-center justify-between p-2.5 rounded-lg bg-green-500/5 border border-green-500/10 hover:bg-green-500/10 transition-colors">
                   <span className="text-xs text-slate-300">{opp.title}</span>
                   <span className="text-xs font-mono font-bold text-green-500">{formatBRL(opp.potential_rs)}</span>
                 </div>
               ))}
             </div>
          </CardContent>
        </Card>
      </div>

      <ExpenseClassificationModal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)}
        start={data.period.start}
        end={data.period.end}
      />
    </div>
  );
}

function KpiCard({ title, value, subValue, trend, icon, status }: { title: string; value: string; subValue: string; trend?: number; icon: React.ReactNode; status?: string }) {
  return (
    <Card className="overflow-hidden border-white/5 bg-slate-900/40 backdrop-blur-sm relative group hover:border-white/10 transition-all">
      <div className="absolute top-0 right-0 p-3 opacity-20 group-hover:opacity-40 transition-opacity">
        {icon}
      </div>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-[11px] font-bold uppercase tracking-wider text-slate-500">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold text-white tracking-tight">{value}</div>
        <div className="flex items-center gap-1.5 mt-1">
          {trend !== undefined && (
            <div className={cn(
              "flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-bold", 
              trend >= 0 ? "bg-green-500/10 text-green-500" : "bg-red-500/10 text-red-500"
            )}>
              {trend >= 0 ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
              {Math.abs(trend)}%
            </div>
          )}
          <span className="text-[10px] text-slate-500 font-medium">{subValue}</span>
        </div>
      </CardContent>
      {status === 'CRITICO' && (
        <div className="h-1 w-full bg-red-500/50 absolute bottom-0 left-0" />
      )}
      {status === 'WARNING' && (
        <div className="h-1 w-full bg-yellow-500/50 absolute bottom-0 left-0" />
      )}
    </Card>
  );
}
