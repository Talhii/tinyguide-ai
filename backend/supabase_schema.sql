-- TinyGuide AI — Supabase schema
-- Run this once in your Supabase project: SQL Editor → New query → paste → Run.

-- Baby profiles
create table if not exists infants (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  birth_date date not null,
  gender text not null,
  created_at timestamptz not null default now()
);

-- Growth measurements (weight/height over time)
create table if not exists growth_logs (
  id uuid primary key default gen_random_uuid(),
  infant_id uuid not null references infants(id) on delete cascade,
  weight_kg numeric not null,
  height_cm numeric not null,
  recorded_at date not null,
  created_at timestamptz not null default now()
);

-- Administered vaccinations
create table if not exists vaccination_logs (
  id uuid primary key default gen_random_uuid(),
  infant_id uuid not null references infants(id) on delete cascade,
  code text not null,
  administered_on date not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_growth_logs_infant on growth_logs (infant_id);
create index if not exists idx_vaccination_logs_infant on vaccination_logs (infant_id);

-- Note: the backend connects with the SERVICE ROLE key (server-side only),
-- which bypasses Row Level Security, so no RLS policies are required here.
