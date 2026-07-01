import { CockpitShell } from "@/components/cockpit-shell";
import { TmsPostosAdmin } from "@/components/tms-postos-admin";

export default function TmsPostosPage() {
  return (
    <CockpitShell title="TMS · Cadastro de Postos">
      <TmsPostosAdmin />
    </CockpitShell>
  );
}
