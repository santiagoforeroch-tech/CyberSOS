create index if not exists ai_analyses_report_id_idx
on private.ai_analyses (report_id);

create index if not exists case_history_report_id_idx
on private.case_history (report_id);

create index if not exists observations_report_id_idx
on private.observations (report_id);
