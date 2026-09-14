create table if not exists private.agent_conversations (
  id uuid primary key default gen_random_uuid(),
  status text not null default 'open' check (status in ('open','confirmed','abandoned')),
  report_id uuid references private.reports(id) on delete set null,
  draft jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create table if not exists private.agent_messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references private.agent_conversations(id) on delete cascade,
  role text not null check (role in ('user','assistant')),
  content text not null,
  created_at timestamptz not null default now()
);
create index if not exists agent_messages_conversation_idx on private.agent_messages(conversation_id, created_at);
alter table private.agent_conversations enable row level security;
alter table private.agent_messages enable row level security;
