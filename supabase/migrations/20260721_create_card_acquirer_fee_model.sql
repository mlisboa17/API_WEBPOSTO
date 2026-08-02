-- Modelagem Adquirente -> Bandeira -> ModalidadePagamento -> TaxaOperadora -> PrazoRecebimento
-- -> RecebimentoCartao. Extensão do VALUE-04 (Card Receivable Loss Detector, roadmap FASE 4
-- EXECUTAR) para sair do "Reconciliation LEVEL 1" (sinal agregado) rumo a evidência real por
-- transação (ver docs/d02/D02_CONCEPTUAL_CORRECTION.md, regra #4 "Cartões" exige evidência de
-- Adquirente/portal/NSU). Espelha src/domain/reconciliation/acquirer_fee_model.py.
--
-- Convenções seguem supabase/migrations/20260709_create_tms_fleet_and_drivers.sql
-- (uuid pk, timestamptz, snake_case, nomes em português onde já é o padrão do projeto).

create extension if not exists "pgcrypto";

create table if not exists public.adquirente (
  id uuid primary key default gen_random_uuid(),
  nome text not null unique check (nome in ('PAGBANK', 'REDE', 'CIELO', 'STONE', 'GETNET', 'SAFRAPAY')),
  ativo boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.bandeira (
  id uuid primary key default gen_random_uuid(),
  nome text not null unique check (nome in ('VISA', 'MASTERCARD', 'ELO', 'HIPERCARD', 'AMEX', 'MAESTRO', 'DINERS')),
  created_at timestamptz not null default now()
);

create table if not exists public.adquirente_bandeira (
  id uuid primary key default gen_random_uuid(),
  adquirente_id uuid not null references public.adquirente(id) on delete cascade,
  bandeira_id uuid not null references public.bandeira(id) on delete cascade,
  ativo boolean not null default true,
  created_at timestamptz not null default now(),
  unique (adquirente_id, bandeira_id)
);

create table if not exists public.modalidade_pagamento (
  id uuid primary key default gen_random_uuid(),
  nome text not null unique check (nome in ('DEBITO', 'CREDITO_VISTA', 'CREDITO_PARCELADO', 'CREDITO_PRE_PAGO', 'PIX')),
  created_at timestamptz not null default now()
);

-- Taxa vigente por Empresa + Adquirente + Bandeira + Modalidade, com histórico (vigencia_fim
-- null = taxa atual). Nunca sobrescrever uma linha antiga: ao corrigir, fechar vigencia_fim da
-- linha anterior e inserir uma nova com vigencia_inicio a partir da correção.
create table if not exists public.taxa_operadora (
  id uuid primary key default gen_random_uuid(),
  empresa_codigo integer not null,
  adquirente_id uuid not null references public.adquirente(id) on delete cascade,
  bandeira_id uuid not null references public.bandeira(id) on delete cascade,
  modalidade_id uuid not null references public.modalidade_pagamento(id) on delete cascade,
  percentual numeric(6, 4) not null check (percentual >= 0),
  parcelas integer check (parcelas is null or parcelas > 0),
  vigencia_inicio date not null,
  vigencia_fim date check (vigencia_fim is null or vigencia_fim >= vigencia_inicio),
  fonte text not null default 'validado_usuario',
  created_at timestamptz not null default now()
);

create index if not exists ix_taxa_operadora_lookup
  on public.taxa_operadora(empresa_codigo, adquirente_id, bandeira_id, modalidade_id, vigencia_inicio);

-- Prazo de liquidação por Adquirente + Modalidade (ex.: PagBank D+0 incluindo fim de semana,
-- Rede D+1 útil, Crédito Pré-Pago D+2 úteis independente da adquirente).
create table if not exists public.prazo_recebimento (
  id uuid primary key default gen_random_uuid(),
  adquirente_id uuid not null references public.adquirente(id) on delete cascade,
  modalidade_id uuid not null references public.modalidade_pagamento(id) on delete cascade,
  dias integer not null check (dias >= 0),
  dias_uteis boolean not null default true,
  inclui_fim_de_semana boolean not null default false,
  vigencia_inicio date not null default current_date,
  vigencia_fim date,
  created_at timestamptz not null default now(),
  unique (adquirente_id, modalidade_id, vigencia_inicio)
);

-- Recebimento real/esperado por venda de cartão (granularidade transacional, alimentado a
-- partir de /INTEGRACAO/CARTAO + venda_forma_pagamento).
create table if not exists public.recebimento_cartao (
  id uuid primary key default gen_random_uuid(),
  empresa_codigo integer not null,
  venda_codigo bigint not null,
  adquirente_id uuid references public.adquirente(id),
  bandeira_id uuid not null references public.bandeira(id),
  modalidade_id uuid not null references public.modalidade_pagamento(id),
  valor_bruto numeric(12, 2) not null,
  valor_liquido numeric(12, 2) not null,
  taxa_aplicada numeric(6, 4),
  data_venda date not null,
  data_prevista_recebimento date,
  data_efetiva_recebimento date,
  created_at timestamptz not null default now(),
  unique (empresa_codigo, venda_codigo, bandeira_id, modalidade_id)
);

create index if not exists ix_recebimento_cartao_empresa_data
  on public.recebimento_cartao(empresa_codigo, data_venda);

-- ---------------------------------------------------------------------------
-- Seed: adquirentes, bandeiras e vínculo (o que já observamos em cadastro real)
-- ---------------------------------------------------------------------------
insert into public.adquirente (nome) values
  ('PAGBANK'), ('REDE'), ('CIELO'), ('STONE'), ('GETNET'), ('SAFRAPAY')
on conflict (nome) do nothing;

insert into public.bandeira (nome) values
  ('VISA'), ('MASTERCARD'), ('ELO'), ('HIPERCARD'), ('AMEX'), ('MAESTRO'), ('DINERS')
on conflict (nome) do nothing;

insert into public.modalidade_pagamento (nome) values
  ('DEBITO'), ('CREDITO_VISTA'), ('CREDITO_PARCELADO'), ('CREDITO_PRE_PAGO'), ('PIX')
on conflict (nome) do nothing;

insert into public.adquirente_bandeira (adquirente_id, bandeira_id)
select a.id, b.id
from public.adquirente a
cross join public.bandeira b
where (a.nome = 'PAGBANK' and b.nome in ('VISA', 'MASTERCARD', 'ELO', 'AMEX', 'HIPERCARD'))
   or (a.nome = 'REDE' and b.nome in ('VISA', 'MASTERCARD', 'ELO', 'MAESTRO', 'HIPERCARD'))
on conflict (adquirente_id, bandeira_id) do nothing;

-- ---------------------------------------------------------------------------
-- Seed: taxas PagBank validadas pelo usuário em 2026-07-21 (referência oficial)
-- ---------------------------------------------------------------------------
insert into public.taxa_operadora (empresa_codigo, adquirente_id, bandeira_id, modalidade_id, percentual, vigencia_inicio, fonte)
select v.empresa_codigo, a.id, b.id, m.id, v.percentual, date '2026-07-21', 'validado_usuario_pagbank'
from (values
  -- Casa Caiada (5555)
  (5555, 'VISA', 'PIX', 0.50),
  (5555, 'VISA', 'DEBITO', 1.05),
  (5555, 'MASTERCARD', 'DEBITO', 1.05),
  (5555, 'ELO', 'DEBITO', 1.65),
  (5555, 'VISA', 'CREDITO_VISTA', 3.39),
  (5555, 'MASTERCARD', 'CREDITO_VISTA', 3.39),
  (5555, 'ELO', 'CREDITO_VISTA', 4.32),
  (5555, 'AMEX', 'CREDITO_VISTA', 3.19),
  -- Posto Doze Filial II (74014)
  (74014, 'VISA', 'PIX', 0.20),
  (74014, 'VISA', 'DEBITO', 0.65),
  (74014, 'MASTERCARD', 'DEBITO', 0.65),
  (74014, 'ELO', 'DEBITO', 1.04),
  (74014, 'VISA', 'CREDITO_VISTA', 2.79),
  (74014, 'MASTERCARD', 'CREDITO_VISTA', 2.79),
  (74014, 'ELO', 'CREDITO_VISTA', 4.28),
  (74014, 'AMEX', 'CREDITO_VISTA', 3.19)
) as v(empresa_codigo, bandeira_nome, modalidade_nome, percentual)
join public.adquirente a on a.nome = 'PAGBANK'
join public.bandeira b on b.nome = v.bandeira_nome
join public.modalidade_pagamento m on m.nome = v.modalidade_nome
on conflict do nothing;

-- Taxas Rede validadas pelo usuário em 2026-07-21 (site oficial e-Rede) para Posto Vip (11495)
insert into public.taxa_operadora (empresa_codigo, adquirente_id, bandeira_id, modalidade_id, percentual, vigencia_inicio, fonte)
select v.empresa_codigo, a.id, b.id, m.id, v.percentual, date '2026-07-21', 'validado_usuario_rede'
from (values
  (11495, 'VISA', 'DEBITO', 0.63),
  (11495, 'MAESTRO', 'DEBITO', 0.63),
  (11495, 'ELO', 'DEBITO', 1.43),
  (11495, 'MASTERCARD', 'CREDITO_VISTA', 2.70),
  (11495, 'VISA', 'CREDITO_VISTA', 2.70),
  (11495, 'ELO', 'CREDITO_VISTA', 3.50)
) as v(empresa_codigo, bandeira_nome, modalidade_nome, percentual)
join public.adquirente a on a.nome = 'REDE'
join public.bandeira b on b.nome = v.bandeira_nome
join public.modalidade_pagamento m on m.nome = v.modalidade_nome
on conflict do nothing;

-- ---------------------------------------------------------------------------
-- Seed: prazos de recebimento
-- ---------------------------------------------------------------------------
insert into public.prazo_recebimento (adquirente_id, modalidade_id, dias, dias_uteis, inclui_fim_de_semana)
select a.id, m.id, 0, false, true
from public.adquirente a
cross join public.modalidade_pagamento m
where a.nome = 'PAGBANK' and m.nome in ('PIX', 'DEBITO', 'CREDITO_VISTA')
on conflict (adquirente_id, modalidade_id, vigencia_inicio) do nothing;

insert into public.prazo_recebimento (adquirente_id, modalidade_id, dias, dias_uteis, inclui_fim_de_semana)
select a.id, m.id, 2, true, false
from public.adquirente a
cross join public.modalidade_pagamento m
where a.nome = 'PAGBANK' and m.nome = 'CREDITO_PRE_PAGO'
on conflict (adquirente_id, modalidade_id, vigencia_inicio) do nothing;

insert into public.prazo_recebimento (adquirente_id, modalidade_id, dias, dias_uteis, inclui_fim_de_semana)
select a.id, m.id, 1, true, false
from public.adquirente a
cross join public.modalidade_pagamento m
where a.nome = 'REDE' and m.nome in ('DEBITO', 'CREDITO_VISTA')
on conflict (adquirente_id, modalidade_id, vigencia_inicio) do nothing;
