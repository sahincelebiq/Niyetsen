-- Occurrence zaman çizelgesi + otomatik doldurma (prod 20260913131242 ile eşitleme, 2026-09-13)
-- Prod'da agent ile uygulanmış; bu dosya fresh DB'lerin aynı son duruma gelmesi içindir.
-- Tamamı idempotent. 131020'den SONRA uygulanır.

alter table public.plan_event_occurrences
  add column if not exists scheduled_at timestamptz null;
alter table public.plan_event_occurrences
  add column if not exists remind_at timestamptz null;
alter table public.plan_event_occurrences
  add column if not exists reminded_at timestamptz null;
alter table public.plan_event_occurrences
  add column if not exists snoozed_until timestamptz null;

-- Etkinlik saatinden scheduled_at/remind_at türetir; done'da puan kaynağını 'self' sayar.
-- users.timezone kullanır (çekirdek tabloda varsayılan 'Europe/Istanbul').
create or replace function public.plan_event_occurrences_fill()
returns trigger
language plpgsql
set search_path to 'public'
as $function$
declare
  v_time text;
  v_offset int;
  v_tz text;
  v_local timestamp;
begin
  if tg_op = 'INSERT' then
    if new.scheduled_at is null or new.remind_at is null then
      select e.scheduled_time, e.remind_offset_min, u.timezone
        into v_time, v_offset, v_tz
      from public.plan_events e
      join public.users u on u.id = e.user_id
      where e.id = new.event_id;
      if v_time is not null then
        v_local := new.date + v_time::time;
        if new.scheduled_at is null then
          begin
            new.scheduled_at := v_local at time zone coalesce(v_tz, 'Europe/Istanbul');
          exception when invalid_parameter_value then
            new.scheduled_at := v_local at time zone 'Europe/Istanbul';
          end;
        end if;
        if new.remind_at is null then
          new.remind_at := new.scheduled_at - make_interval(mins => coalesce(v_offset, 0));
        end if;
      end if;
    end if;
    if new.status = 'done' and new.points_source is null then
      new.points_source := 'self';
    end if;
    return new;
  end if;

  -- UPDATE
  if new.status = 'done' and old.status is distinct from 'done' and new.points_source is null then
    new.points_source := 'self';
  end if;
  return new;
end;
$function$;

drop trigger if exists plan_event_occurrences_fill_trg on public.plan_event_occurrences;
create trigger plan_event_occurrences_fill_trg
  before insert or update on public.plan_event_occurrences
  for each row execute function plan_event_occurrences_fill();

create index if not exists plan_event_occurrences_remind_due_idx
  on public.plan_event_occurrences (remind_at)
  where ((status = 'pending') and (reminded_at is null));
create index if not exists plan_event_occurrences_user_status_date_idx
  on public.plan_event_occurrences (user_id, status, date);
