"use client";

import { useEffect, useState } from "react";
import { CalendarClock, ClipboardCheck, Pause, Play, Plus } from "lucide-react";
import type { PeriodicAuditCycle } from "@/lib/treasury";
import { COMPANIES } from "@/lib/treasury";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

type Props = { cycles: PeriodicAuditCycle[]; company: string; start: string; end: string };
type AuditRun = { id: string; empresa_codigo: string; centro_custo: string; data_inicial: string; data_final: string; status: string };
type Result = { evidenceId: string; status: string; reviewed?: boolean; comparisons: { metric: string; pdf: string | null; api: string | null; status: string }[] };
type Integrity = { integrity: string; sha256?: string };
const companyName = (code: string) => COMPANIES.find(item => item.code === code)?.name || `Unidade ${code}`;

export function PeriodicAudits({ cycles: initial, company, end }: Props) {
  const [cycles, setCycles] = useState(initial);
  const [runs, setRuns] = useState<AuditRun[]>([]);
  const [results, setResults] = useState<Record<string, Result>>({});
  const [integrities, setIntegrities] = useState<Record<string, Integrity>>({});
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetch("/api/periodic-audits/runs", { cache: "no-store" }).then(r => r.json())
      .then(p => setRuns(Array.isArray(p.data) ? p.data : [])).catch(() => setRuns([]));
  }, []);

  async function create(form: FormData) {
    setBusy(true);
    const response = await fetch("/api/periodic-audits", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
      empresaCodigo: company, centroCusto: form.get("centroCusto"), periodicidadeDias: Number(form.get("periodicidadeDias")), responsavel: form.get("responsavel"), dataCorte: form.get("dataCorte"),
    }) });
    const payload = await response.json(); setBusy(false);
    if (!response.ok) { setMessage(payload.detail || "Não foi possível criar a rotina."); return; }
    setCycles(current => [...current, payload.data]); setOpen(false);
  }

  async function toggle(cycle: PeriodicAuditCycle) {
    const response = await fetch("/api/periodic-audits", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id: cycle.id, ativo: !cycle.ativo }) });
    const payload = await response.json();
    if (response.ok) setCycles(current => current.map(item => item.id === cycle.id ? payload.data : item));
  }

  async function upload(run: AuditRun, file?: File) {
    if (!file || file.type !== "application/pdf") { setMessage("Selecione um PDF válido."); return; }
    setBusy(true); setMessage("Validando e conciliando o documento...");
    const uploaded = await fetch(`/api/periodic-audits/runs/${encodeURIComponent(run.id)}/pdf`, { method: "POST", headers: { "Content-Type": "application/pdf", "X-Filename": file.name }, body: file });
    const uploadPayload = await uploaded.json();
    if (!uploaded.ok) { setBusy(false); setMessage(uploadPayload.detail || "PDF rejeitado."); return; }
    const response = await fetch(`/api/periodic-audits/runs/${encodeURIComponent(run.id)}/pdf/${encodeURIComponent(uploadPayload.data.id)}/reconcile`, { method: "POST" });
    const payload = await response.json(); setBusy(false);
    if (!response.ok) { setMessage(payload.detail || "Não foi possível conciliar."); return; }
    setResults(current => ({ ...current, [run.id]: { ...payload.data.reconciliation, evidenceId: uploadPayload.data.id } }));
    setMessage("PDF validado. A revisão humana continua obrigatória.");
  }

  async function review(run: AuditRun, result: Result) {
    const justification = window.prompt("Justificativa da revisão documental:");
    if (!justification || justification.trim().length < 3) return;
    const response = await fetch(`/api/periodic-audits/runs/${encodeURIComponent(run.id)}/pdf/${encodeURIComponent(result.evidenceId)}/review`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ justificativa: justification }),
    });
    if (!response.ok) { const payload = await response.json(); setMessage(payload.detail || "Revisão não registrada."); return; }
    setResults(current => ({ ...current, [run.id]: { ...result, reviewed: true } }));
    setMessage("Revisão documental registrada na trilha de auditoria.");
  }

  async function verifyIntegrity(run: AuditRun) {
    setBusy(true);
    const response = await fetch(`/api/periodic-audits/runs/${encodeURIComponent(run.id)}/integrity`, { cache: "no-store" });
    const payload = await response.json();
    setBusy(false);
    const result = response.ok ? payload.data : payload.detail;
    if (!result) { setMessage("Não foi possível verificar o dossiê."); return; }
    setIntegrities(current => ({ ...current, [run.id]: result }));
    setMessage(result.integrity === "VERIFIED" ? "Integridade criptográfica confirmada." : `Integridade: ${result.integrity}.`);
  }

  const visible = company === "all" ? cycles : cycles.filter(item => item.empresa_codigo === company);
  const visibleRuns = company === "all" ? runs : runs.filter(item => item.empresa_codigo === company);
  return <section className="mt-5" aria-label="Auditorias periódicas"><Card className="border-indigo-200/80">
    <CardHeader><div className="flex flex-wrap justify-between gap-3"><div><div className="flex items-center gap-2"><ClipboardCheck size={19}/><h2 className="font-semibold">Auditorias periódicas</h2><Badge>Diretoria</Badge></div><p className="mt-1 text-xs text-muted-foreground">PDF privado, conciliação com a API e revisão humana obrigatória.</p></div>{company !== "all" && <Button onClick={() => setOpen(v => !v)}><Plus size={16}/>{open ? "Cancelar" : "Nova rotina"}</Button>}</div></CardHeader>
    <CardContent>
      {open && <form action={create} className="mb-4 grid gap-3 rounded-lg border p-4 md:grid-cols-4"><select name="centroCusto"><option value="PISTA">Pista</option><option value="CONVENIENCIA">Conveniência</option></select><select name="periodicidadeDias"><option value="7">Semanal</option><option value="15">15 dias</option><option value="30">30 dias</option></select><input required name="responsavel" placeholder="Responsável"/><input required name="dataCorte" type="date" defaultValue={end}/><Button disabled={busy}>Criar rotina</Button></form>}
      {message && <p className="mb-4 rounded-md bg-indigo-500/10 p-3 text-xs">{message}</p>}
      <div className="grid gap-3 lg:grid-cols-2">{visible.map(cycle => <article key={cycle.id} className="rounded-lg border p-4"><div className="flex justify-between"><div><Badge>{cycle.centro_custo}</Badge><h3 className="mt-2 font-semibold">{companyName(cycle.empresa_codigo)}</h3><p className="text-xs text-muted-foreground">{cycle.periodicidade_dias} dias · {cycle.responsavel}</p></div><button onClick={() => toggle(cycle)}>{cycle.ativo ? <Pause size={16}/> : <Play size={16}/>}</button></div><p className="mt-3 flex items-center gap-1 text-xs"><CalendarClock size={14}/>{cycle.proximaAuditoria}</p></article>)}</div>
      <div className="mt-5 space-y-3">{visibleRuns.map(run => <article key={run.id} className="rounded-lg border p-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><strong className="text-sm">{companyName(run.empresa_codigo)} · {run.centro_custo}</strong><p className="text-xs text-muted-foreground">{run.data_inicial} a {run.data_final} · {run.status}</p></div><div className="flex flex-wrap gap-2"><label className="cursor-pointer rounded-md border px-3 py-2 text-xs font-semibold">Anexar PDF<input className="hidden" type="file" accept="application/pdf,.pdf" disabled={busy} onChange={event => upload(run, event.target.files?.[0])}/></label>{run.status === "APROVADO" && <><Button className="bg-transparent text-foreground ring-1 ring-border hover:bg-muted" disabled={busy} onClick={() => verifyIntegrity(run)}>Verificar integridade</Button><a className="rounded-md bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground" href={`/api/periodic-audits/runs/${encodeURIComponent(run.id)}/dossier`}>Baixar dossiê</a></>}</div></div>{integrities[run.id] && <p className="mt-3 rounded-md bg-muted/30 p-3 text-xs"><strong>{integrities[run.id].integrity}</strong>{integrities[run.id]?.sha256 && <> · SHA-256 {integrities[run.id]?.sha256?.slice(0, 16)}…</>}</p>}{results[run.id] && <div className="mt-3 rounded-md bg-muted/30 p-3 text-xs"><strong>Conciliação: {results[run.id].status}</strong>{results[run.id].comparisons.map(item => <p key={item.metric}>{item.metric}: PDF {item.pdf ?? "—"} · API {item.api ?? "indisponível"} · {item.status}</p>)}<Button className="mt-2" disabled={results[run.id].reviewed} onClick={() => review(run, results[run.id])}>{results[run.id].reviewed ? "Revisão registrada" : "Registrar revisão humana"}</Button></div>}</article>)}</div>
    </CardContent>
  </Card></section>;
}
