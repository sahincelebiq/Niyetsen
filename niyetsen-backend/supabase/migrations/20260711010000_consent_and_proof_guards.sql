-- Granular/versioned consent and proof request concurrency guards.

create table if not exists public.user_consents (
  user_id text not null references public.users(id) on delete cascade,
  consent_kind text not null check (consent_kind in (
    'privacy_policy', 'kvkk_explicit_consent', 'ai_chat_processing',
    'proof_photo_processing', 'marketing_communications'
  )),
  version text not null,
  accepted boolean not null default false,
  decided_at timestamptz not null default now(),
  primary key (user_id, consent_kind, version)
);
alter table public.user_consents enable row level security;

-- Existing onboarding checkbox represented only KVKK/privacy acknowledgement.
-- It must never silently opt users into AI, proof-photo, or marketing processing.
insert into public.user_consents
  (user_id, consent_kind, version, accepted, decided_at)
select id, kind, '2026-07-11', true, kvkk_consent_at
from public.users
cross join (values ('privacy_policy'), ('kvkk_explicit_consent')) as kinds(kind)
where kvkk_consent_at is not null
on conflict do nothing;

create table if not exists public.proof_requests (
  user_id text not null references public.users(id) on delete cascade,
  task_id text not null references public.tasks(id) on delete cascade,
  idempotency_key text not null,
  status text not null check (status in ('in_progress', 'completed')),
  attempt_no int not null check (attempt_no > 0),
  result_json jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (user_id, task_id, idempotency_key)
);
create unique index if not exists proof_requests_one_in_progress_per_task
  on public.proof_requests(task_id) where status = 'in_progress';
alter table public.proof_requests enable row level security;

create or replace function public.claim_proof_attempt(
  p_user_id text, p_task_id text, p_idempotency_key text
) returns table (
  claim_status text, attempt_no int, result_json jsonb
) language plpgsql security definer set search_path = public as $$
declare
  v_task public.tasks%rowtype;
  v_request public.proof_requests%rowtype;
begin
  select t.* into v_task
  from public.tasks t
  join public.plans p on p.id = t.plan_id
  where t.id = p_task_id and p.user_id = p_user_id
  for update of t;
  if not found then
    return query select 'not_found'::text, 0, null::jsonb;
    return;
  end if;

  select * into v_request from public.proof_requests
  where user_id = p_user_id and task_id = p_task_id
    and idempotency_key = p_idempotency_key;
  if found then
    -- A worker can die after claiming. Reclaim stale work so the task is not
    -- permanently blocked; attempts are committed only by finish_proof_attempt.
    if v_request.status = 'in_progress'
       and v_request.updated_at < now() - interval '5 minutes' then
      delete from public.proof_requests
      where user_id = p_user_id and task_id = p_task_id
        and idempotency_key = p_idempotency_key;
    else
      return query select
        case when v_request.status = 'completed' then 'completed' else 'in_progress' end,
        v_request.attempt_no, v_request.result_json;
      return;
    end if;
  end if;

  delete from public.proof_requests
  where task_id = p_task_id and status = 'in_progress'
    and updated_at < now() - interval '5 minutes';
  if exists (
    select 1 from public.proof_requests
    where task_id = p_task_id and status = 'in_progress'
  ) then
    return query select
      'in_progress'::text, v_task.proof_attempts + 1, null::jsonb;
    return;
  end if;
  if v_task.status <> 'pending' then
    return query select 'resolved'::text, v_task.proof_attempts, null::jsonb;
    return;
  end if;
  insert into public.proof_requests
    (user_id, task_id, idempotency_key, status, attempt_no)
  values
    (p_user_id, p_task_id, p_idempotency_key, 'in_progress', v_task.proof_attempts + 1);
  return query select 'started'::text, v_task.proof_attempts + 1, null::jsonb;
end;
$$;

create or replace function public.finish_proof_attempt(
  p_user_id text, p_task_id text, p_idempotency_key text, p_result jsonb
) returns void language plpgsql security definer set search_path = public as $$
declare
  v_attempt int;
begin
  select attempt_no into v_attempt
  from public.proof_requests
  where user_id = p_user_id and task_id = p_task_id
    and idempotency_key = p_idempotency_key and status = 'in_progress'
  for update;
  if not found then
    raise exception 'proof request is not active';
  end if;
  update public.tasks set proof_attempts = greatest(proof_attempts, v_attempt)
  where id = p_task_id;
  update public.proof_requests
  set status = 'completed', result_json = p_result, updated_at = now()
  where user_id = p_user_id and task_id = p_task_id
    and idempotency_key = p_idempotency_key;
end;
$$;

create or replace function public.abort_proof_attempt(
  p_user_id text, p_task_id text, p_idempotency_key text
) returns void language sql security definer set search_path = public as $$
  delete from public.proof_requests
  where user_id = p_user_id and task_id = p_task_id
    and idempotency_key = p_idempotency_key and status = 'in_progress';
$$;

revoke all on function public.claim_proof_attempt(text, text, text)
  from public, anon, authenticated;
revoke all on function public.finish_proof_attempt(text, text, text, jsonb)
  from public, anon, authenticated;
revoke all on function public.abort_proof_attempt(text, text, text)
  from public, anon, authenticated;
grant execute on function public.claim_proof_attempt(text, text, text) to service_role;
grant execute on function public.finish_proof_attempt(text, text, text, jsonb) to service_role;
grant execute on function public.abort_proof_attempt(text, text, text) to service_role;
