import type {
  TmsDescargaFinalizarPayload,
  TmsMobileEventoResultado,
  TmsProgramacao,
  TmsValidacaoResultado,
} from "@/types/tms";

const TMS_API_BASE =
  process.env.NEXT_PUBLIC_API_URL ??
  process.env.NEXT_PUBLIC_TMS_API_URL ??
  "http://127.0.0.1:8000";

export async function validarProgramacaoTms(
  programacao: TmsProgramacao,
): Promise<TmsValidacaoResultado> {
  const response = await fetch(`${TMS_API_BASE}/api/tms/programacoes/validar`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(programacao),
  });

  if (!response.ok) {
    throw new Error(`Validacao TMS indisponivel (${response.status})`);
  }

  return response.json();
}

export async function finalizarDescargaTms(
  payload: TmsDescargaFinalizarPayload,
): Promise<TmsMobileEventoResultado> {
  const response = await fetch(`${TMS_API_BASE}/descarga/finalizar`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Finalizacao de descarga indisponivel (${response.status})`);
  }

  return response.json();
}
