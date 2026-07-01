create extension if not exists "pgcrypto";

create table if not exists tms_postos (
  id uuid primary key default gen_random_uuid(),
  nome varchar(255) not null,
  cnpj varchar(20) not null unique,
  razao_social varchar(255),
  nome_fantasia varchar(255),
  codigo_interno varchar(50),
  endereco text,
  cidade varchar(120),
  uf varchar(2) not null default 'PE',
  bairro varchar(120),
  cep varchar(20),
  latitude numeric(10, 7),
  longitude numeric(10, 7),
  raio_checkin_metros integer not null default 300,
  responsavel_principal varchar(255),
  telefone_whatsapp varchar(30),
  observacoes text,
  ativo boolean not null default true,
  criado_em timestamp without time zone not null default now(),
  atualizado_em timestamp without time zone not null default now()
);

create table if not exists tms_produtos (
  id uuid primary key default gen_random_uuid(),
  nome varchar(120) not null unique,
  codigo varchar(50),
  ativo boolean not null default true,
  criado_em timestamp without time zone not null default now()
);

create table if not exists tms_usuarios (
  id uuid primary key default gen_random_uuid(),
  nome varchar(255) not null,
  email varchar(255) not null unique,
  perfil varchar(50) not null,
  posto_id uuid references tms_postos(id),
  ativo boolean not null default true,
  criado_em timestamp without time zone not null default now(),
  atualizado_em timestamp without time zone not null default now()
);

create table if not exists tms_tanques (
  id uuid primary key default gen_random_uuid(),
  posto_id uuid not null references tms_postos(id),
  produto_id uuid not null references tms_produtos(id),
  codigo varchar(80) not null,
  capacidade_litros numeric(12, 2),
  qr_code varchar(255) not null unique,
  ativo boolean not null default true,
  criado_em timestamp without time zone not null default now(),
  atualizado_em timestamp without time zone not null default now(),
  unique (posto_id, codigo)
);

create table if not exists tms_bases_operacionais (
  id uuid primary key default gen_random_uuid(),
  nome varchar(255) not null,
  tipo varchar(50) not null,
  latitude numeric(10, 7),
  longitude numeric(10, 7),
  raio_checkin_metros integer not null default 300,
  ativo boolean not null default true,
  criado_em timestamp without time zone not null default now()
);

create table if not exists tms_caminhoes (
  id uuid primary key default gen_random_uuid(),
  placa varchar(20) not null unique,
  nome varchar(120),
  capacidade_total_litros numeric(12, 2) not null default 25000,
  ativo boolean not null default true,
  criado_em timestamp without time zone not null default now(),
  atualizado_em timestamp without time zone not null default now()
);

create table if not exists tms_compartimentos (
  id uuid primary key default gen_random_uuid(),
  caminhao_id uuid not null references tms_caminhoes(id),
  numero integer not null check (numero between 1 and 5),
  capacidade_litros numeric(12, 2) not null default 5000,
  posicao_fisica varchar(80),
  qr_code varchar(255) not null unique,
  ultimo_produto_id uuid references tms_produtos(id),
  ativo boolean not null default true,
  criado_em timestamp without time zone not null default now(),
  unique (caminhao_id, numero)
);

create table if not exists tms_motoristas (
  id uuid primary key default gen_random_uuid(),
  nome varchar(255) not null,
  cpf varchar(20) unique,
  cnh varchar(50),
  cnh_validade timestamp without time zone,
  mopp_validade timestamp without time zone,
  aso_validade timestamp without time zone,
  caminhao_habitual_id uuid references tms_caminhoes(id),
  ativo boolean not null default true,
  criado_em timestamp without time zone not null default now(),
  atualizado_em timestamp without time zone not null default now()
);

create table if not exists tms_politicas (
  id uuid primary key default gen_random_uuid(),
  chave varchar(120) not null unique,
  modo varchar(50) not null,
  configuracao jsonb,
  ativo boolean not null default true,
  criado_em timestamp without time zone not null default now(),
  atualizado_em timestamp without time zone not null default now()
);

create table if not exists tms_pedidos (
  id uuid primary key default gen_random_uuid(),
  posto_id uuid not null references tms_postos(id),
  solicitado_por_id uuid references tms_usuarios(id),
  data_desejada timestamp without time zone not null,
  prioridade varchar(30) not null default 'normal',
  status varchar(30) not null default 'solicitado',
  observacao text,
  criado_em timestamp without time zone not null default now(),
  atualizado_em timestamp without time zone not null default now()
);

create table if not exists tms_itens_pedido (
  id uuid primary key default gen_random_uuid(),
  pedido_id uuid not null references tms_pedidos(id),
  produto_id uuid not null references tms_produtos(id),
  quantidade_litros numeric(12, 2) not null,
  criado_em timestamp without time zone not null default now()
);

create table if not exists tms_viagens (
  id uuid primary key default gen_random_uuid(),
  caminhao_id uuid references tms_caminhoes(id),
  motorista_id uuid references tms_motoristas(id),
  janela_suape timestamp without time zone,
  protocolo_suape varchar(120),
  status varchar(40) not null default 'rascunho',
  ordem_descarga jsonb,
  ordem_manual boolean not null default false,
  nfe_vinculada boolean not null default false,
  criado_por_id uuid references tms_usuarios(id),
  criado_em timestamp without time zone not null default now(),
  atualizado_em timestamp without time zone not null default now()
);

create table if not exists tms_entregas (
  id uuid primary key default gen_random_uuid(),
  viagem_id uuid not null references tms_viagens(id),
  posto_id uuid not null references tms_postos(id),
  rota_index integer not null default 0,
  status varchar(40) not null default 'programada',
  criado_em timestamp without time zone not null default now()
);

create table if not exists tms_compartimentos_viagem (
  id uuid primary key default gen_random_uuid(),
  viagem_id uuid not null references tms_viagens(id),
  compartimento_id uuid not null references tms_compartimentos(id),
  entrega_id uuid references tms_entregas(id),
  pedido_id uuid references tms_pedidos(id),
  posto_id uuid references tms_postos(id),
  tanque_id uuid references tms_tanques(id),
  produto_id uuid references tms_produtos(id),
  volume_litros numeric(12, 2) not null default 5000,
  lacre varchar(120),
  ordem_descarga integer,
  excecao_vazio_autorizada boolean not null default false,
  criado_em timestamp without time zone not null default now(),
  unique (viagem_id, compartimento_id)
);

create table if not exists tms_eventos_viagem (
  id uuid primary key default gen_random_uuid(),
  viagem_id uuid not null references tms_viagens(id),
  entrega_id uuid references tms_entregas(id),
  status varchar(40) not null,
  usuario_id uuid references tms_usuarios(id),
  latitude numeric(10, 7),
  longitude numeric(10, 7),
  origem varchar(30) not null,
  observacao text,
  payload jsonb,
  criado_em timestamp without time zone not null default now()
);

create table if not exists tms_ocorrencias (
  id uuid primary key default gen_random_uuid(),
  viagem_id uuid references tms_viagens(id),
  entrega_id uuid references tms_entregas(id),
  tipo varchar(80) not null,
  severidade varchar(30) not null,
  descricao text not null,
  status varchar(30) not null default 'aberta',
  criado_em timestamp without time zone not null default now()
);

create table if not exists tms_autorizacoes_excecao (
  id uuid primary key default gen_random_uuid(),
  viagem_id uuid references tms_viagens(id),
  entrega_id uuid references tms_entregas(id),
  regra varchar(120) not null,
  justificativa text not null,
  autorizado_por_id uuid not null references tms_usuarios(id),
  payload jsonb,
  criado_em timestamp without time zone not null default now()
);

create table if not exists tms_estoques_posto (
  id uuid primary key default gen_random_uuid(),
  posto_id uuid not null references tms_postos(id),
  produto_id uuid not null references tms_produtos(id),
  estoque_litros numeric(12, 2) not null,
  medido_em timestamp without time zone not null,
  responsavel_id uuid references tms_usuarios(id),
  foto_veeder_root_antes varchar(500),
  foto_veeder_root_depois varchar(500),
  observacao text,
  criado_em timestamp without time zone not null default now()
);

create table if not exists tms_documentos_anexos (
  id uuid primary key default gen_random_uuid(),
  viagem_id uuid references tms_viagens(id),
  entrega_id uuid references tms_entregas(id),
  tipo varchar(80) not null,
  storage_path varchar(500) not null,
  criado_por_id uuid references tms_usuarios(id),
  criado_em timestamp without time zone not null default now()
);

create table if not exists tms_nfes_importadas (
  id uuid primary key default gen_random_uuid(),
  chave varchar(60) unique,
  numero varchar(30) not null,
  serie varchar(20),
  posto_cnpj varchar(20) not null,
  emitente_cnpj varchar(20),
  emitente_nome varchar(255),
  produto varchar(255) not null,
  volume numeric(12, 3) not null,
  valor numeric(14, 2),
  transportador varchar(255),
  transportador_documento varchar(20),
  placa varchar(20),
  uf_placa varchar(2),
  viagem_id uuid references tms_viagens(id),
  xml_storage_path varchar(500),
  dados_xml jsonb,
  emitida_em timestamp without time zone,
  importada_em timestamp without time zone not null default now()
);

create index if not exists ix_tms_postos_geo on tms_postos(latitude, longitude);
create index if not exists ix_tms_tanques_posto on tms_tanques(posto_id);
create index if not exists ix_tms_pedidos_status_prioridade on tms_pedidos(status, prioridade);
create index if not exists ix_tms_viagens_status_janela on tms_viagens(status, janela_suape);
create index if not exists ix_tms_eventos_viagem_criado on tms_eventos_viagem(viagem_id, criado_em);
create index if not exists ix_tms_ocorrencias_status on tms_ocorrencias(status, severidade);
create index if not exists ix_tms_nfes_placa on tms_nfes_importadas(placa);
create index if not exists ix_tms_nfes_posto_emitida on tms_nfes_importadas(posto_cnpj, emitida_em);

