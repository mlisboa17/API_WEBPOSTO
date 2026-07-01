"use client";

import { useEffect, useMemo, useState } from "react";
import { z } from "zod";
import {
  AlertTriangleIcon,
  BanknoteIcon,
  CalendarIcon,
  CheckCircle2Icon,
  CircleDollarSignIcon,
  ClipboardCheckIcon,
  CreditCardIcon,
  LandmarkIcon,
  ReceiptTextIcon,
  ShieldAlertIcon,
  TrendingUpIcon,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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
import { fmtBRL } from "@/lib/format";
import { cn } from "@/lib/utils";

const paymentModes = [
  "Dinheiro",
  "PIX",
  "Cartao Debito",
  "Cartao Credito",
  "Frotistas/Prazo",
] as const;

const cashRegisterSchema = z.object({
  id: z.string(),
  unidade: z.enum(["Real", "Casa Caiada", "VIP"]),
  data: z.string(),
  caixa: z.enum(["Pista", "Conveniencia", "Restaurante"]),
  operador: z.string(),
  status: z.enum(["Aberto", "Fechado", "Consolidado"]),
  vendasBrutas: z.number().nonnegative(),
  despesas: z.number().nonnegative(),
  saldoEspecie: z.number().nonnegative(),
  pagamentos: z.array(
    z.object({
      modalidade: z.enum(paymentModes),
      valorSistema: z.number().nonnegative(),
      valorInformado: z.number().nonnegative(),
    }),
  ),
});

const expenseSchema = z.object({
  id: z.string(),
  unidade: z.enum(["Real", "Casa Caiada", "VIP"]),
  data: z.string(),
  horario: z.string(),
  categoria: z.string().nullable(),
  valor: z.number().nonnegative(),
  operador: z.string(),
  temAnexo: z.boolean(),
  justificativa: z.string().nullable(),
});

const auditDatasetSchema = z.object({
  caixas: z.array(cashRegisterSchema),
  despesas: z.array(expenseSchema),
  source: z.string().optional(),
  lastUpdated: z.string().optional(),
  error: z.string().optional(),
});

type CashRegister = z.infer<typeof cashRegisterSchema>;
type Expense = z.infer<typeof expenseSchema>;
type UnitFilter = "Todas" | CashRegister["unidade"];
type AuditDataset = z.infer<typeof auditDatasetSchema>;

const emptyDataset: AuditDataset = {
  source: "aguardando-api",
  caixas: [],
  despesas: [],
};

const units: UnitFilter[] = ["Todas", "Real", "Casa Caiada", "VIP"];

function todaySaoPaulo() {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Sao_Paulo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

function total(values: number[]) {
  return values.reduce((sum, value) => sum + value, 0);
}

function difference(systemValue: number, informedValue: number) {
  return informedValue - systemValue;
}

function getRegisterBreak(register: CashRegister) {
  return total(
    register.pagamentos.map((payment) =>
      Math.abs(difference(payment.valorSistema, payment.valorInformado)),
    ),
  );
}

function getPaymentRows(registers: CashRegister[]) {
  return paymentModes.map((mode) => {
    const payments = registers.flatMap((register) =>
      register.pagamentos.filter((payment) => payment.modalidade === mode),
    );
    const valorSistema = total(payments.map((payment) => payment.valorSistema));
    const valorInformado = total(payments.map((payment) => payment.valorInformado));

    return {
      modalidade: mode,
      valorSistema,
      valorInformado,
      diferenca: difference(valorSistema, valorInformado),
    };
  });
}

function getInsights(registers: CashRegister[], error?: string) {
  if (error) {
    return [
      {
        tone: "warning" as const,
        text: `API webPosto indisponivel: ${error}`,
      },
    ];
  }

  if (registers.length === 0) {
    return [
      {
        tone: "warning" as const,
        text: "Sem registros reais de caixa para o filtro atual. Nenhuma inferencia foi gerada.",
      },
    ];
  }

  const byUnit = units
    .filter((unit): unit is CashRegister["unidade"] => unit !== "Todas")
    .map((unit) => {
      const unitRegisters = registers.filter((register) => register.unidade === unit);
      const revenue = total(unitRegisters.map((register) => register.vendasBrutas));
      const expenses = total(unitRegisters.map((register) => register.despesas));
      return {
        unit,
        revenue,
        expenses,
        expenseRate: revenue > 0 ? expenses / revenue : 0,
      };
    })
    .filter((item) => item.revenue > 0);

  const insights = byUnit.flatMap((item) => {
    const unitInsights: { tone: "critical" | "warning" | "ok"; text: string }[] = [];
    if (item.expenseRate > 0.05) {
      unitInsights.push({
        tone: item.expenseRate > 0.07 ? "critical" : "warning",
        text: `${item.unit}: despesas em ${(item.expenseRate * 100).toFixed(1)}% do faturamento, acima do padrao historico de 5%.`,
      });
    }
    return unitInsights;
  });

  const vip = byUnit.find((item) => item.unit === "VIP");
  const others = byUnit.filter((item) => item.unit !== "VIP");
  const otherAverage =
    others.length > 0 ? total(others.map((item) => item.expenseRate)) / others.length : 0;

  if (vip && otherAverage > 0 && vip.expenseRate > otherAverage * 1.3) {
    insights.unshift({
      tone: "critical",
      text: `VIP teve ${(((vip.expenseRate / otherAverage) - 1) * 100).toFixed(0)}% mais despesas de caixa que a media das outras unidades.`,
    });
  }

  if (insights.length === 0) {
    insights.push({
      tone: "ok",
      text: "Dados reais carregados sem distorcao acima das regras configuradas.",
    });
  }

  return insights;
}

function toneClasses(tone: "critical" | "warning" | "ok") {
  if (tone === "critical") {
    return "border-red-500/40 bg-red-950/30 text-red-100";
  }
  if (tone === "warning") {
    return "border-orange-500/40 bg-orange-950/30 text-orange-100";
  }
  return "border-emerald-500/40 bg-emerald-950/20 text-emerald-100";
}

function statusBadge(status: CashRegister["status"]) {
  if (status === "Aberto") {
    return <Badge className="bg-orange-500/15 text-orange-200">Aberto</Badge>;
  }
  if (status === "Fechado") {
    return <Badge className="bg-cyan-500/15 text-cyan-200">Fechado</Badge>;
  }
  return <Badge className="bg-emerald-500/15 text-emerald-200">Consolidado</Badge>;
}

function KpiCard({
  title,
  value,
  detail,
  icon: Icon,
  tone = "default",
}: {
  title: string;
  value: string;
  detail: string;
  icon: React.ComponentType<{ className?: string }>;
  tone?: "default" | "cash" | "risk";
}) {
  return (
    <Card className="omie-card rounded-lg">
      <CardContent className="flex min-h-28 items-center justify-between gap-4 p-4">
        <div className="min-w-0">
          <p className="text-xs font-medium text-muted-foreground">{title}</p>
          <p className="mt-2 truncate font-mono text-2xl font-semibold text-white">{value}</p>
          <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
        </div>
        <div
          className={cn(
            "flex size-11 shrink-0 items-center justify-center rounded-lg border",
            tone === "cash" && "border-emerald-400/30 bg-emerald-500/10 text-emerald-200",
            tone === "risk" && "border-red-400/30 bg-red-500/10 text-red-200",
            tone === "default" && "border-cyan-400/30 bg-cyan-500/10 text-cyan-200",
          )}
        >
          <Icon className="size-5" />
        </div>
      </CardContent>
    </Card>
  );
}

function EmptyRow({ colSpan, text }: { colSpan: number; text: string }) {
  return (
    <TableRow>
      <TableCell colSpan={colSpan} className="h-24 text-center text-muted-foreground">
        {text}
      </TableCell>
    </TableRow>
  );
}

export function AuditoriaDashboard() {
  const [unit, setUnit] = useState<UnitFilter>("Todas");
  const [date, setDate] = useState(todaySaoPaulo);
  const [dataset, setDataset] = useState<AuditDataset>(emptyDataset);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    async function loadAuditData() {
      setLoading(true);
      try {
        const params = new URLSearchParams({ data: date, unidade: unit });
        const response = await fetch(`/api/auditoria?${params.toString()}`, {
          cache: "no-store",
          signal: controller.signal,
        });
        const parsed = auditDatasetSchema.safeParse(await response.json());
        setDataset(
          parsed.success
            ? parsed.data
            : {
                ...emptyDataset,
                source: "resposta-invalida",
                error: "Formato retornado pela API nao passou na validacao do dashboard.",
              },
        );
      } catch (error) {
        if ((error as Error).name !== "AbortError") {
          setDataset({
            ...emptyDataset,
            source: "falha-fetch",
            error: error instanceof Error ? error.message : "Falha ao consultar dados reais.",
          });
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadAuditData();
    return () => controller.abort();
  }, [date, unit]);

  const registers = useMemo(
    () =>
      dataset.caixas.filter(
        (register) =>
          register.data === date && (unit === "Todas" || register.unidade === unit),
      ),
    [dataset.caixas, date, unit],
  );

  const expenses = useMemo(
    () =>
      dataset.despesas.filter(
        (expense) => expense.data === date && (unit === "Todas" || expense.unidade === unit),
      ),
    [dataset.despesas, date, unit],
  );

  const revenue = total(registers.map((register) => register.vendasBrutas));
  const operationalExpenses = total(registers.map((register) => register.despesas));
  const cashBalance = total(registers.map((register) => register.saldoEspecie));
  const breakTotal = total(registers.map(getRegisterBreak));
  const paymentRows = getPaymentRows(registers);
  const insights = getInsights(registers, dataset.error);
  const openRegisters = registers.filter((register) => register.status !== "Consolidado").length;

  return (
    <div className="space-y-4 p-4 lg:p-6">
      <section className="flex flex-col gap-3 rounded-lg border border-border bg-card/70 p-4 md:flex-row md:items-center md:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-sm font-medium text-cyan-200">
            <ClipboardCheckIcon className="size-4" />
            Logos Auditoria
          </div>
          <h1 className="mt-1 text-xl font-semibold text-white">
            Conferencia de caixas WebPosto
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Pista, conveniencia e restaurante consolidados apenas com dados reais.
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            Origem:{" "}
            <span className="font-mono text-cyan-200">
              {loading ? "sincronizando..." : dataset.source ?? "api"}
            </span>
            {dataset.lastUpdated ? ` - ${dataset.lastUpdated}` : ""}
          </p>
        </div>
        <div className="grid gap-2 sm:grid-cols-[180px_170px]">
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Unidade</label>
            <Select
              value={unit}
              onValueChange={(value: UnitFilter | null) => {
                if (value) {
                  setUnit(value);
                }
              }}
            >
              <SelectTrigger className="h-9 w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {units.map((unitName) => (
                  <SelectItem key={unitName} value={unitName}>
                    {unitName}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Data</label>
            <div className="relative">
              <CalendarIcon className="pointer-events-none absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
              <Input
                type="date"
                value={date}
                onChange={(event) => setDate(event.target.value)}
                className="h-9 pl-8"
              />
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          title="Faturamento Total"
          value={fmtBRL(revenue)}
          detail={`${registers.length} caixas reais no filtro`}
          icon={TrendingUpIcon}
        />
        <KpiCard
          title="Despesas Operacionais"
          value={fmtBRL(operationalExpenses)}
          detail={`${revenue > 0 ? ((operationalExpenses / revenue) * 100).toFixed(1) : "0.0"}% do faturamento`}
          icon={ReceiptTextIcon}
          tone={operationalExpenses / Math.max(revenue, 1) > 0.05 ? "risk" : "default"}
        />
        <KpiCard
          title="Saldo em Especie"
          value={fmtBRL(cashBalance)}
          detail="Dinheiro fisico esperado"
          icon={BanknoteIcon}
          tone="cash"
        />
        <KpiCard
          title="Quebra Financeira"
          value={fmtBRL(breakTotal)}
          detail={breakTotal > 10 ? "Acima da tolerancia de R$ 10,00" : "Dentro da tolerancia"}
          icon={ShieldAlertIcon}
          tone={breakTotal > 10 ? "risk" : "default"}
        />
      </section>

      <section className="grid gap-4 xl:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          <Card className="omie-card rounded-lg">
            <CardHeader className="flex flex-row items-center justify-between gap-3 pb-2">
              <CardTitle className="flex items-center gap-2 text-base text-white">
                <CircleDollarSignIcon className="size-4 text-cyan-300" />
                Movimentacao por especie
              </CardTitle>
              <Badge variant="outline" className="border-border text-muted-foreground">
                Sistema vs. operador
              </Badge>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Modalidade</TableHead>
                    <TableHead className="text-right">Valor sistemico</TableHead>
                    <TableHead className="text-right">Valor informado</TableHead>
                    <TableHead className="text-right">Diferenca</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {registers.length === 0 ? (
                    <EmptyRow colSpan={4} text="Sem movimentacao real por especie para o filtro atual." />
                  ) : (
                    paymentRows.map((row) => {
                      const hasBreak = Math.abs(row.diferenca) > 10;
                      return (
                        <TableRow key={row.modalidade} className={hasBreak ? "bg-red-950/20" : ""}>
                          <TableCell className="font-medium text-white">{row.modalidade}</TableCell>
                          <TableCell className="text-right font-mono">{fmtBRL(row.valorSistema)}</TableCell>
                          <TableCell className="text-right font-mono">{fmtBRL(row.valorInformado)}</TableCell>
                          <TableCell
                            className={cn(
                              "text-right font-mono font-semibold",
                              hasBreak ? "text-red-200" : "text-emerald-200",
                            )}
                          >
                            {fmtBRL(row.diferenca)}
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card className="omie-card rounded-lg">
            <CardHeader className="flex flex-row items-center justify-between gap-3 pb-2">
              <CardTitle className="flex items-center gap-2 text-base text-white">
                <LandmarkIcon className="size-4 text-cyan-300" />
                Fechamento de turno
              </CardTitle>
              <Badge className={openRegisters > 0 ? "bg-orange-500/15 text-orange-200" : "bg-emerald-500/15 text-emerald-200"}>
                {openRegisters} pendentes
              </Badge>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Unidade</TableHead>
                    <TableHead>Caixa</TableHead>
                    <TableHead>Operador</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Quebra</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {registers.length === 0 ? (
                    <EmptyRow colSpan={5} text="Sem fechamentos reais carregados." />
                  ) : (
                    registers.map((register) => {
                      const registerBreak = getRegisterBreak(register);
                      return (
                        <TableRow
                          key={register.id}
                          className={cn(
                            register.status !== "Consolidado" && "bg-orange-950/20",
                            registerBreak > 10 && "bg-red-950/30",
                          )}
                        >
                          <TableCell className="font-medium text-white">{register.unidade}</TableCell>
                          <TableCell>{register.caixa}</TableCell>
                          <TableCell>{register.operador}</TableCell>
                          <TableCell>{statusBadge(register.status)}</TableCell>
                          <TableCell
                            className={cn(
                              "text-right font-mono font-semibold",
                              registerBreak > 10 ? "text-red-200" : "text-emerald-200",
                            )}
                          >
                            {fmtBRL(registerBreak)}
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card className="omie-card rounded-lg">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base text-white">
                <CreditCardIcon className="size-4 text-cyan-300" />
                Auditoria de despesas
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Horario</TableHead>
                    <TableHead>Categoria</TableHead>
                    <TableHead className="text-right">Valor</TableHead>
                    <TableHead>Operador</TableHead>
                    <TableHead>Status de justificativa</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {expenses.length === 0 ? (
                    <EmptyRow colSpan={5} text="Sem despesas reais para auditar no filtro atual." />
                  ) : (
                    expenses.map((expense: Expense) => {
                      const irregular = !expense.categoria || !expense.temAnexo;
                      return (
                        <TableRow key={expense.id} className={irregular ? "bg-red-950/30" : ""}>
                          <TableCell className="font-mono">{expense.horario}</TableCell>
                          <TableCell className="font-medium text-white">
                            {expense.categoria ?? "Sem categoria"}
                          </TableCell>
                          <TableCell className="text-right font-mono">{fmtBRL(expense.valor)}</TableCell>
                          <TableCell>{expense.operador}</TableCell>
                          <TableCell>
                            {irregular ? (
                              <Badge className="bg-red-500/15 text-red-200">
                                Falta categoria ou anexo
                              </Badge>
                            ) : (
                              <Badge className="bg-emerald-500/15 text-emerald-200">
                                Justificada
                              </Badge>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>

        <aside className="space-y-4">
          <Card className="omie-card rounded-lg">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base text-white">
                <AlertTriangleIcon className="size-4 text-orange-300" />
                Insights do Auditor
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {insights.map((insight, index) => (
                <div
                  key={`${insight.tone}-${index}`}
                  className={cn("rounded-lg border p-3 text-sm leading-5", toneClasses(insight.tone))}
                >
                  {insight.text}
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="omie-card rounded-lg">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base text-white">
                <CheckCircle2Icon className="size-4 text-emerald-300" />
                Regra operacional
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <div className="flex items-center justify-between border-b border-border pb-2">
                <span>Limite despesas/receita</span>
                <span className="font-mono text-white">5,0%</span>
              </div>
              <div className="flex items-center justify-between border-b border-border pb-2">
                <span>Tolerancia de quebra</span>
                <span className="font-mono text-white">R$ 10,00</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Fonte de dados</span>
                <span className="font-mono text-white">API webPosto</span>
              </div>
            </CardContent>
          </Card>
        </aside>
      </section>
    </div>
  );
}
