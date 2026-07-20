"use client";

import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp, CreditCard, Info, Search, TriangleAlert, WalletCards } from "lucide-react";
import type { CardAdministratorSummary, CardCatalogSummary } from "@/lib/treasury";
import { brl, dateBr } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

const METHOD_LABELS: Record<string, string> = {
  CREDITO: "Crédito",
  DEBITO: "Débito",
  PREMMIA: "Premmia",
  PIX_TRANSFERENCIA: "PIX/Transferência",
  NAO_IDENTIFICADO: "Não identificado",
};

const METHOD_ORDER = ["CREDITO", "DEBITO", "PREMMIA", "PIX_TRANSFERENCIA", "NAO_IDENTIFICADO"];

export function CardCatalog({ data }: { data: CardCatalogSummary }) {
  const [query, setQuery] = useState(""); const [methodFilter, setMethodFilter] = useState("all"); const [companyFilter, setCompanyFilter] = useState("all");
  const [sort, setSort] = useState<keyof CardAdministratorSummary>("date"); const [direction, setDirection] = useState<"asc" | "desc">("desc");
  const filtered = useMemo(() => data.items.filter(item => `${item.company} ${item.name} ${item.method}`.toLowerCase().includes(query.toLowerCase()) && (methodFilter === "all" || item.method === methodFilter) && (companyFilter === "all" || item.company === companyFilter)).sort((a, b) => { const left = a[sort]; const right = b[sort]; const compared = typeof left === "number" && typeof right === "number" ? left - right : String(left).localeCompare(String(right), "pt-BR"); return direction === "asc" ? compared : -compared; }), [data.items, query, methodFilter, companyFilter, sort, direction]);
  const filteredGross = filtered.reduce((sum, item) => sum + item.gross, 0); const filteredFee = filtered.reduce((sum, item) => sum + item.fee, 0); const filteredNet = filtered.reduce((sum, item) => sum + item.expectedNet, 0); const filteredRecords = filtered.reduce((sum, item) => sum + item.records, 0);
  const companies = [...new Set(data.items.map(item => item.company))].sort();
  function toggleSort(field: keyof CardAdministratorSummary) { if (sort === field) setDirection(value => value === "asc" ? "desc" : "asc"); else { setSort(field); setDirection("asc"); } }
  const totals = new Map<string, number>();
  for (const item of data.items) totals.set(item.method, (totals.get(item.method) || 0) + item.gross);

  return <Card className="mt-5">
    <CardHeader>
      <div>
        <div className="flex items-center gap-2"><WalletCards size={18}/><h2 className="font-semibold">Cartões e carteiras digitais</h2></div>
        <p className="mt-1 text-xs text-muted-foreground">Formas de recebimento mapeadas pelo cadastro oficial de administradoras do WebPosto.</p>
      </div>
      <Badge>{data.items.reduce((sum, item) => sum + item.records, 0)} lançamentos</Badge>
    </CardHeader>
    <CardContent>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {METHOD_ORDER.map(method => <div key={method} className={method === "NAO_IDENTIFICADO" && (totals.get(method) || 0) > 0 ? "rounded-lg border border-amber-300 bg-amber-50/70 p-3 dark:bg-amber-950/20" : "rounded-lg border bg-muted/20 p-3"}>
          <span className="text-xs text-muted-foreground">{METHOD_LABELS[method]}</span>
          <strong className="mt-1 block font-mono text-sm">{brl(totals.get(method) || 0)}</strong>
        </div>)}
      </div>

      {data.premiaConfigured.length > 0 && <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50/60 p-3 dark:bg-blue-950/20">
        <div className="flex items-center gap-2 text-sm font-medium"><CreditCard size={16} className="text-blue-600"/> Premmia identificado no ERP</div>
        <div className="mt-2 flex flex-wrap gap-1.5">{data.premiaConfigured.map(item => <Badge key={`${item.company}-${item.code}`} className="bg-blue-500/10 text-blue-700 dark:text-blue-300">{item.company}: {item.name}{item.type ? ` · ${item.type}` : ""}</Badge>)}</div>
      </div>}

      <div className="mt-4 flex flex-wrap gap-2 rounded-lg border bg-muted/15 p-3"><label className="relative"><Search className="absolute left-3 top-2.5 text-muted-foreground" size={15}/><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Buscar administradora" className="h-9 w-64 rounded-md border bg-background pl-9 pr-3 text-sm"/></label><select value={methodFilter} onChange={event => setMethodFilter(event.target.value)} className="h-9 rounded-md border bg-background px-2 text-sm"><option value="all">Todas as modalidades</option>{METHOD_ORDER.map(method => <option key={method} value={method}>{METHOD_LABELS[method]}</option>)}</select><select value={companyFilter} onChange={event => setCompanyFilter(event.target.value)} className="h-9 rounded-md border bg-background px-2 text-sm"><option value="all">Todas as unidades</option>{companies.map(company => <option key={company}>{company}</option>)}</select></div>
      {data.items.length ? <div className="mt-3 overflow-x-auto rounded-lg border">
        <table className="w-full min-w-[900px] text-left text-sm">
          <thead className="bg-muted/60 text-xs text-muted-foreground"><tr><CardSort label="Unidade" field="company" active={sort} direction={direction} toggle={toggleSort}/><CardSort label="Administradora" field="name" active={sort} direction={direction} toggle={toggleSort}/><CardSort label="Modalidade" field="method" active={sort} direction={direction} toggle={toggleSort}/><CardSort label="Bruto" field="gross" active={sort} direction={direction} toggle={toggleSort} right/><CardSort label="Taxa estimada" field="fee" active={sort} direction={direction} toggle={toggleSort} right/><CardSort label="Líquido esperado" field="expectedNet" active={sort} direction={direction} toggle={toggleSort} right/><CardSort label="Registros" field="records" active={sort} direction={direction} toggle={toggleSort} right/></tr></thead>
          <tbody>{filtered.map(item => <tr key={`${item.company}-${item.date}-${item.code}-${item.method}`} className={item.method === "NAO_IDENTIFICADO" ? "border-t bg-amber-50/60 dark:bg-amber-950/20" : "border-t"}>
            <td className="px-3 py-2.5 font-medium">{item.company}<span className="mt-0.5 block font-mono text-[11px] text-muted-foreground">{item.date ? dateBr(item.date) : "Data não informada"}</span></td><td className="px-3 py-2.5">{item.name}<span className="ml-1 text-xs text-muted-foreground">#{item.code}</span></td>
            <td className="px-3 py-2.5"><Badge>{METHOD_LABELS[item.method] || item.method}</Badge></td><td className="px-3 py-2.5 text-right font-mono">{brl(item.gross)}</td><td className="px-3 py-2.5 text-right font-mono">{brl(item.fee)}</td><td className="px-3 py-2.5 text-right font-mono">{brl(item.expectedNet)}</td><td className="px-3 py-2.5 text-right">{item.records}</td>
          </tr>)}</tbody><tfoot><tr className="border-t-2 bg-muted/40 font-medium"><td colSpan={3} className="px-3 py-3">{filteredRecords} registros · {filtered.length} grupos · Média {brl(filteredRecords ? filteredGross / filteredRecords : 0)}</td><td className="px-3 py-3 text-right font-mono">{brl(filteredGross)}</td><td className="px-3 py-3 text-right font-mono">{brl(filteredFee)}</td><td className="px-3 py-3 text-right font-mono">{brl(filteredNet)}</td><td className="px-3 py-3 text-right">{filteredRecords}</td></tr></tfoot>
        </table>
      </div> : <div className="mt-4 rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">Nenhum movimento de cartão ou carteira retornado no período.</div>}

      <div className="mt-4 grid gap-2 text-xs text-muted-foreground lg:grid-cols-2">
        <p className="flex gap-2 rounded-lg bg-muted/40 p-3"><Info size={15} className="mt-0.5 shrink-0"/> Quando a origem for VENDA_FORMA_PAGAMENTO, o valor representa venda capturada no ERP e não confirma liquidação bancária.</p>
        {(data.unmappedRecords > 0 || data.unavailableCompanies.length > 0) && <p className="flex gap-2 rounded-lg bg-amber-50 p-3 text-amber-800 dark:bg-amber-950/20 dark:text-amber-300"><TriangleAlert size={15} className="mt-0.5 shrink-0"/> {data.unmappedRecords} registro(s) sem administradora identificada. Fontes indisponíveis: {data.unavailableCompanies.join(", ") || "nenhuma"}.</p>}
      </div>
    </CardContent>
  </Card>;
}

function CardSort({ label, field, active, direction, toggle, right = false }: { label: string; field: keyof CardAdministratorSummary; active: keyof CardAdministratorSummary; direction: "asc" | "desc"; toggle: (field: keyof CardAdministratorSummary) => void; right?: boolean }) { return <th className={right ? "px-3 py-2.5 text-right" : "px-3 py-2.5"}><button onClick={() => toggle(field)} className={right ? "ml-auto flex items-center gap-1" : "flex items-center gap-1"}>{label}{active === field && (direction === "asc" ? <ArrowUp size={12}/> : <ArrowDown size={12}/>)}</button></th>; }
