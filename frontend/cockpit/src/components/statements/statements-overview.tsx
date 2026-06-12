"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { fetchBankMovements } from "@/lib/statements-api";
import { presetRange } from "@/lib/datetime-br";
import { fmtBRL } from "@/lib/format";
import type { BankMovement } from "@/types/statements";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { LandmarkIcon, RefreshCwIcon, SearchIcon } from "lucide-react";
import { toast } from "sonner";

function movementKind(row: BankMovement): "entrada" | "saida" | "neutro" {
  const tipo = (row.tipo ?? "").toLowerCase();
  if (tipo.includes("crédito") || tipo.includes("credito")) return "entrada";
  if (tipo.includes("débito") || tipo.includes("debito")) return "saida";
  const v = Number.parseFloat(row.valor);
  if (v > 0) return "entrada";
  if (v < 0) return "saida";
  return "neutro";
}

export function StatementsOverview() {
  const defaultRange = useMemo(() => presetRange("7d"), []);
  const [dataInicial, setDataInicial] = useState(defaultRange.inicio);
  const [dataFinal, setDataFinal] = useState(defaultRange.fim);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [rows, setRows] = useState<BankMovement[]>([]);
  const [total, setTotal] = useState(0);
  const [resumo, setResumo] = useState<Record<string, unknown> | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetchBankMovements({
        dataInicial,
        dataFinal,
        page: 1,
        limit: 100,
      });
      setRows(resp.data ?? []);
      setTotal(resp.total ?? 0);
      setResumo(resp.resumo ?? null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Erro ao carregar extrato");
      setRows([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [dataInicial, dataFinal]);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter(
      (r) =>
        r.descricao?.toLowerCase().includes(q) ||
        String(r.movimentoContaCodigo ?? "").includes(q) ||
        String(r.empresaCodigo ?? "").includes(q),
    );
  }, [rows, search]);

  const creditos = (resumo as { creditos?: { valor?: string } })?.creditos?.valor;
  const debitos = (resumo as { debitos?: { valor?: string } })?.debitos?.valor;

  return (
    <div className="flex flex-col gap-4 p-4 lg:p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Extratos bancários</h2>
          <p className="text-sm text-muted-foreground">
            Movimentos consolidados via Finance Center (MOVIMENTO_CONTA).
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          <RefreshCwIcon className={loading ? "size-4 animate-spin" : "size-4"} />
          Atualizar
        </Button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Registros</CardDescription>
            <CardTitle className="text-2xl">{loading ? "—" : total}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Créditos</CardDescription>
            <CardTitle className="text-2xl text-emerald-600">
              {loading ? "—" : fmtBRL(Number.parseFloat(creditos ?? "0"))}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Débitos</CardDescription>
            <CardTitle className="text-2xl text-rose-600">
              {loading ? "—" : fmtBRL(Number.parseFloat(debitos ?? "0"))}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Período</CardDescription>
            <CardTitle className="text-base font-medium">
              {dataInicial} → {dataFinal}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Filtros</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-3">
          <div className="space-y-1.5">
            <Label htmlFor="stmt-ini">Data inicial</Label>
            <Input
              id="stmt-ini"
              type="date"
              value={dataInicial}
              onChange={(e) => setDataInicial(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="stmt-fim">Data final</Label>
            <Input
              id="stmt-fim"
              type="date"
              value={dataFinal}
              onChange={(e) => setDataFinal(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="stmt-search">Buscar</Label>
            <div className="relative">
              <SearchIcon className="absolute top-2.5 left-2.5 size-4 text-muted-foreground" />
              <Input
                id="stmt-search"
                className="pl-8"
                placeholder="Descrição, código..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Transações</CardTitle>
          <CardDescription>
            {loading ? "Carregando..." : `${filtered.length} de ${rows.length} na página`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-12 text-center text-muted-foreground">
              <LandmarkIcon className="size-10 opacity-40" />
              <p className="font-medium">Nenhuma transação no período</p>
              <p className="text-sm">Ajuste as datas ou importe um arquivo OFX/CSV na aba Importação.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Data</TableHead>
                  <TableHead>Descrição</TableHead>
                  <TableHead>Filial</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead className="text-right">Valor</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((row) => {
                  const kind = movementKind(row);
                  const valor = Number.parseFloat(row.valor);
                  return (
                    <TableRow key={`${row.movimentoContaCodigo}-${row.dataMovimento}-${row.descricao}`}>
                      <TableCell className="whitespace-nowrap">{row.dataMovimento?.slice(0, 10)}</TableCell>
                      <TableCell className="max-w-[320px] truncate" title={row.descricao}>
                        {row.descricao || "—"}
                      </TableCell>
                      <TableCell>{row.empresaCodigo ?? "—"}</TableCell>
                      <TableCell>
                        <Badge variant={kind === "entrada" ? "default" : "secondary"}>
                          {row.tipo || kind}
                        </Badge>
                      </TableCell>
                      <TableCell
                        className={`text-right font-medium ${
                          kind === "entrada" ? "text-emerald-600" : kind === "saida" ? "text-rose-600" : ""
                        }`}
                      >
                        {fmtBRL(Math.abs(valor))}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
