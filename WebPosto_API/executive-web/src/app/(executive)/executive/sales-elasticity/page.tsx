import { redirect } from "next/navigation";

/** Alias: /executive/sales-elasticity → Vendas & Elasticidade */
export default function ExecutiveSalesElasticityAliasPage() {
  redirect("/dashboard/sales-analytics");
}
