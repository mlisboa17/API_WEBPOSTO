"use client";

import { useEffect, useRef, useState } from "react";
import { AlertTriangle, ArrowRight, CircleDollarSign, Lightbulb, MessageCircleQuestion } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { brl } from "@/lib/utils";
import { ThemeToggle } from "./theme-toggle";

type Insight = {
  id: string; type: string; title: string; confidence: string; priorityScore: number;
  estimatedImpactBRL?: number | null; suggestedOwner?: string; recommendedAction?: string;
  contributingAgents?: string[];
};
type Intelligence = {
  radar?: { priorities?: Insight[]; executiveAnswers?: Record<string, unknown>; governance?: { humanReviewRequired?: boolean } };
  agents?: { presidencyAgent?: { coordinatedPriorities?: Insight[]; message?: string } };
  value?: { summary?: {
    estimatedValue?: { potentialValueBRL?: number };
    businessValueGeneratedByAI?: { totalFinancialValueBRL?: number };
    adoptionRate?: number;
    topContributingAgent?: { agent?: string } | null;
  } };
};
const INSUFFICIENT = "Não existem evidências suficientes para produzir uma recomendação confiável.";

export function PresidencyDashboardV2({ day, detailsHref }: { day: string; detailsHref: string }) {
  const [data, setData] = useState<Intelligence>({});
  const [loading, setLoading] = useState(true);
  const started = useRef(Date.now());
  const clicks = useRef(0);
  const session = useRef("");

  useEffect(() => {
    session.current = sessionStorage.getItem("logos-executive-session") || crypto.randomUUID();
    sessionStorage.setItem("logos-executive-session", session.current);
    void track("PAGE_OPEN", "ATTENTION");
    const controller = new AbortController();
    fetch(`/api/executive-intelligence?day=${encodeURIComponent(day)}`, { signal: controller.signal })
      .then(response => response.json()).then(setData).finally(() => setLoading(false));
    return () => controller.abort();
  }, [day]);

  async function track(eventType: string, feature: string, found = false) {
    clicks.current += eventType === "FEATURE_USED" ? 1 : 0;
    const payload = { eventType, feature, sessionId: session.current || "pending", ...(found ? { elapsedMs: Date.now() - started.current, clicks: clicks.current } : {}) };
    await fetch("/api/executive-adoption", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload), keepalive: true }).catch(() => undefined);
  }

  const priorities = data.agents?.presidencyAgent?.coordinatedPriorities || data.radar?.priorities || [];
  const risks = priorities.filter(item => item.type === "RISK").slice(0, 3);
  const opportunities = priorities.filter(item => item.type === "OPPORTUNITY").slice(0, 3);
  const summary = data.value?.summary;
  const confirmed = summary?.businessValueGeneratedByAI?.totalFinancialValueBRL || 0;
  const estimated = summary?.estimatedValue?.potentialValueBRL || 0;
  const chart = [{ name: "Comprovado", value: confirmed }, { name: "Estimado", value: estimated }];
  const answers = data.radar?.executiveAnswers || {};

  return <main className="min-w-0 flex-1 px-4 py-5 sm:px-7 lg:px-10">
    <header className="mb-5 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
      <div><Badge>Presidência 2.0</Badge><h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">O que precisa da sua decisão hoje</h1><p className="mt-1 text-base text-muted-foreground">{day} · leitura executiva em menos de 30 segundos</p></div>
      <div className="flex w-full gap-2 sm:w-auto"><ThemeToggle/><Button className="min-h-11 flex-1 sm:flex-none" onClick={() => { void track("FEATURE_USED", "DETAILS"); location.href = detailsHref; }}>Análises detalhadas <ArrowRight size={17}/></Button></div>
    </header>
    {loading ? <div className="grid min-h-72 place-items-center text-lg text-muted-foreground">Preparando síntese executiva…</div> :
    <section className="grid gap-5 xl:grid-cols-2" aria-label="Síntese executiva">
      <ExecutiveBlock icon={AlertTriangle} title="O que exige atenção hoje" feature="ATTENTION" onOpen={track}>
        <InsightList items={risks} empty={INSUFFICIENT}/>
      </ExecutiveBlock>
      <ExecutiveBlock icon={Lightbulb} title="O que gera mais valor" feature="VALUE" onOpen={track}>
        <InsightList items={opportunities} empty={INSUFFICIENT}/>
      </ExecutiveBlock>
      <ExecutiveBlock icon={CircleDollarSign} title="Valor gerado pela IA" feature="AI_VALUE" onOpen={track}>
        <div className="grid items-center gap-4 sm:grid-cols-2"><div><p className="text-sm text-muted-foreground">Comprovado com evidência</p><strong className="mt-1 block font-mono text-3xl">{brl(confirmed)}</strong><p className="mt-3 text-sm">Potencial estimado: <strong>{brl(estimated)}</strong></p><p className="text-sm">Adoção: <strong>{summary?.adoptionRate || 0}%</strong></p><p className="text-sm">Maior contribuição: <strong>{summary?.topContributingAgent?.agent || "Aguardando resultado validado"}</strong></p></div><div aria-label="Comparação entre valor comprovado e estimado"><ResponsiveContainer width="100%" height={170}><BarChart data={chart}><CartesianGrid vertical={false}/><XAxis dataKey="name" fontSize={12}/><YAxis hide/><Tooltip formatter={value => brl(Number(value))}/><Bar dataKey="value" fill="var(--info)" radius={[6,6,0,0]}/></BarChart></ResponsiveContainer></div></div>
      </ExecutiveBlock>
      <ExecutiveBlock icon={MessageCircleQuestion} title="Perguntas da Presidência" feature="PRESIDENCY_ANSWERS" onOpen={track}>
        <dl className="grid gap-3 text-sm"><Answer label="Maior risco" value={answerText(answers.largestRisk)}/><Answer label="Onde perdemos dinheiro" value={answerText(answers.whereLosingMoney)}/><Answer label="Onde crescer mais rápido" value={answerText(answers.fastestGrowthOpportunity)}/><Answer label="Decisões imediatas" value={Array.isArray(answers.immediateDecisions) ? `${answers.immediateDecisions.length} decisão(ões) priorizada(s)` : INSUFFICIENT}/></dl>
      </ExecutiveBlock>
    </section>}
    <p className="mt-5 text-center text-sm text-muted-foreground">Resultados permanecem sujeitos à revisão humana. Valor estimado nunca é apresentado como realizado.</p>
  </main>;
}

function ExecutiveBlock({ icon: Icon, title, feature, onOpen, children }: { icon: typeof AlertTriangle; title: string; feature: string; onOpen: (event: string, feature: string, found?: boolean) => Promise<void>; children: React.ReactNode }) {
  return <Card className="min-h-72 shadow-sm"><CardHeader><button className="flex min-h-12 w-full items-center gap-3 text-left text-lg font-semibold" onClick={() => void Promise.all([onOpen("FEATURE_USED", feature), onOpen("INFORMATION_FOUND", feature, true)])}><span className="rounded-lg bg-muted p-2"><Icon size={22}/></span>{title}</button></CardHeader><CardContent>{children}</CardContent></Card>;
}
function InsightList({ items, empty }: { items: Insight[]; empty: string }) { return items.length ? <ol className="space-y-3">{items.map(item => <li key={item.id} className="rounded-lg border p-3"><div className="flex items-start justify-between gap-3"><strong>{item.title}</strong><Badge>{item.confidence}</Badge></div><p className="mt-2 text-sm text-muted-foreground">{item.recommendedAction}</p><p className="mt-2 text-xs">Responsável: {item.suggestedOwner || "A definir por revisão"} · Impacto: {item.estimatedImpactBRL == null ? "não quantificado" : brl(item.estimatedImpactBRL)}</p></li>)}</ol> : <p className="rounded-lg border border-dashed p-4 text-base text-muted-foreground">{empty}</p>; }
function Answer({ label, value }: { label: string; value: string }) { return <div className="border-b pb-2"><dt className="text-muted-foreground">{label}</dt><dd className="mt-1 font-medium">{value}</dd></div>; }
function answerText(value: unknown) { if (!value || typeof value !== "object") return INSUFFICIENT; const item = value as Record<string, unknown>; return String(item.title || item.message || (item.status === "INSUFFICIENT_EQUIVALENT_DATA" ? INSUFFICIENT : INSUFFICIENT)); }
