"use client";

import { useEffect, useState, useCallback } from "react";
import { 
  CheckCircle2, 
  Clock, 
  RefreshCcw,
  AlertTriangle,
  Fuel,
  Wallet,
  User
} from "lucide-react";
import { apiService } from "@/lib/api";
import { ExecutiveAlert } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { motion } from "motion/react";
import { useGlobalFilter } from "@/contexts/global-filter-context";
import { GlobalFilterHeader } from "@/components/executive/global-filter-header";
import { InfoTooltip } from "@/components/ui/info-tooltip";

const CATEGORY_CONFIG: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  QUEBRA_CAIXA: { icon: Wallet, color: "text-red-500", label: "Quebra de Caixa" },
  ABASTECIMENTO_RETIDO: { icon: Fuel, color: "text-amber-500", label: "Abastecimento Retido" },
  GIRO_CAIXA: { icon: Clock, color: "text-orange-500", label: "Giro de Caixa" },
  DESVIO_TANQUE: { icon: AlertTriangle, color: "text-purple-500", label: "Desvio de Tanque" },
  ESTOURO_VACUO: { icon: AlertTriangle, color: "text-blue-500", label: "Estouro Vacuo" },
  RUPTURA_CURVA_A: { icon: AlertTriangle, color: "text-cyan-500", label: "Ruptura Curva A" },
};

export default function AlertManagementPage() {
  const [alerts, setAlerts] = useState<ExecutiveAlert[]>([]);
  const [history, setHistory] = useState<ExecutiveAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'pending' | 'history'>('pending');

  const { periodDates, selectedFilial, isConsolidated } = useGlobalFilter();

  const fetchData = useCallback(async () => {
    console.log("[Alerts] Iniciando fetch...", { start: periodDates.start, end: periodDates.end, filial: selectedFilial });
    try {
      setLoading(true);
      const [pending, past] = await Promise.all([
        apiService.getDashboardBundle(periodDates.start, periodDates.end).catch((e) => {
          console.error("[Alerts] Erro getDashboardBundle:", e);
          return { active_alerts: [] };
        }),
        apiService.getAlertHistory(periodDates.start, periodDates.end).catch((e) => {
          console.error("[Alerts] Erro getAlertHistory:", e);
          return [];
        })
      ]);
      
      console.log("[Alerts] Dados recebidos:", { pending, past });
      
      let pendingAlerts = pending.active_alerts || [];
      let historyAlerts = Array.isArray(past) ? past as ExecutiveAlert[] : [];
      
      if (!isConsolidated && selectedFilial) {
        pendingAlerts = pendingAlerts.filter((a: ExecutiveAlert) => a.unit_id === selectedFilial);
        historyAlerts = historyAlerts.filter((a: ExecutiveAlert) => a.unit_id === selectedFilial);
      }
      
      setAlerts(pendingAlerts);
      setHistory(historyAlerts);
    } catch (err) {
      console.error("[Alerts] Erro geral:", err);
      setAlerts([]);
      setHistory([]);
    } finally {
      setLoading(false);
    }
  }, [periodDates.start, periodDates.end, selectedFilial, isConsolidated]);

  useEffect(() => {
    (async () => {
      await fetchData();
    })();
  }, [fetchData]);

  const handleResolve = async (id: number) => {
    try {
      await apiService.resolveAlert(id, "Resolvido via Central de Alertas");
      fetchData();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erro ao resolver";
      alert("Erro ao resolver: " + message);
    }
  };

  if (loading) {
    return <div className="flex h-full items-center justify-center p-8"><RefreshCcw className="animate-spin" /></div>;
  }

  const criticalCount = alerts.filter(a => a.severity === 'CRITICAL').length;
  const warningCount = alerts.filter(a => a.severity === 'WARNING').length;
  const totalImpact = alerts.reduce((sum, a) => sum + (a.impact_rs || 0), 0);

  return (
    <div className="p-4 lg:p-8 max-w-[1400px] mx-auto space-y-6">
      <header className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            Gestao de Alertas Proativos
            <InfoTooltip content="Central unificada de alertas de Pista (abastecimentos retidos), Caixa (quebras financeiras) e Tanques (desvios volumetricos) detectados automaticamente pela IA." />
          </h1>
          <p className="text-slate-500 text-sm">Monitore e resolva excecoes criticas detectadas pela inteligencia</p>
        </div>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={fetchData}
          disabled={loading}
          className="bg-cyan-500/10 border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20 hover:text-cyan-200"
        >
          <RefreshCcw size={14} className={cn("mr-2 text-cyan-400", loading && "animate-spin")} /> Sincronizar
        </Button>
      </header>

      <GlobalFilterHeader />

      {/* KPIs de Alertas */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-slate-800/50 border-slate-700/50">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-400">Alertas Criticos</p>
                <p className="text-2xl font-bold text-red-400">{criticalCount}</p>
              </div>
              <div className="p-2 bg-red-500/10 rounded-lg">
                <AlertTriangle className="text-red-400" size={20} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800/50 border-slate-700/50">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-400">Alertas Atencao</p>
                <p className="text-2xl font-bold text-amber-400">{warningCount}</p>
              </div>
              <div className="p-2 bg-amber-500/10 rounded-lg">
                <Clock className="text-amber-400" size={20} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800/50 border-slate-700/50">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-400">Total Pendentes</p>
                <p className="text-2xl font-bold text-slate-100">{alerts.length}</p>
              </div>
              <div className="p-2 bg-slate-500/10 rounded-lg">
                <User className="text-slate-400" size={20} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800/50 border-slate-700/50">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-400">Impacto Total (R$)</p>
                <p className="text-2xl font-bold text-cyan-400">
                  {totalImpact.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
                </p>
              </div>
              <div className="p-2 bg-cyan-500/10 rounded-lg">
                <Wallet className="text-cyan-400" size={20} />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="flex border-b border-white/10 gap-8">
        <button 
          onClick={() => setActiveTab('pending')}
          className={cn(
            "pb-4 text-sm font-medium transition-colors relative",
            activeTab === 'pending' ? "text-blue-500" : "text-slate-500 hover:text-slate-300"
          )}
        >
          Pendentes ({alerts.length})
          {activeTab === 'pending' && <motion.div layoutId="tab" className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500" />}
        </button>
        <button 
          onClick={() => setActiveTab('history')}
          className={cn(
            "pb-4 text-sm font-medium transition-colors relative",
            activeTab === 'history' ? "text-blue-500" : "text-slate-500 hover:text-slate-300"
          )}
        >
          Histórico Resolvido
          {activeTab === 'history' && <motion.div layoutId="tab" className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500" />}
        </button>
      </div>

      <div className="space-y-4">
        {activeTab === 'pending' ? (
          alerts.length === 0 ? (
            <div className="text-center py-20 bg-slate-900/50 rounded-xl border border-dashed border-white/10">
              <CheckCircle2 className="mx-auto text-green-500 mb-4" size={48} />
              <h3 className="text-lg font-semibold text-white">Tudo sob controle!</h3>
              <p className="text-slate-500">Não há alertas críticos pendentes para o período.</p>
            </div>
          ) : (
            alerts.map((alert) => (
              <AlertItem key={alert.id} alert={alert} onResolve={() => handleResolve(alert.id)} />
            ))
          )
        ) : (
          history.filter(a => a.is_resolved).map((alert) => (
            <AlertItem key={alert.id} alert={alert} isHistory />
          ))
        )}
      </div>
    </div>
  );
}

function AlertItem({ alert, onResolve, isHistory }: { alert: ExecutiveAlert, onResolve?: () => void, isHistory?: boolean }) {
  const isCritical = alert.severity === 'CRITICAL';
  const config = CATEGORY_CONFIG[alert.category] || { icon: AlertTriangle, color: "text-slate-400", label: alert.category };
  const CategoryIcon = config.icon;

  const severityLabel = isCritical ? "ALTA" : "MEDIA";
  const severityColor = isCritical ? "bg-red-500/20 text-red-300 border-red-500/30" : "bg-amber-500/20 text-amber-300 border-amber-500/30";

  return (
    <Card className={cn("overflow-hidden border-l-4 bg-slate-800/50", isHistory ? "opacity-75 border-l-slate-500" : isCritical ? "border-l-red-500 shadow-lg shadow-red-500/5" : "border-l-orange-500")}>
      <CardContent className="p-0">
        <div className="flex flex-col md:flex-row md:items-center">
          <div className="p-5 flex-1 space-y-3">
            <div className="flex items-center gap-3 flex-wrap">
              <div className={cn("flex items-center gap-1.5 px-2 py-1 rounded-md bg-slate-700/50", config.color)}>
                <CategoryIcon size={14} />
                <span className="text-xs font-medium">{config.label}</span>
              </div>
              <Badge variant="outline" className={cn("text-xs", severityColor)}>
                Gravidade: {severityLabel}
              </Badge>
              <span className="text-xs text-slate-500 flex items-center gap-1">
                <Clock size={12} /> {new Date(alert.created_at).toLocaleString("pt-BR")}
              </span>
              {alert.unit_id && (
                <Badge variant="outline" className="text-[10px] font-mono bg-slate-700/50">
                  Filial #{alert.unit_id}
                </Badge>
              )}
            </div>
            
            <div>
              <h3 className="text-base font-bold text-white">{alert.title}</h3>
              <p className="text-sm text-slate-400 mt-1">{alert.description}</p>
            </div>

            {alert.impact_rs !== null && alert.impact_rs !== undefined && (
              <div className="flex items-center gap-4 text-sm">
                <div>
                  <span className="text-slate-500">Impacto Estimado:</span>
                  <span className={cn("ml-2 font-mono font-bold text-lg", isCritical ? "text-red-400" : "text-amber-400")}>
                    {alert.impact_rs.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
                  </span>
                </div>
              </div>
            )}
          </div>

          <div className="p-5 md:border-l border-slate-700/50 bg-slate-900/50 flex flex-col justify-center gap-2 min-w-[180px]">
            {!isHistory ? (
              <>
                <Button size="sm" className="w-full bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300" onClick={onResolve}>
                  Resolver Agora
                </Button>
                <Button variant="outline" size="sm" className="w-full border-slate-600 text-slate-300 hover:bg-slate-700">
                  Investigar DRE
                </Button>
              </>
            ) : (
              <div className="space-y-1">
                <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Resolvido por</p>
                <p className="text-xs font-medium text-slate-300">admin@logos.com</p>
                <p className="text-[10px] text-slate-400 italic mt-2">&ldquo;Diferenca conferida no caixa fisico.&rdquo;</p>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
