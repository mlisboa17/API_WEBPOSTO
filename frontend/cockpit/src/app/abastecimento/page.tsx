import { AbastecimentoLive } from "@/components/abastecimento-live";
import { CockpitShell } from "@/components/cockpit-shell";

export default function AbastecimentoPage() {
  return (
    <CockpitShell title="Abastecimento">
      <AbastecimentoLive />
    </CockpitShell>
  );
}
