import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: { root: process.cwd() },
  // Permite build paralelo quando `.next` está travado (OneDrive / `next dev`)
  distDir: process.env.NEXT_DIST_DIR || ".next",
  // Dev: Playwright/browser em 127.0.0.1 vs localhost — evita bloqueio de HMR/hidratação
  allowedDevOrigins: ["127.0.0.1", "localhost"],
};

export default nextConfig;
