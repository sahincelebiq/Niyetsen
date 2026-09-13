-- 2026-09-13 — 04 (2/2): olay tablosu güvenlik ağı.
-- Deploy'daki backend occurrence açarken scheduled_at/remind_at yazmaz; backend güncellenene
-- kadar cron'un taradığı alan boş kalmasın. Backend alanı kendisi gönderirse tetikleyici dokunmaz.
--   • INSERT: scheduled_at NULL ise (date + plan_events.scheduled_time) @ users.timezone → UTC.
--            remind_at NULL ise scheduled_at - plan_events.remind_offset_min.
--   • UPDATE: status pending→done ve points_source NULL ise 'self' (gölge olayda backend 'task' yazar).
-- Geçersiz timezone adı → Europe/Istanbul (invalid_parameter_value yakalanır; pg_timezone_names taranmaz).
-- Geri alma: 20260913131500_plan_event_occurrences_fill_schedule_down.sql

create or replace function public.plan_event_occurrences_fill()
returns trigger
language plpgsql
set search_path = public
as $$
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
$$;

revoke all on function public.plan_event_occurrences_fill() from public, anon, authenticated;

drop trigger if exists plan_event_occurrences_fill_trg on public.plan_event_occurrences;
create trigger plan_event_occurrences_fill_trg
  before insert or update on public.plan_event_occurrences
  for each row execute function public.plan_event_occurrences_fill();
