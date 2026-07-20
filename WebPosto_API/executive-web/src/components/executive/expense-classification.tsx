"use client";

import { useMemo, useState } from "react";
import { Check, CheckCircle2, ChevronLeft, ChevronRight, Search, Sparkles, Undo2 } from "lucide-react";
import { useRouter } from "next/navigation";
import type { ExpenseCategory, ExpenseRow } from "@/lib/treasury";
import { brl, dateBr } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

const CATEGORIES = ["CMV", "INSUMOS OPERACIONAIS", "PESSOAL", "BENEFÍCIOS", "UTILIDADES", "IMPOSTOS E TAXAS", "CONTABILIDADE E FISCAL", "JURÍDICO", "ADMINISTRATIVAS", "TECNOLOGIA", "MANUTENÇÃO", "LOGÍSTICA", "SEGURANÇA", "MARKETING", "TAXAS BANCÁRIAS", "FINANCEIRAS", "SEGUROS", "CAPEX", "OUTRAS DESPESAS"];
const deptValue = (row: ExpenseRow) => row.department === "Combustíveis" ? "combustiveis" : row.department === "Conveniência" ? "conveniencia" : row.department === "Lubrificantes" ? "lubrificantes" : "";

export function ExpenseClassification({ rows, categories }: { rows: ExpenseRow[]; categories: ExpenseCategory[] }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [view, setView] = useState("Revisar");
  const [reviewer, setReviewer] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<ExpenseRow | null>(() => rows.find(row => row.status === "Provável") || rows.find(row => row.status === "Quarentena") || rows[0] || null);
  const [checked, setChecked] = useState<Set<string>>(() => new Set());
  const [processed, setProcessed] = useState<Set<string>>(() => new Set());
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const pageSize = 15;
  const isApplied = (row: ExpenseRow) => row.status === "Comprovada" || processed.has(row.id);
  const filtered = useMemo(() => rows.filter(row => {
    const text = `${row.description} ${row.unit} ${row.category} ${row.department}`.toLowerCase();
    const effectiveConfirmed = row.status === "Comprovada" || processed.has(row.id);
    const stateMatches = view === "Todos" || (view === "Revisar" ? !effectiveConfirmed : effectiveConfirmed);
    return stateMatches && text.includes(query.toLowerCase());
  }), [rows, query, view, processed]);
  const visible = filtered.slice((page - 1) * pageSize, page * pageSize);
  const selectedRows = rows.filter(row => checked.has(row.id));
  const probable = rows.filter(row => row.status === "Provável").length;
  const quarantine = rows.filter(row => row.status === "Quarentena").length;
  const confirmed = rows.filter(isApplied).length;
  const totalValue = rows.reduce((sum, row) => sum + row.value, 0);

  async function post(items: object[]) {
    setSaving(true); setMessage("");
    const response = await fetch("/api/expense-classification?bulk=1", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ items }) });
    setSaving(false); if (response.ok) router.refresh();
    return response.ok;
  }

  async function approve(row: ExpenseRow) {
    if (!reviewer.trim()) { setMessage("Informe o responsável antes de aprovar."); return; }
    if (row.employeeRelated && !row.employeeName) { setSelected(row); setMessage("Informe quem recebeu esta saída antes de confirmar."); return; }
    const department = deptValue(row);
    if (!department) { setSelected(row); setMessage("Escolha um departamento no painel ao lado."); return; }
    const ok = await post([{ factId: row.id, managementAccountCode: row.accountCode, department, category: row.category, subcategory: row.category, reviewer, rationale: "Sugestão automática confirmada", applyToSimilar: Boolean(row.accountCode) }]);
    if (ok) { setProcessed(current => new Set(current).add(row.id)); setSelected(filtered.find(item => item.id !== row.id && !processed.has(item.id)) || null); }
    setMessage(ok ? "Sugestão aprovada. A próxima despesa já foi aberta." : "Não foi possível salvar.");
  }

  async function approveVisible() {
    if (!reviewer.trim()) { setMessage("Informe o responsável antes de aprovar."); return; }
    const suggestions = visible.filter(row => row.status === "Provável" && deptValue(row));
    const items = suggestions.map(row => ({ factId: row.id, managementAccountCode: row.accountCode, department: deptValue(row), category: row.category, subcategory: row.category, reviewer, rationale: "Sugestões da página confirmadas", applyToSimilar: Boolean(row.accountCode) }));
    if (!items.length) { setMessage("Esta página não possui sugestões prontas."); return; }
    const ok = await post(items); if (ok) { setProcessed(current => new Set([...current, ...suggestions.map(row => row.id)])); setSelected(filtered.find(row => !suggestions.some(item => item.id === row.id)) || null); } setMessage(ok ? `${items.length} sugestões aprovadas. A fila foi atualizada.` : "Falha ao aprovar a página.");
  }

  async function saveReview(formData: FormData) {
    if (!selected || !reviewer.trim()) { setMessage("Selecione uma despesa e informe o responsável."); return; }
    const item = { factId: selected.id, managementAccountCode: selected.accountCode, department: formData.get("department"), category: formData.get("category"), subcategory: formData.get("subcategory"), recipientName: formData.get("recipientName"), reviewer, rationale: formData.get("rationale"), applyToSimilar: Boolean(selected.accountCode) && formData.get("similar") === "on" };
    const ok = await post([item]); if (ok) { setProcessed(current => new Set(current).add(selected.id)); setSelected(filtered.find(row => row.id !== selected.id && !processed.has(row.id)) || null); } setMessage(ok ? "Classificação salva. A próxima despesa já foi aberta." : "Não foi possível salvar.");
  }

  async function saveBulk(formData: FormData) {
    if (!reviewer.trim()) { setMessage("Informe o responsável antes de aplicar o lote."); return; }
    const items = selectedRows.map(row => ({ factId: row.id, managementAccountCode: row.accountCode, department: formData.get("department"), category: formData.get("category"), subcategory: formData.get("subcategory"), reviewer, rationale: "Alteração em lote pela diretoria", applyToSimilar: Boolean(row.accountCode) && formData.get("similar") === "on" }));
    const ok = await post(items); setMessage(ok ? `${items.length} despesas alteradas e retiradas da fila.` : "Falha na alteração em lote."); if (ok) { setProcessed(current => new Set([...current, ...selectedRows.map(row => row.id)])); setChecked(new Set()); }
  }

  async function undo() {
    if (!selected) return;
    setSaving(true); const response = await fetch(`/api/expense-classification?factId=${encodeURIComponent(selected.id)}&accountCode=${encodeURIComponent(selected.accountCode)}`, { method: "DELETE" });
    setSaving(false); setMessage(response.ok ? "Classificação desfeita." : "Não foi possível desfazer."); router.refresh();
  }

  return <div>
    <div className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Metric label="Sugestões prontas" value={String(probable)} tone="blue"/><Metric label="Exceções" value={String(quarantine)} tone="amber"/><Metric label="Confirmadas" value={String(confirmed)} tone="green"/><Metric label="Valor analisado" value={brl(totalValue)} tone="slate"/>
    </div>
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-card p-3 shadow-sm">
      <div className="flex flex-wrap gap-2"><div className="relative"><Search className="absolute left-3 top-2.5 text-muted-foreground" size={16}/><input value={query} onChange={event => { setQuery(event.target.value); setPage(1); }} placeholder="Buscar despesa" className="h-9 w-64 rounded-md border bg-background pl-9 pr-3 text-sm"/></div>{["Revisar", "Confirmadas", "Todos"].map(item => <button key={item} onClick={() => { setView(item); setPage(1); }} className={view === item ? "rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground" : "rounded-md px-3 text-xs font-medium text-muted-foreground hover:bg-muted"}>{item}</button>)}</div>
      <div className="flex flex-wrap items-center gap-2"><label className="text-xs text-muted-foreground">Responsável</label><input value={reviewer} onChange={event => setReviewer(event.target.value)} placeholder="Digite seu nome uma vez" className="h-9 w-52 rounded-md border bg-background px-3 text-sm"/><button onClick={approveVisible} disabled={saving} className="flex h-9 items-center gap-2 rounded-md bg-blue-600 px-3 text-xs font-semibold text-white disabled:opacity-50"><Sparkles size={14}/> Aprovar sugestões da página</button></div>
    </div>
    {message && <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-200">{message}</div>}
    {checked.size > 0 && <form action={saveBulk} className="mb-4 flex flex-wrap items-end gap-3 rounded-xl border border-violet-300 bg-violet-50 p-4 dark:border-violet-900 dark:bg-violet-950/30"><div className="mr-auto"><span className="text-xs font-semibold uppercase text-violet-600">Edição em lote</span><strong className="block">{checked.size} selecionadas</strong></div><SelectDepartment name="department"/><SelectCategory name="category"/><input required name="subcategory" placeholder="Subcategoria" className="h-9 rounded-md border bg-background px-3 text-sm"/><label className="flex h-9 items-center gap-2 text-xs"><input type="checkbox" name="similar" defaultChecked/> Memorizar regras</label><button disabled={saving} className="h-9 rounded-md bg-violet-600 px-4 text-sm font-medium text-white">Aplicar ao lote</button><button type="button" onClick={() => setChecked(new Set())} className="h-9 px-2 text-xs">Cancelar</button></form>}
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1.55fr)_minmax(340px,.75fr)]">
      <section className="overflow-hidden rounded-xl border bg-card"><div className="flex items-center justify-between border-b px-4 py-3"><div><h3 className="text-sm font-semibold">Fila de revisão</h3><p className="text-xs text-muted-foreground">{filtered.length} despesas · sugestões aparecem primeiro</p></div><label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={visible.length > 0 && visible.every(row => checked.has(row.id))} onChange={event => setChecked(current => { const next = new Set(current); visible.forEach(row => { if (event.target.checked) next.add(row.id); else next.delete(row.id); }); return next; })}/> Selecionar página</label></div>
        <div className="divide-y">{visible.map(row => { const applied = isApplied(row); return <article key={row.id} className={applied ? "grid grid-cols-[auto_1fr_auto] gap-3 border-l-4 border-l-emerald-500 bg-emerald-50/80 p-4 dark:bg-emerald-950/25" : selected?.id === row.id ? "grid grid-cols-[auto_1fr_auto] gap-3 bg-blue-50/60 p-4 dark:bg-blue-950/20" : "grid grid-cols-[auto_1fr_auto] gap-3 p-4 hover:bg-muted/30"}><input type="checkbox" className="mt-1" checked={checked.has(row.id)} onChange={event => setChecked(current => { const next = new Set(current); if (event.target.checked) next.add(row.id); else next.delete(row.id); return next; })}/><button className="min-w-0 text-left" onClick={() => { setSelected(row); setMessage(""); }}><div className="flex flex-wrap items-center gap-2"><strong className="truncate text-sm">{row.description}</strong><Status status={row.status} applied={applied}/></div><p className="mt-1 text-xs text-muted-foreground">{row.unit} · {dateBr(row.date)} · {row.source}</p>{row.employeeRelated && <p className={row.employeeName ? "mt-1 text-xs font-semibold text-violet-700 dark:text-violet-300" : "mt-1 text-xs font-semibold text-red-600"}>Recebedor: {row.employeeName || "Funcionário não identificado pelo ERP"}{row.employeeCode ? ` · código ${row.employeeCode}` : ""}</p>}<div className="mt-2 flex flex-wrap gap-2"><Badge>{row.category}</Badge><Badge className="bg-blue-500/10 text-blue-700">{row.department}</Badge>{applied && <Badge className="gap-1 border-emerald-300 bg-emerald-100 text-emerald-800"><CheckCircle2 size={11}/> Aplicado</Badge>}</div></button><div className="text-right"><strong className={applied ? "font-mono text-sm text-emerald-700 dark:text-emerald-300" : "font-mono text-sm"}>{brl(row.value)}</strong>{row.status === "Provável" && !applied && <button onClick={() => approve(row)} className="mt-2 flex items-center gap-1 rounded-md bg-emerald-600 px-2.5 py-1.5 text-xs font-semibold text-white"><Check size={13}/> Aprovar</button>}</div></article>})}</div>
        {!visible.length && <div className="grid h-40 place-items-center text-sm text-muted-foreground">Nenhuma despesa nesta fila.</div>}
        <div className="flex items-center justify-between border-t p-3 text-xs text-muted-foreground"><span>Página {page} de {Math.max(1, Math.ceil(filtered.length / pageSize))}</span><div className="flex gap-2"><button disabled={page === 1} onClick={() => setPage(value => value - 1)} className="rounded border p-2 disabled:opacity-30"><ChevronLeft size={14}/></button><button disabled={page * pageSize >= filtered.length} onClick={() => setPage(value => value + 1)} className="rounded border p-2 disabled:opacity-30"><ChevronRight size={14}/></button></div></div>
      </section>
      <aside className="self-start rounded-xl border bg-card p-5 shadow-sm xl:sticky xl:top-5">{selected ? <form key={selected.id} action={saveReview}><div className="flex items-start justify-between"><div><span className="text-xs font-semibold uppercase tracking-wide text-blue-600">Dados do ERP + decisão</span><h3 className="mt-1 font-semibold">{selected.description}</h3><p className="mt-1 text-xs text-muted-foreground">{selected.unit} · {brl(selected.value)} · plano {selected.accountCode || "não informado"}</p>{selected.employeeRelated && <div className={selected.employeeName ? "mt-3 rounded-lg border border-violet-200 bg-violet-50 p-3 text-sm dark:border-violet-900 dark:bg-violet-950/30" : "mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30"}><span className="block text-[10px] font-semibold uppercase tracking-wide">Quem recebeu</span><strong>{selected.employeeName || "Funcionário não identificado pelo ERP"}</strong>{selected.employeeCode && <span className="ml-2 text-xs">Código {selected.employeeCode}</span>}</div>}<p className="mt-2 text-[11px] text-muted-foreground">Origem: {selected.source}. Os campos abaixo já vêm preenchidos; altere somente se necessário.</p></div>{selected.status === "Comprovada" && <button type="button" onClick={undo} className="flex items-center gap-1 text-xs"><Undo2 size={13}/> Desfazer</button>}</div><div className="mt-5 grid gap-3">{selected.employeeRelated && <label className="grid gap-1 text-xs font-medium">Quem recebeu<input required name="recipientName" defaultValue={selected.employeeName} placeholder="Nome do funcionário" className="h-10 rounded-md border border-violet-300 bg-background px-3 text-sm"/></label>}<label className="grid gap-1 text-xs font-medium">Departamento<SelectDepartment name="department" value={deptValue(selected)}/></label><label className="grid gap-1 text-xs font-medium">Categoria do ERP<SelectCategory name="category" value={selected.category}/></label><label className="grid gap-1 text-xs font-medium">Subcategoria<input required name="subcategory" defaultValue={selected.category} className="h-10 rounded-md border bg-background px-3 text-sm"/></label><label className="grid gap-1 text-xs font-medium">Justificativa<input required name="rationale" defaultValue={selected.status === "Provável" ? "Sugestão do sistema confirmada" : "Classificação revisada pela diretoria"} className="h-10 rounded-md border bg-background px-3 text-sm"/></label><label className="flex items-center gap-2 text-xs"><input type="checkbox" name="similar" defaultChecked={Boolean(selected.accountCode)} disabled={!selected.accountCode}/> {selected.accountCode ? "Aplicar automaticamente às semelhantes" : "ERP não informou plano para criar regra"}</label><button disabled={saving || !reviewer.trim()} className="mt-2 h-11 rounded-md bg-primary text-sm font-semibold text-primary-foreground disabled:opacity-40">{selected.status === "Provável" ? "Confirmar dados do ERP" : "Salvar alteração"}</button>{!reviewer.trim() && <p className="text-center text-xs text-amber-600">Informe o responsável no topo para liberar.</p>}</div></form> : <div className="grid h-48 place-items-center text-sm text-muted-foreground">Fila concluída ou selecione uma despesa.</div>}</aside>
    </div>
    <div className="mt-4 flex flex-wrap gap-2 text-xs text-muted-foreground"><span className="font-medium">Principais categorias:</span>{categories.slice(0, 6).map(item => <span key={item.name}>{item.name} {brl(item.value)}</span>)}</div>
  </div>;
}

function Metric({ label, value, tone }: { label: string; value: string; tone: string }) { const colors: Record<string,string> = { blue: "border-blue-200 bg-blue-50/50", amber: "border-amber-200 bg-amber-50/50", green: "border-emerald-200 bg-emerald-50/50", slate: "bg-muted/30" }; return <div className={`rounded-xl border p-4 ${colors[tone]}`}><span className="text-xs text-muted-foreground">{label}</span><strong className="mt-1 block font-mono text-xl">{value}</strong></div>; }
function Status({ status, applied = false }: { status: ExpenseRow["status"]; applied?: boolean }) { return <span className={applied ? "rounded-full bg-emerald-600 px-2 py-0.5 text-[10px] font-semibold text-white" : status === "Provável" ? "rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-700" : "rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-700"}>{applied ? "APLICADO" : status}</span>; }
function SelectDepartment({ name, value = "" }: { name: string; value?: string }) { return <select required name={name} defaultValue={value} className="h-10 rounded-md border bg-background px-3 text-sm"><option value="" disabled>Selecione</option><option value="combustiveis">Combustíveis</option><option value="conveniencia">Conveniência</option><option value="lubrificantes">Lubrificantes</option></select>; }
function SelectCategory({ name, value = "" }: { name: string; value?: string }) { return <select required name={name} defaultValue={value} className="h-10 rounded-md border bg-background px-3 text-sm">{value && !CATEGORIES.includes(value) && <option>{value}</option>}<option value="" disabled>Selecione</option>{CATEGORIES.map(item => <option key={item}>{item}</option>)}</select>; }
