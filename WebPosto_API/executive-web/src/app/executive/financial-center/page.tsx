import { redirect } from "next/navigation";

/**
 * Rota legada fora do (executive) layout.
 * Redireciona para a suíte unificada com Sidebar + GlobalFilter.
 */
export default function FinancialCenterLegacyRedirect() {
  redirect("/executive/financial");
}
