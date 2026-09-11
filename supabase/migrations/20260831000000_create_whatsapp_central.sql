create extension if not exists pgcrypto;

create table public.whatsapp_connections (
  id uuid primary key default gen_random_uuid(),
  session_key text not null unique default 'central',
  account_jid text,
  display_name text,
  state text not null default 'disconnected'
    check (state in ('disconnected', 'starting', 'qr', 'connected', 'reconnecting', 'logged_out', 'error')),
  safe_error text,
  bridge_instance_id text,
  lease_expires_at timestamptz,
  connected_at timestamptz,
  last_seen_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.whatsapp_auth_items (
  id uuid primary key default gen_random_uuid(),
  connection_id uuid not null references public.whatsapp_connections(id) on delete cascade,
  item_type text not null,
  item_key text not null,
  ciphertext bytea not null,
  nonce bytea not null check (octet_length(nonce) = 12),
  auth_tag bytea not null check (octet_length(auth_tag) = 16),
  updated_at timestamptz not null default now(),
  unique (connection_id, item_type, item_key)
);

create table public.whatsapp_conversations (
  id uuid primary key default gen_random_uuid(),
  chat_jid text not null unique,
  kind text not null check (kind in ('direct', 'group')),
  title text,
  participant_jid text,
  last_message_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.whatsapp_messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.whatsapp_conversations(id) on delete restrict,
  wa_message_id text,
  direction text not null check (direction in ('inbound', 'outbound')),
  message_type text not null check (message_type in (
    'text', 'image', 'video', 'audio', 'document', 'sticker',
    'location', 'contact', 'poll', 'reaction', 'unknown'
  )),
  sender_jid text,
  text_content text,
  caption text,
  quoted_message_id uuid references public.whatsapp_messages(id) on delete set null,
  quoted_wa_message_id text,
  status text not null default 'queued'
    check (status in ('queued', 'sending', 'sent', 'delivered', 'read', 'failed')),
  safe_error text,
  metadata jsonb not null default '{}'::jsonb,
  occurred_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index whatsapp_messages_wa_unique
  on public.whatsapp_messages (conversation_id, wa_message_id, direction)
  where wa_message_id is not null;

create table public.whatsapp_message_events (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null unique,
  message_id uuid not null references public.whatsapp_messages(id) on delete cascade,
  status text not null check (status in ('queued', 'sending', 'sent', 'delivered', 'read', 'failed')),
  safe_error text,
  occurred_at timestamptz not null,
  created_at timestamptz not null default now()
);

create table public.whatsapp_processed_events (
  event_id uuid primary key,
  event_type text not null,
  occurred_at timestamptz not null,
  processed_at timestamptz not null default now()
);

create table public.whatsapp_media (
  id uuid primary key default gen_random_uuid(),
  message_id uuid not null references public.whatsapp_messages(id) on delete cascade,
  media_kind text not null check (media_kind in ('image', 'video', 'audio', 'document', 'sticker')),
  storage_bucket text not null default 'whatsapp-media',
  storage_path text not null unique,
  mime_type text not null,
  original_filename text,
  size_bytes bigint check (size_bytes is null or size_bytes >= 0),
  sha256 text,
  duration_seconds numeric,
  created_at timestamptz not null default now()
);

create table public.whatsapp_polls (
  id uuid primary key default gen_random_uuid(),
  message_id uuid not null unique references public.whatsapp_messages(id) on delete cascade,
  question text not null,
  selectable_count integer not null default 1 check (selectable_count > 0),
  created_at timestamptz not null default now()
);

create table public.whatsapp_poll_options (
  id uuid primary key default gen_random_uuid(),
  poll_id uuid not null references public.whatsapp_polls(id) on delete cascade,
  option_index integer not null check (option_index >= 0),
  label text not null,
  vote_count integer not null default 0 check (vote_count >= 0),
  unique (poll_id, option_index)
);

create table public.whatsapp_poll_votes (
  id uuid primary key default gen_random_uuid(),
  poll_id uuid not null references public.whatsapp_polls(id) on delete cascade,
  voter_jid text not null,
  selected_option_indexes integer[] not null default '{}',
  updated_at timestamptz not null default now(),
  unique (poll_id, voter_jid)
);

create table public.whatsapp_outbox (
  id uuid primary key default gen_random_uuid(),
  message_id uuid not null unique references public.whatsapp_messages(id) on delete cascade,
  command jsonb not null,
  state text not null default 'pending' check (state in ('pending', 'processing', 'sent', 'failed')),
  attempts integer not null default 0 check (attempts >= 0),
  available_at timestamptz not null default now(),
  lease_owner text,
  lease_expires_at timestamptz,
  safe_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.whatsapp_bridge_events (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null unique,
  event_type text not null,
  payload jsonb not null,
  occurred_at timestamptz not null,
  delivered_at timestamptz,
  processed_at timestamptz,
  attempts integer not null default 0 check (attempts >= 0),
  available_at timestamptz not null default now(),
  safe_error text,
  created_at timestamptz not null default now()
);

create index whatsapp_conversations_activity_idx
  on public.whatsapp_conversations (last_message_at desc nulls last, id);
create index whatsapp_messages_page_idx
  on public.whatsapp_messages (conversation_id, occurred_at desc, id desc);
create index whatsapp_outbox_ready_idx
  on public.whatsapp_outbox (state, available_at, lease_expires_at)
  where state in ('pending', 'processing');
create index whatsapp_bridge_events_ready_idx
  on public.whatsapp_bridge_events (processed_at, available_at)
  where processed_at is null;

insert into public.whatsapp_connections (session_key)
values ('central')
on conflict (session_key) do nothing;

insert into storage.buckets (id, name, public, file_size_limit)
values ('whatsapp-media', 'whatsapp-media', false, 20971520)
on conflict (id) do update
set public = false,
    file_size_limit = excluded.file_size_limit;

alter table public.whatsapp_connections enable row level security;
alter table public.whatsapp_auth_items enable row level security;
alter table public.whatsapp_conversations enable row level security;
alter table public.whatsapp_messages enable row level security;
alter table public.whatsapp_message_events enable row level security;
alter table public.whatsapp_processed_events enable row level security;
alter table public.whatsapp_media enable row level security;
alter table public.whatsapp_polls enable row level security;
alter table public.whatsapp_poll_options enable row level security;
alter table public.whatsapp_poll_votes enable row level security;
alter table public.whatsapp_outbox enable row level security;
alter table public.whatsapp_bridge_events enable row level security;

create or replace function public.claim_whatsapp_outbox(
  worker_id text,
  lease_seconds integer default 30
)
returns setof public.whatsapp_outbox
language plpgsql
security definer
set search_path = public
as $$
declare
  claimed_id uuid;
begin
  select id into claimed_id
  from public.whatsapp_outbox
  where (
      state = 'pending'
      or (state = 'processing' and lease_expires_at < now())
    )
    and available_at <= now()
  order by created_at
  for update skip locked
  limit 1;

  if claimed_id is null then
    return;
  end if;

  return query
  update public.whatsapp_outbox
  set state = 'processing',
      attempts = attempts + 1,
      lease_owner = worker_id,
      lease_expires_at = now() + make_interval(secs => greatest(lease_seconds, 10)),
      updated_at = now()
  where id = claimed_id
  returning *;
end;
$$;

revoke all on function public.claim_whatsapp_outbox(text, integer) from public, anon, authenticated;
