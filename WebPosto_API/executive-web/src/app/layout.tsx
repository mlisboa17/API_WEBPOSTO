import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LOGOS | Tesouraria Executiva",
  description: "Dashboard executivo de tesouraria e fluxo de caixa",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body className="min-h-full bg-background text-foreground antialiased">{children}</body>
    </html>
  );
}
