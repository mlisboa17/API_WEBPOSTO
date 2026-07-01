import { CockpitShell } from "@/components/cockpit-shell";
import { TmsProgramacaoLive } from "@/components/tms-programacao-live";

export default function TmsProgramacaoPage() {
  return (
    <CockpitShell title="TMS · Programação de Carga">
      <TmsProgramacaoLive />
    </CockpitShell>
  );
}
