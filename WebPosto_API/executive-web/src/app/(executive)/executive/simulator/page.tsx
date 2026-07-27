"use client";

import { useState, useEffect, useCallback } from "react";
import { 
  Calculator, 
  TrendingUp, 
  RotateCcw,
  Info,
  Zap,
  Wallet
} from "lucide-react";
import { apiService } from "@/lib/api";
import { SimulationInput, SimulationResult } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export default function FinancialSimulatorPage() {
  const [input, setInput] = useState<SimulationInput>({
    delta_preco_bomba_rs: 0,
    variacao_volume_pct: 0,
    taxa_antecipacao_mensal_pct: 1.5
  });
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);

  const runSimulation = useCallback(async () => {
    try {
      setLoading(true);
      const res = await apiService.simulateMarginImpact(input);
      setResult(res);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erro na simulação";
      alert("Erro na simulação: " + message);
    } finally {
      setLoading(false);
      setInitialLoading(false);
    }
  }, [input]);

  useEffect(() => {
    const timer = setTimeout(() => {
      runSimulation();
    }, 500);
    return () => clearTimeout(timer);
  }, [runSimulation]);

  const formatCurrency = (val: number) => 
    new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);

  return (
    <div className="p-4 lg:p-8 max-w-[1200px] mx-auto space-y-6">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className="bg-purple-500/10 text-purple-400 border-purple-500/20">S54</Badge>
            <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Simulator</span>
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Simulador Estratégico de Margem</h1>
          <p className="text-slate-400 text-sm">Projeção de impacto em EBITDA, Margem e Vácuo de Caixa</p>
        </div>
        <Button 
          variant="outline" 
          className="bg-slate-900 border-white/5 hover:bg-slate-800"
          onClick={() => setInput({
            delta_preco_bomba_rs: 0,
            variacao_volume_pct: 0,
            taxa_antecipacao_mensal_pct: 1.5
          })}
        >
          <RotateCcw size={14} className="mr-2" /> Resetar
        </Button>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-4 space-y-6">
          <Card className="border-white/5 bg-slate-900/40">
            <CardHeader>
              <CardTitle className="text-sm font-bold flex items-center gap-2">
                <Calculator size={16} className="text-purple-500" /> Parâmetros de Simulação
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-8 pt-4">
              <ControlGroup
                label="Preço na Bomba (Delta R$)"
                value={input.delta_preco_bomba_rs}
                suffix="R$/L"
                min={-0.50}
                max={0.50}
                step={0.01}
                onChange={(v: number) => setInput(prev => ({ ...prev, delta_preco_bomba_rs: v }))}
                hint="Impacto direto na margem bruta unitária."
                positiveIndicator={input.delta_preco_bomba_rs >= 0}
              />

              <ControlGroup
                label="Variação de Volume (%)"
                value={input.variacao_volume_pct}
                suffix="%"
                min={-20}
                max={20}
                step={0.5}
                onChange={(v: number) => setInput(prev => ({ ...prev, variacao_volume_pct: v }))}
                hint="Simula elasticidade ou perda de mercado."
                positiveIndicator={input.variacao_volume_pct >= 0}
              />

              <ControlGroup
                label="Taxa de Antecipação (%)"
                value={input.taxa_antecipacao_mensal_pct || 1.5}
                suffix="% a.m."
                min={0}
                max={3}
                step={0.1}
                onChange={(v: number) => setInput(prev => ({ ...prev, taxa_antecipacao_mensal_pct: v }))}
                hint="Custo financeiro para cobrir o vácuo de caixa."
                positiveIndicator={false}
                accentColor="blue"
              />
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-8 space-y-6">
          {initialLoading || loading ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Skeleton className="h-32 w-full" />
                <Skeleton className="h-32 w-full" />
              </div>
              <Skeleton className="h-[300px] w-full" />
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <ResultCard 
                  title="Impacto no EBITDA"
                  value={formatCurrency(result?.impacto_ebitda_rs || 0)}
                  subValue="Lucro Operacional mensal projetado"
                  positive={ (result?.impacto_ebitda_rs || 0) >= 0}
                  icon={<TrendingUp size={24} />}
                />
                <ResultCard 
                  title="Impacto no Capital de Giro"
                  value={formatCurrency(result?.impacto_capital_giro_rs || 0)}
                  subValue="Necessidade adicional de caixa (Vácuo)"
                  positive={(result?.impacto_capital_giro_rs || 0) <= 0}
                  icon={<Wallet size={24} />}
                />
              </div>

              <Card className="border-white/5 bg-slate-900/40">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Zap size={18} className="text-yellow-500" />
                    DRE Projetada (Mensal)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex justify-between py-3 border-b border-white/5">
                       <span className="text-slate-400 text-sm">Faturamento Bruto Projetado</span>
                       <span className="font-semibold text-white">{formatCurrency(result?.faturamento_projetado_rs || 0)}</span>
                    </div>
                    <div className="flex justify-between py-3 border-b border-white/5">
                       <span className="text-slate-400 text-sm">EBITDA Projetado</span>
                       <span className="font-semibold text-green-500">{formatCurrency(result?.ebitda_projetado_rs || 0)}</span>
                    </div>
                    <div className="flex justify-between py-3 border-b border-white/5">
                       <span className="text-slate-400 text-sm">Margem Líquida (Pós-Cartão)</span>
                       <span className="font-semibold text-blue-500">{formatCurrency(result?.margem_liquida_pos_cartoes_projetada_rs || 0)}</span>
                    </div>
                    <div className="flex justify-between py-3 border-b border-white/5">
                       <span className="text-slate-400 text-sm">Capital de Giro Projetado</span>
                       <span className={cn("font-semibold", (result?.necessidade_capital_projetada_rs || 0) >= 0 ? "text-red-500" : "text-green-500")}>
                         {formatCurrency(result?.necessidade_capital_projetada_rs || 0)}
                       </span>
                    </div>
                    <div className="flex justify-between py-4 font-bold text-lg bg-white/5 rounded-lg px-4">
                       <span className="text-white">Resultado Líquido do Cenário</span>
                       <span className={cn((result?.variacao_margem_liquida_rs || 0) >= 0 ? "text-green-500" : "text-red-500")}>
                         {formatCurrency(result?.variacao_margem_liquida_rs || 0)}
                       </span>
                    </div>
                  </div>

                  <div className="mt-6 p-4 rounded-lg bg-blue-500/5 border border-blue-500/20 flex gap-4">
                    <Info className="text-blue-500 shrink-0" size={20} />
                    <p className="text-xs text-blue-400 leading-relaxed">
                      Esta simulação utiliza como base o volume médio mensal do grupo (100.000 L). 
                      O impacto real pode variar conforme a participação de cada combustível e as taxas individuais de cada bandeira de cartão.
                    </p>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function ControlGroup({ label, value, suffix, min, max, step, onChange, hint, positiveIndicator, accentColor = 'green' }: { label: string; value: number; suffix: string; min: number; max: number; step: number; onChange: (v: number) => void; hint: string; positiveIndicator: boolean; accentColor?: string }) {
  const displayValue = value > 0 ? `+${value.toFixed(step < 0.1 ? 2 : 1)}` : value.toFixed(step < 0.1 ? 2 : 1);
  const colorClass = accentColor === 'blue' 
    ? 'text-blue-500' 
    : positiveIndicator ? 'text-green-500' : 'text-red-500';

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-end">
         <label className="text-xs font-bold uppercase text-slate-500 tracking-wider">{label}</label>
         <span className={cn("text-sm font-bold font-mono", colorClass)}>
           {displayValue} {suffix}
         </span>
      </div>
      <Slider 
        min={min} 
        max={max} 
        step={step} 
        value={[value]} 
        onValueChange={([v]) => onChange(v)}
      />
      <p className="text-[10px] text-slate-500 italic">{hint}</p>
    </div>
  );
}

function ResultCard({ title, value, subValue, positive, icon }: { title: string; value: string; subValue: string; positive: boolean; icon: React.ReactNode }) {
  return (
    <Card className={cn(
      "overflow-hidden border-l-4 bg-slate-900/40",
      positive ? "border-l-green-500" : "border-l-red-500"
    )}>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-bold uppercase text-slate-500 tracking-wider mb-1">{title}</p>
            <h3 className={cn("text-2xl font-bold", positive ? "text-green-500" : "text-red-500")}>{value}</h3>
            <p className="text-[10px] text-slate-400 mt-2">{subValue}</p>
          </div>
          <div className={cn("p-2 rounded-full", positive ? "bg-green-500/10 text-green-500" : "bg-red-500/10 text-red-500")}>
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
