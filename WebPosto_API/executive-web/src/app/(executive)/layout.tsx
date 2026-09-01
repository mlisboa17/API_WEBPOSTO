"use client";

import { Suspense } from "react";
import { SidebarV2 } from "@/components/executive/sidebar-v2";
import { MobileNav } from "@/components/executive/mobile-nav";
import { GlobalFilterProvider } from "@/contexts/global-filter-context";
import { OperationalQuickBar } from "@/components/operational/OperationalQuickBar";
import { OfflineModeProvider } from "@/contexts/offline-mode-context";
import { OfflineModeBanner } from "@/components/executive/offline-mode-banner";

export default function ExecutiveLayout({ children }: { children: React.ReactNode }) {
  return (
    <GlobalFilterProvider>
      <OfflineModeProvider>
        <div className="flex min-h-screen bg-background">
          <Suspense fallback={<aside className="sticky top-0 hidden h-screen w-[248px] shrink-0 border-r bg-[#0f172a] lg:block" />}>
            <SidebarV2 />
          </Suspense>
          <main className="flex-1 overflow-y-auto pb-20 lg:pb-0">
            <OfflineModeBanner />
            <OperationalQuickBar />
            {children}
          </main>
          <div className="lg:hidden">
            <MobileNav />
          </div>
        </div>
      </OfflineModeProvider>
    </GlobalFilterProvider>
  );
}
