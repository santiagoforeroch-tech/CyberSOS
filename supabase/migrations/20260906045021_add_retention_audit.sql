-- La eliminación efectiva se realiza desde el backend para retirar primero
-- los objetos privados de Storage. Esta migración solo amplía la auditoría.
alter table private.deletion_audit
  add column if not exists report_id uuid,
  add column if not exists evidence_count integer not null default 0,
  add column if not exists reason text not null default 'retención de 90 días';

create index if not exists deletion_audit_deleted_at_idx
  on private.deletion_audit (deleted_at desc);
