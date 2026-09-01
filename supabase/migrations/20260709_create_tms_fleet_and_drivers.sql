create table if not exists public.trucks (
  id uuid primary key default gen_random_uuid(),
  plate text not null unique,
  model text not null default '',
  status text not null default 'Ativo' check (status in ('Ativo', 'Inativo')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.truck_compartments (
  id uuid primary key default gen_random_uuid(),
  truck_id uuid not null references public.trucks(id) on delete cascade,
  compartment_number integer not null check (compartment_number between 1 and 5),
  capacity_liters numeric not null check (capacity_liters > 0),
  qr_code_identifier text not null unique,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (truck_id, compartment_number)
);

create table if not exists public.drivers (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  cnh_number text not null unique check (cnh_number ~ '^\d{11}$'),
  cnh_expiration date not null,
  mopp_certified boolean not null default false,
  habitual_truck_id uuid references public.trucks(id) on delete set null,
  status text not null default 'Ativo' check (status in ('Ativo', 'Inativo')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists ix_truck_compartments_truck_id
  on public.truck_compartments(truck_id);

create index if not exists ix_drivers_habitual_truck_id
  on public.drivers(habitual_truck_id);

create or replace function public.create_truck_with_compartments(
  p_plate text,
  p_model text,
  p_status text,
  p_compartment_capacities numeric[]
)
returns jsonb
language plpgsql
as $$
declare
  v_truck public.trucks%rowtype;
  v_index integer;
  v_compartment public.truck_compartments%rowtype;
  v_compartments jsonb := '[]'::jsonb;
  v_clean_plate text := upper(regexp_replace(coalesce(p_plate, ''), '[^A-Za-z0-9]', '', 'g'));
begin
  if v_clean_plate = '' then
    raise exception 'Placa e obrigatoria';
  end if;

  if p_compartment_capacities is null or array_length(p_compartment_capacities, 1) <> 5 then
    raise exception 'Informe exatamente 5 compartimentos';
  end if;

  insert into public.trucks (plate, model, status)
  values (v_clean_plate, trim(coalesce(p_model, '')), coalesce(nullif(p_status, ''), 'Ativo'))
  returning * into v_truck;

  for v_index in 1..5 loop
    if p_compartment_capacities[v_index] is null or p_compartment_capacities[v_index] <= 0 then
      raise exception 'Capacidade invalida no compartimento %', v_index;
    end if;

    insert into public.truck_compartments (
      truck_id,
      compartment_number,
      capacity_liters,
      qr_code_identifier
    )
    values (
      v_truck.id,
      v_index,
      p_compartment_capacities[v_index],
      v_clean_plate || '-COMP-' || lpad(v_index::text, 2, '0')
    )
    returning * into v_compartment;

    v_compartments := v_compartments || jsonb_build_object(
      'id', v_compartment.id,
      'truck_id', v_compartment.truck_id,
      'compartment_number', v_compartment.compartment_number,
      'capacity_liters', v_compartment.capacity_liters,
      'qr_code_identifier', v_compartment.qr_code_identifier
    );
  end loop;

  return jsonb_build_object(
    'id', v_truck.id,
    'plate', v_truck.plate,
    'model', v_truck.model,
    'status', v_truck.status,
    'created_at', v_truck.created_at,
    'compartments', v_compartments
  );
end;
$$;

grant select, insert, update, delete on public.trucks to anon, authenticated;
grant select, insert, update, delete on public.truck_compartments to anon, authenticated;
grant select, insert, update, delete on public.drivers to anon, authenticated;
grant execute on function public.create_truck_with_compartments(text, text, text, numeric[]) to anon, authenticated;
