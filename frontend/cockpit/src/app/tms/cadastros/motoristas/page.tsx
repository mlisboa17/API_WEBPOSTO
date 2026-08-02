import { CockpitShell } from "@/components/cockpit-shell";
import { TmsMotoristasAdmin } from "@/components/tms-motoristas-admin";

export default function TmsMotoristasPage() {
  return (
    <CockpitShell title="TMS - Cadastro de Motoristas">
      <TmsMotoristasAdmin />
    </CockpitShell>
  );
}
