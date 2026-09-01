export type StatusCompartimento = "valido" | "faltando_info" | "conflito" | "rascunho";
export type SeveridadeAlerta = "info" | "warning" | "erro";

export type TmsPosto = {
  id: string;
  nome: string;
  latitude?: number;
  longitude?: number;
  raio_checkin_metros: number;
};

export type TmsProduto = {
  id: string;
  nome: string;
  codigo?: string;
};

export type TmsTanque = {
  id: string;
  posto_id: string;
  produto_id: string;
  codigo: string;
  qr_code?: string;
  ativo: boolean;
  produto?: string;
  capacidade_litros?: number;
  estoque_atual_litros?: number;
};

export type TmsCompartimento = {
  id: string;
  numero: number;
  volume_litros: number;
  produto_id?: string;
  posto_id?: string;
  tanque_id?: string;
  pedido_id?: string;
  entrega_id?: string;
  lacre?: string;
  qr_code?: string;
  excecao_vazio_autorizada: boolean;
};

export type TmsDocumentoCritico = {
  tipo: string;
  valido: boolean;
  vence_em_dias?: number;
};

export type TmsProgramacao = {
  id?: string;
  veiculo_id?: string;
  motorista_id?: string;
  janela_suape?: string;
  protocolo_suape?: string;
  compartimentos: TmsCompartimento[];
  postos: TmsPosto[];
  tanques: TmsTanque[];
  documentos_criticos: TmsDocumentoCritico[];
  pedidos_criticos_pendentes: number;
  ordem_definida: boolean;
  nfe_vinculada: boolean;
};

export type TmsAlerta = {
  tipo: string;
  mensagem: string;
  severidade: SeveridadeAlerta;
};

export type TmsValidacaoResultado = {
  erros: string[];
  alertas: string[];
  status_compartimentos: Record<string, StatusCompartimento>;
  alertas_laterais: TmsAlerta[];
};

export type TmsMobileEventoResultado = {
  status: string;
  bloqueado: boolean;
  requer_autorizacao: boolean;
  alertas: TmsAlerta[];
  evento: {
    status: string;
    data_hora: string;
    usuario_id: string;
    origem: string;
    observacao?: string;
  };
};

export type TmsDescargaFinalizarPayload = {
  viagem_id: string;
  usuario_id: string;
  entrega_id: string;
  posto_id: string;
  tanque_id: string;
  produto_id: string;
  compartimento_id: string;
  volume_programado_litros: number;
  volume_descargado_litros: number;
  estoque_pos_descarga_litros: number;
  foto_veeder_root_url: string;
  observacao?: string;
  payload?: Record<string, unknown>;
};
