import { redirect } from "next/navigation";

/** Alias pedido: /executive/sales → tela canônica de Vendas & Elasticidade */
export default function ExecutiveSalesAliasPage() {
  redirect("/dashboard/sales-analytics");
}
