import { DataRequestResponse } from "../types/data-request-types";

/**
 * Adaptador HTTP isolado para a API DATA-ON-DEMAND.
 * Consome os endpoints /api/proxy/executive-copilot/data-requests/*
 */

export async function planDataRequest(
  unidades: number[],
  startDate: string,
  endDate: string,
  signal?: AbortSignal
): Promise<DataRequestResponse> {
  const payload = {
    unidades,
    periodo: {
      inicio: startDate,
      fim: endDate,
    },
  };

  const response = await fetch("/api/proxy/executive-copilot/data-requests/plan", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include",
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => "");
    const status = response.status;
    let customMessage = `Erro HTTP ${status} ao planejar solicitação de dados.`;

    if (status === 401) {
      customMessage = "Sua sessão expirou";
    } else if (status === 403) {
      customMessage = "Você não possui acesso a esta unidade";
    } else if (status === 422) {
      customMessage = "Revise o escopo da solicitação de dados";
    }

    const err = new Error(customMessage);
    (err as any).status = status;
    (err as any).detail = errorText;
    throw err;
  }

  return response.json();
}

export async function confirmDataRequest(
  requestId: string,
  planHash: string,
  signal?: AbortSignal
): Promise<DataRequestResponse> {
  const payload = {
    planHash,
  };

  const response = await fetch(`/api/proxy/executive-copilot/data-requests/${requestId}/confirm`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include",
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => "");
    const status = response.status;
    let customMessage = `Erro HTTP ${status} ao confirmar solicitação de dados.`;

    if (status === 401) {
      customMessage = "Sua sessão expirou";
    } else if (status === 403) {
      customMessage = "Você não possui acesso a esta unidade";
    } else if (status === 422) {
      customMessage = "Plano expirado ou hash inválido. Prepare uma nova solicitação.";
    }

    const err = new Error(customMessage);
    (err as any).status = status;
    (err as any).detail = errorText;
    throw err;
  }

  return response.json();
}

export async function getDataRequestStatus(
  requestId: string,
  signal?: AbortSignal
): Promise<DataRequestResponse> {
  const response = await fetch(`/api/proxy/executive-copilot/data-requests/${requestId}`, {
    method: "GET",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    signal,
  });

  if (!response.ok) {
    const status = response.status;
    let customMessage = `Erro HTTP ${status} ao consultar status da solicitação.`;
    if (status === 401) customMessage = "Sua sessão expirou";

    const err = new Error(customMessage);
    (err as any).status = status;
    throw err;
  }

  return response.json();
}

export async function cancelDataRequest(
  requestId: string,
  signal?: AbortSignal
): Promise<DataRequestResponse> {
  const response = await fetch(`/api/proxy/executive-copilot/data-requests/${requestId}/cancel`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    signal,
  });

  if (!response.ok) {
    const status = response.status;
    let customMessage = `Erro HTTP ${status} ao cancelar solicitação.`;
    if (status === 401) customMessage = "Sua sessão expirou";

    const err = new Error(customMessage);
    (err as any).status = status;
    throw err;
  }

  return response.json();
}
