"use client";

import React from "react";
import { ArrowLeft, FileText, Download } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

interface ReportLayoutProps {
  title: string;
  subtitle: string;
  children: React.ReactNode;
  onExportMarkdown?: () => void;
  onExportPdf?: () => void;
  loading?: boolean;
}

export function ReportLayout({
  title,
  subtitle,
  children,
  onExportMarkdown,
  onExportPdf,
  loading = false,
}: ReportLayoutProps) {
  return (
    <div className="p-4 lg:p-8 max-w-[1600px] mx-auto space-y-6">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link href="/executive/reports">
            <Button
              variant="outline"
              size="icon"
              className="bg-slate-900 border-white/5 hover:bg-white/5"
            >
              <ArrowLeft size={18} />
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold text-white tracking-tight">{title}</h1>
            <p className="text-slate-400 text-sm">{subtitle}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {onExportMarkdown && (
            <Button
              variant="outline"
              size="sm"
              onClick={onExportMarkdown}
              disabled={loading}
              className="bg-slate-900 border-white/5 hover:bg-white/5"
            >
              <FileText size={14} className="mr-2" /> Markdown
            </Button>
          )}
          {onExportPdf && (
            <Button
              variant="outline"
              size="sm"
              onClick={onExportPdf}
              disabled={loading}
              className="bg-slate-900 border-white/5 hover:bg-white/5"
            >
              <Download size={14} className="mr-2" /> PDF
            </Button>
          )}
        </div>
      </header>
      {children}
    </div>
  );
}
