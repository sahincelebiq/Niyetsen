-- Kanıt isteği takılı kalırsa daha hızlı kurtar (Vision timeout ~90sn ile uyumlu).

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
    if v_request.status = 'in_progress'
       and v_request.updated_at < now() - interval '2 minutes' then
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
    and updated_at < now() - interval '2 minutes';
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
