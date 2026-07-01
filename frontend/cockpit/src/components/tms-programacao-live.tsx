"use client";

import { useMemo, useState } from "react";
import {
  AlertTriangleIcon,
  CheckCircle2Icon,
  Clock3Icon,
  FileTextIcon,
  FuelIcon,
  MapPinIcon,
  QrCodeIcon,
  RefreshCwIcon,
  RouteIcon,
  SaveIcon,
  ShieldCheckIcon,
  TruckIcon,
  XIcon,
} from "lucide-react";
import { toast } from "sonner";

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
import { cn } from "@/lib/utils";
import { validarProgramacaoTms } from "@/lib/tms-api";
import type {
  StatusCompartimento,
  TmsAlerta,
  TmsCompartimento,
  TmsPosto,
  TmsProgramacao,
  TmsTanque,
  TmsValidacaoResultado,
} from "@/types/tms";

const PRODUTOS = [
  { id: "11111111-1111-4111-8111-111111111111", nome: "Diesel S10" },
  { id: "22222222-2222-4222-8222-222222222222", nome: "Diesel Aditivado" },
  { id: "33333333-3333-4333-8333-333333333333", nome: "Gasolina Comum" },
  { id: "44444444-4444-4444-8444-444444444444", nome: "Gasolina Aditivada" },
  { id: "55555555-5555-4555-8555-555555555555", nome: "Etanol" },
  { id: "66666666-6666-4666-8666-666666666666", nome: "Etanol Aditivado" },
  { id: "77777777-7777-4777-8777-777777777777", nome: "Gasolina Podium" },
];

const POSTOS: TmsPosto[] = [
  {
    id: "aaaaaaaa-0001-4000-8000-000000000001",
    nome: "Posto Real",
    latitude: -7.834,
    longitude: -34.91,
    raio_checkin_metros: 300,
  },
  {
    id: "aaaaaaaa-0002-4000-8000-000000000002",
    nome: "Casa Caiada",
    latitude: -7.99,
    longitude: -34.84,
    raio_checkin_metros: 300,
  },
  {
    id: "aaaaaaaa-0003-4000-8000-000000000003",
    nome: "Posto VIP",
    latitude: -7.85,
    longitude: -34.9,
    raio_checkin_metros: 300,
  },
  {
    id: "aaaaaaaa-0004-4000-8000-000000000004",
    nome: "Igarassu Centro",
    latitude: -7.83,
    longitude: -34.9,
    raio_checkin_metros: 300,
  },
];

const TANQUES: TmsTanque[] = POSTOS.flatMap((posto, postoIndex) =>
  PRODUTOS.slice(0, 5).map((produto, index) => ({
    id: `${String(postoIndex + 1).repeat(8)}-${String(index + 1).repeat(4)}-4000-8000-${String((postoIndex + 1) * 10 + index + 1).padStart(12, "0")}`,
    posto_id: posto.id,
    produto_id: produto.id,
    codigo: `TQ-${index + 1}`,
    qr_code: `${posto.nome.toUpperCase().replaceAll(" ", "-")}-TQ-${index + 1}`,
    ativo: true,
  })),
);

const COMPARTIMENTOS_INICIAIS: TmsCompartimento[] = [
  {
    id: "bbbbbbbb-0001-4000-8000-000000000001",
    numero: 1,
    volume_litros: 5000,
    produto_id: PRODUTOS[0].id,
    posto_id: POSTOS[0].id,
    tanque_id: TANQUES[0].id,
    entrega_id: "cccccccc-0001-4000-8000-000000000001",
    lacre: "LC-1042",
    qr_code: "CAM01-C1",
    excecao_vazio_autorizada: false,
  },
  {
    id: "bbbbbbbb-0002-4000-8000-000000000002",
    numero: 2,
    volume_litros: 5000,
    produto_id: PRODUTOS[2].id,
    posto_id: POSTOS[0].id,
    tanque_id: TANQUES[2].id,
    entrega_id: "cccccccc-0001-4000-8000-000000000001",
    lacre: "LC-1043",
    qr_code: "CAM01-C2",
    excecao_vazio_autorizada: false,
  },
  {
    id: "bbbbbbbb-0003-4000-8000-000000000003",
    numero: 3,
    volume_litros: 5000,
    produto_id: PRODUTOS[4].id,
    posto_id: POSTOS[1].id,
    tanque_id: TANQUES[10].id,
    entrega_id: "cccccccc-0002-4000-8000-000000000002",
    lacre: "LC-1044",
    qr_code: "CAM01-C3",
    excecao_vazio_autorizada: false,
  },
  {
    id: "bbbbbbbb-0004-4000-8000-000000000004",
    numero: 4,
    volume_litros: 5000,
    produto_id: PRODUTOS[1].id,
    posto_id: POSTOS[2].id,
    tanque_id: TANQUES[11].id,
    entrega_id: "cccccccc-0003-4000-8000-000000000003",
    lacre: "LC-1045",
    qr_code: "CAM01-C4",
    excecao_vazio_autorizada: false,
  },
  {
    id: "bbbbbbbb-0005-4000-8000-000000000005",
    numero: 5,
    volume_litros: 5000,
    produto_id: PRODUTOS[3].id,
    posto_id: POSTOS[2].id,
    tanque_id: TANQUES[13].id,
    entrega_id: "cccccccc-0003-4000-8000-000000000003",
    lacre: "LC-1046",
    qr_code: "CAM01-C5",
    excecao_vazio_autorizada: false,
  },
];

const PEDIDOS = [
  { posto: "Posto Real", produto: "Diesel S10", litros: 5000, prioridade: "Critico" },
  { posto: "Casa Caiada", produto: "Etanol", litros: 5000, prioridade: "Urgente" },
  { posto: "Posto VIP", produto: "Gasolina Aditivada", litros: 5000, prioridade: "Atencao" },
  { posto: "Igarassu Centro", produto: "Gasolina Comum", litros: 5000, prioridade: "Normal" },
];

function fallbackValidacao(programacao: TmsProgramacao): TmsValidacaoResultado {
  const status_compartimentos = Object.fromEntries(
    programacao.compartimentos.map((compartimento) => [
      compartimento.id,
      statusCompartimentoLocal(compartimento, programacao.postos, programacao.tanques),
    ]),
  );
  const erros: string[] = [];
  const alertas: string[] = [];
  const alertas_laterais: TmsAlerta[] = [
    {
      tipo: "tempo_rota",
      mensagem: "Igarassu-Suape: 1h30 a 2h para 60km",
      severidade: "info",
    },
  ];
  const volume = programacao.compartimentos.reduce(
    (acc, item) => acc + (item.produto_id ? item.volume_litros : 0),
    0,
  );

  if (volume < 25000) {
    alertas.push("Volume total abaixo de 25.000L");
    alertas_laterais.push({
      tipo: "caminhao_incompleto",
      mensagem: "Carga abaixo de 25.000L",
      severidade: "warning",
    });
  }
  if (
    programacao.compartimentos.some(
      (item) => !item.produto_id || !item.posto_id || !item.tanque_id,
    )
  ) {
    erros.push("Todos os 5 compartimentos devem estar preenchidos");
  }
  if (Object.values(status_compartimentos).includes("conflito")) {
    erros.push("Produto incompativel com tanque");
  }
  if (!programacao.ordem_definida) {
    alertas_laterais.push({
      tipo: "ordem_nao_definida",
      mensagem: "Ordem de descarga pendente",
      severidade: "erro",
    });
  }
  if (!programacao.nfe_vinculada) {
    alertas_laterais.push({
      tipo: "nfe_nao_vinculada",
      mensagem: "NF-e ainda nao vinculada",
      severidade: "info",
    });
  }

  return { erros, alertas, status_compartimentos, alertas_laterais };
}

function statusCompartimentoLocal(
  compartimento: TmsCompartimento,
  postos: TmsPosto[],
  tanques: TmsTanque[],
): StatusCompartimento {
  if (!compartimento.produto_id && !compartimento.posto_id && !compartimento.tanque_id) {
    return "rascunho";
  }
  if (
    !compartimento.produto_id ||
    !compartimento.posto_id ||
    !compartimento.tanque_id ||
    !compartimento.entrega_id
  ) {
    return "faltando_info";
  }
  const tanque = tanques.find((item) => item.id === compartimento.tanque_id);
  const posto = postos.find((item) => item.id === compartimento.posto_id);
  if (!tanque || tanque.produto_id !== compartimento.produto_id || !posto?.latitude || !posto.longitude) {
    return "conflito";
  }
  return "valido";
}

function statusPalette(status: StatusCompartimento) {
  return {
    valido: {
      label: "OK",
      card: "border-emerald-400/25 bg-emerald-500/[0.08] shadow-emerald-950/20",
      accent: "bg-emerald-400",
      text: "text-emerald-200",
      ring: "hover:ring-emerald-400/35",
    },
    faltando_info: {
      label: "Atencao",
      card: "border-amber-400/25 bg-amber-500/[0.08] shadow-amber-950/20",
      accent: "bg-amber-400",
      text: "text-amber-200",
      ring: "hover:ring-amber-400/35",
    },
    conflito: {
      label: "Erro",
      card: "border-red-400/25 bg-red-500/[0.08] shadow-red-950/20",
      accent: "bg-red-400",
      text: "text-red-200",
      ring: "hover:ring-red-400/35",
    },
    rascunho: {
      label: "Vazio",
      card: "border-zinc-500/25 bg-zinc-500/[0.07] shadow-black/20",
      accent: "bg-zinc-400",
      text: "text-zinc-300",
      ring: "hover:ring-zinc-400/25",
    },
  }[status];
}

function severityClass(severidade: TmsAlerta["severidade"]) {
  return {
    info: "border-sky-400/20 bg-sky-400/[0.07] text-sky-100",
    warning: "border-amber-400/25 bg-amber-400/[0.08] text-amber-100",
    erro: "border-red-400/25 bg-red-400/[0.08] text-red-100",
  }[severidade];
}

export function TmsProgramacaoLive() {
  const [janelaSuape, setJanelaSuape] = useState("2026-06-24T08:30");
  const [protocolo, setProtocolo] = useState("SUP-2026-0619");
  const [compartimentos, setCompartimentos] = useState(COMPARTIMENTOS_INICIAIS);
  const [resultado, setResultado] = useState<TmsValidacaoResultado>(() =>
    fallbackValidacao(montarProgramacao(COMPARTIMENTOS_INICIAIS, janelaSuape, protocolo)),
  );
  const [validando, setValidando] = useState(false);
  const [compartimentoAberto, setCompartimentoAberto] = useState<TmsCompartimento | null>(null);

  const totalLitros = useMemo(
    () => compartimentos.reduce((acc, item) => acc + (item.produto_id ? item.volume_litros : 0), 0),
    [compartimentos],
  );
  const ocupacao = compartimentos.filter((item) => item.produto_id).length;
  const statusGeral = resultado.erros.length === 0 ? "Carga validada" : "Ajuste necessario";

  function montarPayload(nextCompartimentos = compartimentos) {
    return montarProgramacao(nextCompartimentos, janelaSuape, protocolo);
  }

  async function validar() {
    const payload = montarPayload();
    setValidando(true);
    try {
      const validacao = await validarProgramacaoTms(payload);
      setResultado(validacao);
      toast.success("Programacao validada pelo backend TMS");
    } catch {
      setResultado(fallbackValidacao(payload));
      toast.warning("Backend TMS indisponivel. Validacao local aplicada.");
    } finally {
      setValidando(false);
    }
  }

  function atualizarCompartimento(
    id: string,
    campo: "produto_id" | "posto_id" | "tanque_id" | "lacre",
    valor: string,
  ) {
    setCompartimentos((atual) => {
      const next = atual.map((item) => {
        if (item.id !== id) return item;
        const atualizado = { ...item, [campo]: valor || undefined };
        if (campo === "posto_id" || campo === "produto_id") {
          const tanque = TANQUES.find(
            (candidate) =>
              candidate.posto_id === atualizado.posto_id &&
              candidate.produto_id === atualizado.produto_id,
          );
          atualizado.tanque_id = tanque?.id;
        }
        return atualizado;
      });
      const nextCompartimento = next.find((item) => item.id === id);
      if (nextCompartimento) setCompartimentoAberto(nextCompartimento);
      setResultado(fallbackValidacao(montarPayload(next)));
      return next;
    });
  }

  return (
    <main className="@container/main min-h-[calc(100vh-3rem)] bg-background">
      <div className="mx-auto flex w-full max-w-[1800px] flex-col gap-6 px-5 py-6 md:px-8">
        <section className="rounded-xl border border-border/70 bg-card/70 p-5 shadow-sm">
          <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={resultado.erros.length ? "destructive" : "default"}>
                  {statusGeral}
                </Badge>
                <Badge variant="outline">Suape PE</Badge>
                <Badge variant="outline">CAM-01</Badge>
              </div>
              <h1 className="mt-3 text-2xl font-semibold tracking-normal md:text-3xl">
                Programação de Carga
              </h1>
              <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
                Planejamento operacional por compartimento, com validação de produto, tanque,
                geolocalização e ordem de descarga.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-[180px_180px_auto_auto]">
              <label className="grid gap-1 text-xs text-muted-foreground">
                Janela Suape
                <Input
                  type="datetime-local"
                  value={janelaSuape}
                  onChange={(event) => setJanelaSuape(event.target.value)}
                  className="h-10"
                />
              </label>
              <label className="grid gap-1 text-xs text-muted-foreground">
                Protocolo
                <Input
                  value={protocolo}
                  onChange={(event) => setProtocolo(event.target.value)}
                  className="h-10 font-mono"
                />
              </label>
              <Button className="self-end" variant="outline" onClick={validar} disabled={validando}>
                <RefreshCwIcon className={cn(validando && "animate-spin")} />
                Validar
              </Button>
              <Button className="self-end" disabled={resultado.erros.length > 0}>
                <SaveIcon />
                Programar viagem
              </Button>
            </div>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-4">
            <Kpi icon={FuelIcon} label="Volume total" value={`${totalLitros.toLocaleString("pt-BR")} L`} />
            <Kpi icon={ShieldCheckIcon} label="Status da carga" value={resultado.erros.length ? "Pendente" : "Validada"} danger={resultado.erros.length > 0} />
            <Kpi icon={TruckIcon} label="Ocupação" value={`${ocupacao}/5`} />
            <Kpi icon={Clock3Icon} label="Janela" value={janelaSuape.replace("T", " ")} />
          </div>
        </section>

        <div className="grid gap-5 xl:grid-cols-[300px_minmax(620px,1fr)_320px]">
          <PedidosPendentes />

          <section className="space-y-5">
            <Card className="rounded-xl border-border/70 bg-card/80 shadow-sm">
              <CardHeader className="pb-1">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <CardTitle>Compartimentos do caminhão</CardTitle>
                    <CardDescription>CAM-01 - capacidade operacional 25.000L</CardDescription>
                  </div>
                  <div className="hidden items-center gap-2 text-xs text-muted-foreground sm:flex">
                    <Legend status="valido" label="OK" />
                    <Legend status="faltando_info" label="Atenção" />
                    <Legend status="conflito" label="Erro" />
                    <Legend status="rascunho" label="Vazio" />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="rounded-2xl border border-border/70 bg-muted/10 p-4 md:p-6">
                  <div className="mb-5 flex items-center justify-between gap-4">
                    <div>
                      <p className="text-sm font-medium">Tanque compartimentado</p>
                      <p className="text-xs text-muted-foreground">5 compartimentos independentes de 5.000L</p>
                    </div>
                    <div className="flex items-center gap-2 rounded-full border border-border/70 px-3 py-1.5 text-xs text-muted-foreground">
                      <RouteIcon className="size-3.5" />
                      Ordem: C1 {"->"} C2 {"->"} C3 {"->"} C4 {"->"} C5
                    </div>
                  </div>

                  <div className="relative">
                    <div className="pointer-events-none absolute -left-2 top-1/2 hidden h-20 w-8 -translate-y-1/2 rounded-l-full border border-border/70 bg-background xl:block" />
                    <div className="pointer-events-none absolute -right-4 top-1/2 hidden h-28 w-12 -translate-y-1/2 rounded-r-2xl border border-border/70 bg-background xl:block" />
                    <div className="grid overflow-hidden rounded-2xl border border-border/80 bg-background/70 shadow-lg shadow-black/10 md:grid-cols-5">
                      {compartimentos.map((compartimento, index) => {
                        const status = resultado.status_compartimentos[compartimento.id] ?? "rascunho";
                        return (
                          <CompartimentoTile
                            key={compartimento.id}
                            compartimento={compartimento}
                            index={index}
                            status={status}
                            onClick={() => setCompartimentoAberto(compartimento)}
                          />
                        );
                      })}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-xl border-border/70 bg-card/80 shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle>Sequência operacional</CardTitle>
                <CardDescription>Resumo rápido para conferência antes da liberação.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-3 md:grid-cols-4">
                <Metric icon={TruckIcon} label="Veículo" value="CAM-01 - 5 x 5.000L" />
                <Metric icon={ShieldCheckIcon} label="Motorista" value="Motorista habitual" />
                <Metric icon={RouteIcon} label="Rota base" value="Igarassu -> Suape" />
                <Metric icon={FileTextIcon} label="NF-e" value="Pendente de vínculo" />
              </CardContent>
            </Card>
          </section>

          <AlertasPanel alertas={resultado.alertas_laterais} erros={resultado.erros} />
        </div>
      </div>

      {compartimentoAberto && (
        <EditorCompartimento
          compartimento={compartimentoAberto}
          status={resultado.status_compartimentos[compartimentoAberto.id] ?? "rascunho"}
          onClose={() => setCompartimentoAberto(null)}
          onChange={atualizarCompartimento}
        />
      )}
    </main>
  );
}

function CompartimentoTile({
  compartimento,
  index,
  status,
  onClick,
}: {
  compartimento: TmsCompartimento;
  index: number;
  status: StatusCompartimento;
  onClick: () => void;
}) {
  const palette = statusPalette(status);
  const produto = nomeProduto(compartimento.produto_id);
  const posto = nomePosto(compartimento.posto_id);

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "group relative flex min-h-[220px] flex-col justify-between border-border/70 p-4 text-left transition duration-200 hover:z-10 hover:-translate-y-0.5 hover:ring-2 focus-visible:z-10 focus-visible:outline-none focus-visible:ring-2",
        index > 0 && "border-t md:border-l md:border-t-0",
        palette.card,
        palette.ring,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-xs text-muted-foreground">Compartimento</p>
          <p className="mt-1 font-mono text-2xl font-semibold">C{compartimento.numero}</p>
        </div>
        <span className={cn("rounded-full px-2.5 py-1 text-xs font-medium", palette.text)}>
          {palette.label}
        </span>
      </div>

      <div className="space-y-3">
        <div>
          <p className="text-xs text-muted-foreground">Produto</p>
          <p className="mt-1 min-h-10 text-base font-semibold leading-tight">{produto}</p>
        </div>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <p className="text-xs text-muted-foreground">Volume</p>
            <p className="font-mono font-medium">{compartimento.volume_litros.toLocaleString("pt-BR")} L</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Posto</p>
            <p className="truncate font-medium">{posto}</p>
          </div>
        </div>
      </div>

      <div className="pointer-events-none absolute inset-x-3 bottom-3 translate-y-1 rounded-lg border border-border/70 bg-background/95 p-3 opacity-0 shadow-xl transition group-hover:translate-y-0 group-hover:opacity-100">
        <div className="grid gap-1 text-xs">
          <span className="font-mono text-muted-foreground">{compartimento.qr_code}</span>
          <span>Lacre: {compartimento.lacre ?? "pendente"}</span>
          <span>Tanque: {nomeTanque(compartimento.tanque_id)}</span>
        </div>
      </div>

      <span className={cn("absolute inset-x-4 bottom-0 h-1 rounded-t-full", palette.accent)} />
    </button>
  );
}

function EditorCompartimento({
  compartimento,
  status,
  onClose,
  onChange,
}: {
  compartimento: TmsCompartimento;
  status: StatusCompartimento;
  onClose: () => void;
  onChange: (
    id: string,
    campo: "produto_id" | "posto_id" | "tanque_id" | "lacre",
    valor: string,
  ) => void;
}) {
  const palette = statusPalette(status);
  const tanquesFiltrados = TANQUES.filter(
    (tanque) =>
      tanque.posto_id === compartimento.posto_id &&
      (!compartimento.produto_id || tanque.produto_id === compartimento.produto_id),
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-2xl border border-border bg-card shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-border/70 p-5">
          <div>
            <div className="flex items-center gap-2">
              <span className={cn("size-2.5 rounded-full", palette.accent)} />
              <span className={cn("text-sm font-medium", palette.text)}>{palette.label}</span>
            </div>
            <h2 className="mt-2 text-xl font-semibold">Compartimento C{compartimento.numero}</h2>
            <p className="text-sm text-muted-foreground">Configuração de produto, destino e lacre.</p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="Fechar">
            <XIcon />
          </Button>
        </div>

        <div className="grid gap-4 p-5 md:grid-cols-2">
          <SelectNative
            label="Produto"
            value={compartimento.produto_id ?? ""}
            options={PRODUTOS.map((produto) => ({ value: produto.id, label: produto.nome }))}
            onChange={(value) => onChange(compartimento.id, "produto_id", value)}
          />
          <SelectNative
            label="Posto destino"
            value={compartimento.posto_id ?? ""}
            options={POSTOS.map((posto) => ({ value: posto.id, label: posto.nome }))}
            onChange={(value) => onChange(compartimento.id, "posto_id", value)}
          />
          <SelectNative
            label="Tanque"
            value={compartimento.tanque_id ?? ""}
            options={tanquesFiltrados.map((tanque) => ({
              value: tanque.id,
              label: `${tanque.codigo} - ${tanque.qr_code}`,
            }))}
            onChange={(value) => onChange(compartimento.id, "tanque_id", value)}
          />
          <label className="grid gap-1 text-xs text-muted-foreground">
            Lacre
            <Input
              value={compartimento.lacre ?? ""}
              onChange={(event) => onChange(compartimento.id, "lacre", event.target.value)}
              className="h-10 font-mono"
            />
          </label>
        </div>

        <div className="grid gap-3 border-t border-border/70 bg-muted/15 p-5 text-sm md:grid-cols-3">
          <Detail label="Volume" value={`${compartimento.volume_litros.toLocaleString("pt-BR")} L`} />
          <Detail label="QR compartimento" value={compartimento.qr_code ?? "pendente"} />
          <Detail label="Tanque" value={nomeTanque(compartimento.tanque_id)} />
        </div>
      </div>
    </div>
  );
}

function PedidosPendentes() {
  return (
    <aside className="space-y-3">
      <div>
        <h2 className="text-sm font-semibold">Pedidos pendentes</h2>
        <p className="text-xs text-muted-foreground">Fila para composição da carga.</p>
      </div>
      <div className="space-y-2">
        {PEDIDOS.map((pedido) => (
          <div
            key={`${pedido.posto}-${pedido.produto}`}
            className="rounded-xl border border-border/70 bg-card/75 p-3 shadow-sm transition hover:bg-card"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{pedido.posto}</p>
                <p className="truncate text-xs text-muted-foreground">{pedido.produto}</p>
              </div>
              <Badge variant={pedido.prioridade === "Critico" ? "destructive" : "outline"}>
                {pedido.prioridade}
              </Badge>
            </div>
            <div className="mt-3 flex items-center justify-between text-sm">
              <span className="font-mono font-semibold">{pedido.litros.toLocaleString("pt-BR")} L</span>
              <span className="text-xs text-muted-foreground">1 compartimento</span>
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}

function AlertasPanel({ alertas, erros }: { alertas: TmsAlerta[]; erros: string[] }) {
  return (
    <aside className="space-y-4">
      <Card className="rounded-xl border-border/70 bg-card/80 shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle>Alertas</CardTitle>
          <CardDescription>Riscos operacionais da programação.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {alertas.map((alerta) => (
            <div
              key={`${alerta.tipo}-${alerta.mensagem}`}
              className={cn("rounded-lg border px-3 py-2.5 text-sm", severityClass(alerta.severidade))}
            >
              <div className="flex items-start gap-2">
                <AlertTriangleIcon className="mt-0.5 size-4 shrink-0" />
                <div className="min-w-0">
                  <p className="font-medium leading-snug">{alerta.mensagem}</p>
                  <p className="mt-1 font-mono text-[11px] opacity-70">{alerta.tipo}</p>
                </div>
              </div>
            </div>
          ))}
          {alertas.length === 0 && (
            <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/[0.07] p-3 text-sm text-emerald-100">
              Nenhum alerta ativo.
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="rounded-xl border-border/70 bg-card/80 shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle>Liberação</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <CheckItem ok={erros.length === 0} label="Validações operacionais" />
          <CheckItem ok label="Postos com geolocalização" />
          <CheckItem ok label="Tanques com QR Code" />
          <CheckItem ok={false} label="NF-e vinculada" />
        </CardContent>
      </Card>
    </aside>
  );
}

function montarProgramacao(
  compartimentos: TmsCompartimento[],
  janelaSuape: string,
  protocolo: string,
): TmsProgramacao {
  return {
    veiculo_id: "dddddddd-0001-4000-8000-000000000001",
    motorista_id: "eeeeeeee-0001-4000-8000-000000000001",
    janela_suape: new Date(janelaSuape).toISOString(),
    protocolo_suape: protocolo,
    compartimentos,
    postos: POSTOS,
    tanques: TANQUES,
    documentos_criticos: [
      { tipo: "CNH", valido: true, vence_em_dias: 24 },
      { tipo: "CRLV", valido: true },
      { tipo: "Inspecao do tanque", valido: true },
    ],
    pedidos_criticos_pendentes: 1,
    ordem_definida: true,
    nfe_vinculada: false,
  };
}

function SelectNative({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="grid gap-1 text-xs text-muted-foreground">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 rounded-lg border border-input bg-background px-3 text-sm text-foreground outline-none transition focus:border-ring focus:ring-2 focus:ring-ring/30"
      >
        <option value="">Selecionar</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function Kpi({
  icon: Icon,
  label,
  value,
  danger = false,
}: {
  icon: typeof FuelIcon;
  label: string;
  value: string;
  danger?: boolean;
}) {
  return (
    <div className="rounded-xl border border-border/70 bg-background/55 p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-muted-foreground">{label}</p>
        <Icon className={cn("size-4", danger ? "text-red-300" : "text-muted-foreground")} />
      </div>
      <p className={cn("mt-2 font-mono text-xl font-semibold", danger && "text-red-300")}>{value}</p>
    </div>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof TruckIcon;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-border/70 bg-background/45 p-3">
      <div className="mb-2 flex items-center gap-2 text-muted-foreground">
        <Icon className="size-4" />
        <p className="text-xs">{label}</p>
      </div>
      <p className="text-sm font-medium">{value}</p>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 truncate font-mono text-sm font-medium">{value}</p>
    </div>
  );
}

function Legend({ status, label }: { status: StatusCompartimento; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={cn("size-2 rounded-full", statusPalette(status).accent)} />
      {label}
    </span>
  );
}

function CheckItem({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="flex min-w-0 items-center gap-2">
        {ok ? (
          <CheckCircle2Icon className="size-4 shrink-0 text-emerald-400" />
        ) : (
          <AlertTriangleIcon className="size-4 shrink-0 text-amber-400" />
        )}
        <span className="truncate">{label}</span>
      </span>
      {label.includes("QR") ? (
        <QrCodeIcon className="size-4 shrink-0 text-muted-foreground" />
      ) : label.includes("NF-e") ? (
        <FileTextIcon className="size-4 shrink-0 text-muted-foreground" />
      ) : (
        <MapPinIcon className="size-4 shrink-0 text-muted-foreground" />
      )}
    </div>
  );
}

function nomeProduto(id?: string) {
  return PRODUTOS.find((produto) => produto.id === id)?.nome ?? "Produto pendente";
}

function nomePosto(id?: string) {
  return POSTOS.find((posto) => posto.id === id)?.nome ?? "Posto pendente";
}

function nomeTanque(id?: string) {
  return TANQUES.find((tanque) => tanque.id === id)?.codigo ?? "pendente";
}
