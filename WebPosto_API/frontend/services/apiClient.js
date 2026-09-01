const API_BASE = window.location.origin || "";

function readAccessToken() {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)access_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

/**
 * Faz a requisição HTTP com timeout.
 * @param {string} url
 * @param {RequestInit} options
 * @param {number} timeoutMs
 * @returns {Promise<Response>}
 */
async function fetchWithTimeout(url, options = {}, timeoutMs = 30000) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    return response;
  } finally {
    clearTimeout(id);
  }
}

/**
 * Centraliza a construção da query string.
 * @param {Object} params
 * @returns {string}
 */
export function buildQueryString(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === null || value === undefined || value === "") return;
    query.set(key, String(value));
  });
  return query.toString() ? `?${query.toString()}` : "";
}

/**
 * Cliente de API Centralizado.
 * Lida com headers base, tratamento de erro, parsing JSON e timeout.
 */
export const apiClient = {
  async request(method, path, options = {}) {
    const { params, body, headers, timeout = 30000, allowDegraded = false } = options;
    const url = `${API_BASE}${path}${buildQueryString(params)}`;

    const authHeaders = {};
    const token = readAccessToken();
    if (token) {
      authHeaders.Authorization = `Bearer ${token}`;
    }

    const fetchOptions = {
      method: method.toUpperCase(),
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders,
        ...headers,
      },
    };

    if (body) {
      fetchOptions.body = JSON.stringify(body);
    }

    let response;
    try {
      response = await fetchWithTimeout(url, fetchOptions, timeout);
    } catch (error) {
      if (error?.name === "AbortError") {
        throw new Error(`Timeout na requisicao ${method.toUpperCase()} ${path}`);
      }
      throw error;
    }

    let data;
    try {
      if (response.status !== 204) {
        data = await response.json();
      }
    } catch (err) {
      throw new Error(`Falha ao processar resposta da API para ${path}`);
    }

    if (!response.ok || (data && data.success === false && !allowDegraded && !data?.degraded)) {
      const msg = data?.error?.message || data?.detail || `Falha na requisicao ${method} ${path}`;
      const error = new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
      error.status = response.status;
      error.unavailable = response.status === 403 || response.status === 404;
      error.path = path;
      throw error;
    }

    return data;
  },

  get(path, options = {}) {
    return this.request("GET", path, options);
  },

  post(path, body, options = {}) {
    return this.request("POST", path, { ...options, body });
  },

  put(path, body, options = {}) {
    return this.request("PUT", path, { ...options, body });
  },

  delete(path, options = {}) {
    return this.request("DELETE", path, options);
  },
};
