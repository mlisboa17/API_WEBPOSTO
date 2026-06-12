"use client";

import { useCallback, useMemo, useRef, useState, useTransition } from "react";

import { parseCsvStatementFile } from "@/lib/csv-statement-parser";
import { parseOfxFile } from "@/lib/ofx-parser";
import { importOfxTransactions, toOfxImportPayload } from "@/lib/statements-api";
import { fmtBRL } from "@/lib/format";
import type { ImportFileKind, ParsedStatementTransaction } from "@/types/statements";

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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { FileUpIcon, UploadCloudIcon } from "lucide-react";
import { toast } from "sonner";

const IMPORT_OPTIONS = [
  {
    value: "IMPORTAR_APENAS_DIAS_INEXISTENTES_SISTEMA",
    label: "Importar apenas dias inexistentes",
  },
  { value: "EXCLUIR_DIAS_SISTEMA", label: "Excluir dias existentes e reimportar" },
] as const;

export function StatementsImport() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [fileKind, setFileKind] = useState<ImportFileKind>("ofx");
  const [fileName, setFileName] = useState("");
  const [rows, setRows] = useState<ParsedStatementTransaction[]>([]);
  const [cdConta, setCdConta] = useState("1");
  const [cdFilial, setCdFilial] = useState("11495");
  const [opcaoImportacao, setOpcaoImportacao] = useState<string>(
    IMPORT_OPTIONS[0].value,
  );
  const [pending, startTransition] = useTransition();

  const totalValor = useMemo(
    () => rows.reduce((acc, r) => acc + r.valor, 0),
    [rows],
  );

  const onPickFile = useCallback(() => inputRef.current?.click(), []);

  const onFileChange = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;
      setFileName(file.name);
      try {
        const ext = file.name.split(".").pop()?.toLowerCase();
        const kind: ImportFileKind = ext === "csv" ? "csv" : "ofx";
        setFileKind(kind);
        const parsed =
          kind === "csv" ? await parseCsvStatementFile(file) : await parseOfxFile(file);
        setRows(parsed);
        toast.success(`${parsed.length} transações lidas do ${kind.toUpperCase()}.`);
      } catch (error) {
        setRows([]);
        toast.error(error instanceof Error ? error.message : "Falha ao ler arquivo");
      } finally {
        event.target.value = "";
      }
    },
    [],
  );

  const onImport = useCallback(() => {
    if (rows.length === 0) {
      toast.error("Selecione um arquivo OFX ou CSV válido antes de importar.");
      return;
    }
    const conta = Number.parseInt(cdConta, 10);
    const filial = Number.parseInt(cdFilial, 10);
    if (!Number.isFinite(conta) || !Number.isFinite(filial)) {
      toast.error("Informe conta e filial válidas.");
      return;
    }

    startTransition(async () => {
      try {
        const payload = toOfxImportPayload(rows, {
          cdConta: conta,
          cdFilial: filial,
          opcaoImportacao,
        });
        await importOfxTransactions(payload);
        toast.success(`Importação enviada — ${rows.length} transações.`);
        setRows([]);
        setFileName("");
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Erro na importação");
      }
    });
  }, [rows, cdConta, cdFilial, opcaoImportacao]);

  return (
    <div className="flex flex-col gap-4 p-4 lg:p-6">
      <div>
        <h2 className="text-lg font-semibold tracking-tight">Importação OFX / CSV</h2>
        <p className="text-sm text-muted-foreground">
          Faça upload do extrato, revise as transações e envie para o WebPosto.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Arquivo</CardTitle>
            <CardDescription>Formatos aceitos: .ofx, .csv</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <input
              ref={inputRef}
              type="file"
              accept=".ofx,.OFX,.csv,.CSV,text/csv,application/x-ofx"
              className="hidden"
              onChange={(e) => void onFileChange(e)}
            />
            <Button type="button" variant="outline" className="w-full" onClick={onPickFile}>
              <UploadCloudIcon className="size-4" />
              Selecionar arquivo
            </Button>
            {fileName ? (
              <div className="flex items-center gap-2 text-sm">
                <FileUpIcon className="size-4 text-muted-foreground" />
                <span className="truncate">{fileName}</span>
                <Badge variant="secondary">{fileKind.toUpperCase()}</Badge>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Nenhum arquivo selecionado.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Parâmetros WebPosto</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="cd-conta">Conta (cdConta)</Label>
              <Input id="cd-conta" value={cdConta} onChange={(e) => setCdConta(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="cd-filial">Filial (cdFilial)</Label>
              <Input id="cd-filial" value={cdFilial} onChange={(e) => setCdFilial(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label>Opção de importação</Label>
              <Select
                value={opcaoImportacao}
                onValueChange={(v) => v && setOpcaoImportacao(v)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {IMPORT_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button type="button" onClick={onImport} disabled={pending || rows.length === 0}>
              {pending ? "Importando..." : "Importar para WebPosto"}
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Pré-visualização</CardTitle>
          <CardDescription>
            {rows.length === 0
              ? "Empty state — aguardando arquivo."
              : `${rows.length} transações · total ${fmtBRL(totalValor)}`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {rows.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-10 text-center text-muted-foreground">
              <UploadCloudIcon className="size-10 opacity-40" />
              <p>Envie um OFX ou CSV para visualizar as transações antes de importar.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Data</TableHead>
                  <TableHead>Descrição</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead className="text-right">Valor</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.slice(0, 50).map((row) => (
                  <TableRow key={row.id}>
                    <TableCell>{row.data}</TableCell>
                    <TableCell className="max-w-[360px] truncate" title={row.descricao}>
                      {row.descricao}
                    </TableCell>
                    <TableCell>{row.tipo ?? "—"}</TableCell>
                    <TableCell className="text-right font-medium">{fmtBRL(row.valor)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          {rows.length > 50 ? (
            <p className="mt-2 text-xs text-muted-foreground">
              Exibindo 50 de {rows.length} transações.
            </p>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
