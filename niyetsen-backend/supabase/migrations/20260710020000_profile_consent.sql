-- Niyetsen — Faz 2: onboarding profili ve KVKK rıza kaydı.
-- irade_modu_active MASTER_PLAN §2'de kilitli; UI'si Faz 3'te açılacak.

alter table public.users
  add column if not exists irade_modu_active boolean not null default false,
  add column if not exists kvkk_consent_at timestamptz;
