alter table tms_estoques_posto
  add column if not exists viagem_id uuid references tms_viagens(id),
  add column if not exists entrega_id uuid references tms_entregas(id),
  add column if not exists compartimento_id uuid references tms_compartimentos(id),
  add column if not exists tanque_id uuid references tms_tanques(id),
  add column if not exists volume_descargado_litros numeric(12, 2),
  add column if not exists origem varchar(50) not null default 'manual';

alter table tms_estoques_posto
  drop column if exists foto_veeder_root_antes;

create index if not exists ix_tms_estoques_viagem on tms_estoques_posto(viagem_id);
create index if not exists ix_tms_estoques_entrega on tms_estoques_posto(entrega_id);
create index if not exists ix_tms_estoques_tanque on tms_estoques_posto(tanque_id);
create index if not exists ix_tms_estoques_origem on tms_estoques_posto(origem);
