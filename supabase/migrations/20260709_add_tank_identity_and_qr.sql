create extension if not exists unaccent;

alter table public.tanks
  add column if not exists name text,
  add column if not exists product_type text,
  add column if not exists qr_code_identifier text;

with numbered as (
  select
    t.id,
    s.name as station_name,
    p.name as product_name,
    row_number() over (partition by t.station_id order by p.name, t.id) as rn
  from public.tanks t
  join public.stations s on s.id = t.station_id
  join public.products p on p.id = t.product_id
)
update public.tanks t
set
  name = coalesce(t.name, 'TQ-' || lpad(numbered.rn::text, 2, '0')),
  product_type = coalesce(t.product_type, numbered.product_name),
  qr_code_identifier = coalesce(
    t.qr_code_identifier,
    upper(
      regexp_replace(
        regexp_replace(
          public.unaccent(numbered.station_name || '-TQ-' || lpad(numbered.rn::text, 2, '0') || '-' || numbered.product_name),
          '[^a-zA-Z0-9]+', '-', 'g'
        ),
        '(^-|-$)', '', 'g'
      )
    )
  ),
  updated_at = now()
from numbered
where numbered.id = t.id;

create unique index if not exists ux_tanks_qr_code_identifier_not_null
  on public.tanks (qr_code_identifier)
  where qr_code_identifier is not null;

create index if not exists ix_tanks_station_name
  on public.tanks (station_id, name);
