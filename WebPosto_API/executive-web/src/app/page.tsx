import { redirect } from "next/navigation";

interface PageProps {
  searchParams: Promise<{ view?: string }>;
}

/**
 * Home e aliases legados (?view=president-dashboard) → suíte executiva unificada.
 */
export default async function Home({ searchParams }: PageProps) {
  const params = await searchParams;
  const view = (params.view || "").toLowerCase().replace(/_/g, "-");

  if (view === "details") {
    redirect("/dashboard/executive");
  }
  if (
    view === "president-dashboard" ||
    view === "presidentdashboard" ||
    view === "presidente" ||
    view === "financial" ||
    view === "app/financial"
  ) {
    redirect("/executive/financial");
  }

  redirect("/executive/financial");
}
