import { CockpitShell } from "@/components/cockpit-shell";
import { TmsVeiculosAdmin } from "@/components/tms-veiculos-admin";

export default function TmsVeiculosPage() {
  return (
    <CockpitShell title="TMS - Cadastro de Veiculos">
      <TmsVeiculosAdmin />
    </CockpitShell>
  );
}
