"use client";

import { useEffect, useState, useCallback } from "react";
import { 
  CheckCircle2, 
  Clock, 
  RefreshCcw
} from "lucide-react";
import { apiService } from "@/lib/api";
import { ExecutiveAlert } from "@/types/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { motion } from "motion/react";

export default function AlertManagementPage() {
  const [alerts, setAlerts] = useState<ExecutiveAlert[]>([]);
  const [history, setHistory] = useState<ExecutiveAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'pending' | 'history'>('pending');

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [pending, past] = await Promise.all([
        apiService.getDashboardBundle("2026-07-17", "2026-07-23"),
        apiService.getAlertHistory("2026-07-01", "2026-07-23")
      ]);
      setAlerts(pending.active_alerts);
      setHistory(past as ExecutiveAlert[]);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

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

  return (
    <div className="p-4 lg:p-8 max-w-[1200px] mx-auto space-y-6">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Gestão de Alertas</h1>
          <p className="text-slate-500 text-sm">Monitore e resolva exceções críticas detectadas pela inteligência</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchData}>
          <RefreshCcw size={14} className="mr-2" /> Sincronizar
        </Button>
      </header>

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

  return (
    <Card className={cn("overflow-hidden border-l-4", isHistory ? "opacity-75 border-l-slate-500" : isCritical ? "border-l-red-500 shadow-lg shadow-red-500/5" : "border-l-orange-500")}>
      <CardContent className="p-0">
        <div className="flex flex-col md:flex-row md:items-center">
          <div className="p-5 flex-1 space-y-3">
            <div className="flex items-center gap-3">
              <Badge variant={isHistory ? "secondary" : isCritical ? "destructive" : "warning"}>
                {alert.category}
              </Badge>
              <span className="text-xs text-slate-500 flex items-center gap-1">
                <Clock size={12} /> {new Date(alert.created_at).toLocaleString()}
              </span>
              {alert.unit_id && (
                <Badge variant="outline" className="text-[10px] font-mono">ID {alert.unit_id}</Badge>
              )}
            </div>
            
            <div>
              <h3 className="text-base font-bold text-white">{alert.title}</h3>
              <p className="text-sm text-slate-500 mt-1">{alert.description}</p>
            </div>

            {alert.impact_rs && (
              <div className="text-sm">
                <span className="text-slate-500">Impacto Estimado:</span>
                <span className={cn("ml-2 font-mono font-bold", isCritical ? "text-red-500" : "text-orange-500")}>
                  R$ {alert.impact_rs.toLocaleString()}
                </span>
              </div>
            )}
          </div>

          <div className="p-5 md:border-l border-white/5 bg-slate-50/5 dark:bg-slate-900/50 flex flex-col justify-center gap-2 min-w-[180px]">
            {!isHistory ? (
              <>
                <Button size="sm" className="w-full" onClick={onResolve}>
                  Resolver Agora
                </Button>
                <Button variant="outline" size="sm" className="w-full">
                  Investigar DRE
                </Button>
              </>
            ) : (
              <div className="space-y-1">
                <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Resolvido por</p>
                <p className="text-xs font-medium">admin@logos.com</p>
                <p className="text-[10px] text-slate-400 italic mt-2">&ldquo;Diferença conferida no caixa físico.&rdquo;</p>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
