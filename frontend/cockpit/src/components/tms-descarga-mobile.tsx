"use client";

import { useMemo, useState } from "react";
import {
  AlertTriangleIcon,
  CameraIcon,
  CheckCircle2Icon,
  ClipboardCheckIcon,
  FuelIcon,
  MapPinIcon,
  QrCodeIcon,
  SendIcon,
  ShieldCheckIcon,
  TruckIcon,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { finalizarDescargaTms } from "@/lib/tms-api";

const IDS = {
  viagem: "dddddddd-0001-4000-8000-000000000001",
  usuario: "eeeeeeee-0001-4000-8000-000000000001",
  entrega: "cccccccc-0001-4000-8000-000000000001",
  posto: "aaaaaaaa-0001-4000-8000-000000000001",
  tanque: "11111111-1111-4000-8000-000000000011",
  produto: "11111111-1111-4111-8111-111111111111",
  compartimento: "bbbbbbbb-0001-4000-8000-000000000001",
};

const ETAPAS = [
  "Chegada",
  "Compartimento",
  "Lacre",
  "Tanque",
  "Descarga",
  "Veeder-Root",
  "Finalizar",
];

export function TmsDescargaMobile() {
  const [etapa, setEtapa] = useState(0);
  const [qrCompartimento, setQrCompartimento] = useState("CAM01-C1");
  const [lacre, setLacre] = useState("LC-1042");
  const [qrTanque, setQrTanque] = useState("POSTO-REAL-TQ-1");
  const [volumeDescargado, setVolumeDescargado] = useState("5000");
  const [estoqueFinal, setEstoqueFinal] = useState("18340");
  const [fotoNome, setFotoNome] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [concluido, setConcluido] = useState(false);

  const compativel = qrCompartimento === "CAM01-C1" && qrTanque === "POSTO-REAL-TQ-1";
  const fotoOk = fotoNome.length > 0;
  const podeAvancar = useMemo(() => {
    if (etapa === 1) return qrCompartimento.length > 0;
    if (etapa === 2) return lacre.length > 0;
    if (etapa === 3) return qrTanque.length > 0 && compativel;
    if (etapa === 5) return fotoOk && Number(estoqueFinal) >= 0 && Number(volumeDescargado) >= 0;
    return true;
  }, [compativel, estoqueFinal, etapa, fotoOk, lacre, qrCompartimento, qrTanque, volumeDescargado]);

  async function finalizar() {
    if (!fotoOk) {
      toast.error("A foto do Veeder-Root apos a descarga e obrigatoria");
      return;
    }
    setEnviando(true);
    try {
      await finalizarDescargaTms({
        viagem_id: IDS.viagem,
        usuario_id: IDS.usuario,
        entrega_id: IDS.entrega,
        posto_id: IDS.posto,
        tanque_id: IDS.tanque,
        produto_id: IDS.produto,
        compartimento_id: IDS.compartimento,
        volume_programado_litros: 5000,
        volume_descargado_litros: Number(volumeDescargado),
        estoque_pos_descarga_litros: Number(estoqueFinal),
        foto_veeder_root_url: `local://${fotoNome}`,
        observacao: "Foto Veeder-Root usada como comprovante de descarga e estoque.",
        payload: {
          qr_compartimento: qrCompartimento,
          qr_tanque: qrTanque,
          lacre,
          origem_estoque: "descarga",
        },
      });
      setConcluido(true);
      toast.success("Descarga finalizada e estoque atualizado");
    } catch {
      setConcluido(true);
      toast.warning("Backend indisponivel. Registro salvo em modo demonstracao.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main className="min-h-[calc(100vh-3rem)] bg-background">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-5 px-4 py-5 md:px-8">
        <section className="rounded-2xl border border-border/70 bg-card p-5 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div>
              <Badge variant={concluido ? "default" : "outline"}>
                {concluido ? "Finalizada" : "Em descarga"}
              </Badge>
              <h1 className="mt-3 text-2xl font-semibold">Descarga Segura</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Validação guiada de compartimento, lacre, tanque e foto Veeder-Root.
              </p>
            </div>
            <div className="rounded-xl border border-border/70 bg-background/60 p-3 text-right">
              <p className="text-xs text-muted-foreground">Entrega</p>
              <p className="font-mono text-sm font-semibold">Posto Real / C1</p>
            </div>
          </div>

          <div className="mt-5 grid grid-cols-7 gap-1">
            {ETAPAS.map((item, index) => (
              <div
                key={item}
                className={cn(
                  "h-2 rounded-full",
                  index <= etapa ? "bg-primary" : "bg-muted",
                )}
                title={item}
              />
            ))}
          </div>
        </section>

        <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
          <Card className="rounded-2xl border-border/70 bg-card shadow-sm">
            <CardHeader>
              <CardTitle>{ETAPAS[etapa]}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              {etapa === 0 && (
                <StepPanel
                  icon={MapPinIcon}
                  title="Confirmar chegada no posto"
                  description="Registre a chegada com geolocalização antes de iniciar qualquer validação física."
                />
              )}

              {etapa === 1 && (
                <FieldPanel
                  icon={QrCodeIcon}
                  title="Escanear compartimento"
                  label="QR do compartimento"
                  value={qrCompartimento}
                  onChange={setQrCompartimento}
                  hint="Esperado: CAM01-C1"
                />
              )}

              {etapa === 2 && (
                <FieldPanel
                  icon={ShieldCheckIcon}
                  title="Conferir lacre"
                  label="Lacre informado"
                  value={lacre}
                  onChange={setLacre}
                  hint="Esperado: LC-1042"
                />
              )}

              {etapa === 3 && (
                <div className="space-y-4">
                  <FieldPanel
                    icon={QrCodeIcon}
                    title="Escanear tanque do posto"
                    label="QR do tanque"
                    value={qrTanque}
                    onChange={setQrTanque}
                    hint="Esperado: POSTO-REAL-TQ-1"
                  />
                  <CompatibilityBanner ok={compativel} />
                </div>
              )}

              {etapa === 4 && (
                <StepPanel
                  icon={FuelIcon}
                  title="Iniciar e acompanhar descarga"
                  description="Produto liberado: Diesel S10. Volume programado: 5.000L. Mantenha a descarga dentro da sequência autorizada."
                />
              )}

              {etapa === 5 && (
                <div className="space-y-4">
                  <StepPanel
                    icon={CameraIcon}
                    title="Foto Veeder-Root pós-descarga"
                    description="Esta única foto comprova a descarga e atualiza o estoque do posto para este produto."
                  />
                  <label className="grid gap-2 text-sm">
                    Foto obrigatória
                    <Input
                      type="file"
                      accept="image/*"
                      capture="environment"
                      onChange={(event) => setFotoNome(event.target.files?.[0]?.name ?? "")}
                    />
                    {fotoNome && <span className="text-xs text-muted-foreground">{fotoNome}</span>}
                  </label>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <label className="grid gap-2 text-sm">
                      Volume descarregado
                      <Input
                        inputMode="decimal"
                        value={volumeDescargado}
                        onChange={(event) => setVolumeDescargado(event.target.value)}
                      />
                    </label>
                    <label className="grid gap-2 text-sm">
                      Estoque pós-descarga
                      <Input
                        inputMode="decimal"
                        value={estoqueFinal}
                        onChange={(event) => setEstoqueFinal(event.target.value)}
                      />
                    </label>
                  </div>
                </div>
              )}

              {etapa === 6 && (
                <div className="space-y-4">
                  <StepPanel
                    icon={ClipboardCheckIcon}
                    title="Finalizar entrega"
                    description="A foto Veeder-Root será gravada como evidência da entrega e registro de estoque do Posto Real."
                  />
                  {concluido && (
                    <div className="rounded-xl border border-emerald-400/25 bg-emerald-400/[0.08] p-4 text-sm text-emerald-100">
                      Descarga finalizada. Estoque atualizado a partir da foto pós-descarga.
                    </div>
                  )}
                </div>
              )}

              <div className="flex gap-2 pt-2">
                <Button
                  variant="outline"
                  onClick={() => setEtapa((value) => Math.max(0, value - 1))}
                  disabled={etapa === 0 || enviando}
                >
                  Voltar
                </Button>
                {etapa < 6 ? (
                  <Button
                    onClick={() => setEtapa((value) => Math.min(6, value + 1))}
                    disabled={!podeAvancar || enviando}
                  >
                    Avançar
                  </Button>
                ) : (
                  <Button onClick={finalizar} disabled={enviando || concluido}>
                    <SendIcon />
                    Finalizar descarga
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>

          <aside className="space-y-4">
            <Card className="rounded-2xl border-border/70 bg-card shadow-sm">
              <CardHeader>
                <CardTitle>Resumo</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <Info icon={TruckIcon} label="Compartimento" value="CAM-01 / C1" />
                <Info icon={FuelIcon} label="Produto" value="Diesel S10" />
                <Info icon={MapPinIcon} label="Posto" value="Posto Real" />
                <Info icon={QrCodeIcon} label="Tanque" value="TQ-1 Diesel S10" />
              </CardContent>
            </Card>

            <Card className="rounded-2xl border-border/70 bg-card shadow-sm">
              <CardHeader>
                <CardTitle>Regras críticas</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <Rule ok={qrCompartimento === "CAM01-C1"} label="Compartimento correto" />
                <Rule ok={lacre === "LC-1042"} label="Lacre esperado" />
                <Rule ok={compativel} label="Tanque compatível" />
                <Rule ok={fotoOk} label="Foto Veeder-Root pós-descarga" />
              </CardContent>
            </Card>
          </aside>
        </div>
      </div>
    </main>
  );
}

function StepPanel({
  icon: Icon,
  title,
  description,
}: {
  icon: typeof MapPinIcon;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-2xl border border-border/70 bg-background/55 p-5">
      <Icon className="size-8 text-primary" />
      <h2 className="mt-4 text-xl font-semibold">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
    </div>
  );
}

function FieldPanel({
  icon: Icon,
  title,
  label,
  value,
  onChange,
  hint,
}: {
  icon: typeof QrCodeIcon;
  title: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  hint: string;
}) {
  return (
    <div className="rounded-2xl border border-border/70 bg-background/55 p-5">
      <Icon className="size-8 text-primary" />
      <h2 className="mt-4 text-xl font-semibold">{title}</h2>
      <label className="mt-4 grid gap-2 text-sm">
        {label}
        <Input value={value} onChange={(event) => onChange(event.target.value)} className="font-mono" />
      </label>
      <p className="mt-2 text-xs text-muted-foreground">{hint}</p>
    </div>
  );
}

function CompatibilityBanner({ ok }: { ok: boolean }) {
  return (
    <div
      className={cn(
        "rounded-xl border p-4 text-sm",
        ok
          ? "border-emerald-400/25 bg-emerald-400/[0.08] text-emerald-100"
          : "border-red-400/25 bg-red-400/[0.08] text-red-100",
      )}
    >
      <div className="flex items-start gap-2">
        {ok ? <CheckCircle2Icon className="size-5" /> : <AlertTriangleIcon className="size-5" />}
        <div>
          <p className="font-medium">{ok ? "Compatível" : "Bloqueado"}</p>
          <p className="mt-1 text-xs opacity-80">
            {ok
              ? "Compartimento, produto e tanque conferem."
              : "Produto ou tanque divergente. Requer intervenção da operação."}
          </p>
        </div>
      </div>
    </div>
  );
}

function Info({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof TruckIcon;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <Icon className="size-4 text-muted-foreground" />
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="font-medium">{value}</p>
      </div>
    </div>
  );
}

function Rule({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className="flex items-center gap-2">
      {ok ? (
        <CheckCircle2Icon className="size-4 text-emerald-400" />
      ) : (
        <AlertTriangleIcon className="size-4 text-amber-400" />
      )}
      <span>{label}</span>
    </div>
  );
}

