-- FAZ 8: şema normalize — FK covering indexes + public bucket listing kapat
-- Prod'a 2026-08-02 MCP apply_migration ile uygulandı.
-- Idempotent; tekrar çalıştırılabilir.

create index if not exists chat_msgs_plan_id_idx
  on public.chat_msgs (plan_id);

create index if not exists chat_threads_plan_id_idx
  on public.chat_threads (plan_id);

create index if not exists intents_plan_id_idx
  on public.intents (plan_id);

create index if not exists point_log_task_id_idx
  on public.point_log (task_id);

create index if not exists tasks_proof_id_idx
  on public.tasks (proof_id);

create index if not exists users_active_plan_id_idx
  on public.users (active_plan_id);

create index if not exists users_active_thread_id_idx
  on public.users (active_thread_id);

-- Public plan-images: SELECT policy listing yüzeyi; object URL çalışmaya devam eder.
drop policy if exists "plan_images_public_read" on storage.objects;
