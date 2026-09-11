create schema if not exists private;
create type private.report_source as enum ('web', 'whatsapp');
create type private.report_status as enum ('Nuevo', 'En revisión', 'Atendido', 'Cerrado');
create type private.report_priority as enum ('Baja', 'Media', 'Alta', 'Crítica');

create table private.case_counters (year integer primary key, value integer not null check (value >= 0));
create table private.reports (
  id uuid primary key default gen_random_uuid(), case_number text not null unique,
  source private.report_source not null default 'web', category text not null, description text not null,
  occurred_at timestamptz, occurred_at_is_approximate boolean not null default false,
  channel text, related_information jsonb not null default '{}'::jsonb,
  reporter_name text not null, contact_type text not null check (contact_type in ('email','phone')), contact_value text not null,
  status private.report_status not null default 'Nuevo', priority private.report_priority not null default 'Media',
  ai_consent boolean not null default false, privacy_notice_version text not null default 'pilot-v1',
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(), expires_at timestamptz not null
);
create index reports_created_at_idx on private.reports (created_at desc);
create index reports_status_priority_idx on private.reports (status, priority);
create table private.evidences (
  id uuid primary key default gen_random_uuid(), report_id uuid not null references private.reports(id) on delete cascade,
  storage_key text not null unique, original_name text not null, mime_type text not null,
  size_bytes bigint not null check (size_bytes > 0 and size_bytes <= 10485760), sha256 text not null, created_at timestamptz not null default now()
);
create table private.ai_analyses (
  id uuid primary key default gen_random_uuid(), report_id uuid not null references private.reports(id) on delete cascade,
  attempt integer not null, status text not null check (status in ('pending','completed','failed')),
  suggested_category text, suggested_priority private.report_priority, neutral_summary text,
  extracted_data jsonb not null default '{}'::jsonb, signals jsonb not null default '[]'::jsonb,
  model text not null, prompt_version text not null, safe_error text, created_at timestamptz not null default now(), completed_at timestamptz
);
create table private.observations (
  id uuid primary key default gen_random_uuid(), report_id uuid not null references private.reports(id) on delete cascade,
  text text not null, admin_user_id uuid not null, created_at timestamptz not null default now()
);
create table private.case_history (
  id uuid primary key default gen_random_uuid(), report_id uuid not null references private.reports(id) on delete cascade,
  action text not null, details jsonb not null default '{}'::jsonb,
  actor_type text not null check (actor_type in ('citizen','admin','system','whatsapp')), actor_id uuid, created_at timestamptz not null default now()
);
create table private.deletion_audit (id bigint generated always as identity primary key, case_number text not null, deleted_at timestamptz not null default now());
insert into storage.buckets (id,name,public,file_size_limit,allowed_mime_types)
values ('cybersos-evidence','cybersos-evidence',false,10485760,array['image/png','image/jpeg','image/webp'])
on conflict (id) do update set public=false,file_size_limit=excluded.file_size_limit,allowed_mime_types=excluded.allowed_mime_types;
revoke all on schema private from anon, authenticated;
revoke all on all tables in schema private from anon, authenticated;
