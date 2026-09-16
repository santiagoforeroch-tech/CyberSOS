alter table private.agent_conversations add column if not exists external_key text;
create unique index if not exists agent_conversations_external_key_idx
  on private.agent_conversations(external_key) where external_key is not null;
