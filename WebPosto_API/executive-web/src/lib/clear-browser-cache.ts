/**
 * Limpa o que o JS consegue no navegador e força reload sem cache de página.
 * Não apaga o cache HTTP interno do Chrome (só o usuário via DevTools / Ctrl+Shift+Del).
 */

export type ClearBrowserCacheResult = {
  localStorage: boolean;
  sessionStorage: boolean;
  cacheApi: number;
  serviceWorkers: number;
};

export async function clearBrowserCache(): Promise<ClearBrowserCacheResult> {
  const result: ClearBrowserCacheResult = {
    localStorage: false,
    sessionStorage: false,
    cacheApi: 0,
    serviceWorkers: 0,
  };

  try {
    localStorage.clear();
    result.localStorage = true;
  } catch {
    /* ignore */
  }

  try {
    sessionStorage.clear();
    result.sessionStorage = true;
  } catch {
    /* ignore */
  }

  if (typeof caches !== "undefined") {
    try {
      const keys = await caches.keys();
      await Promise.all(keys.map((k) => caches.delete(k)));
      result.cacheApi = keys.length;
    } catch {
      /* ignore */
    }
  }

  if (typeof navigator !== "undefined" && "serviceWorker" in navigator) {
    try {
      const regs = await navigator.serviceWorker.getRegistrations();
      await Promise.all(regs.map((r) => r.unregister()));
      result.serviceWorkers = regs.length;
    } catch {
      /* ignore */
    }
  }

  return result;
}

/** Reload forçando bypass de cache da página atual. */
export function hardReload(): void {
  const url = new URL(window.location.href);
  url.searchParams.set("_cb", String(Date.now()));
  window.location.replace(url.toString());
}
