-- Niyetsen — Faz 3: foto kanıtı, puan olayları ve özel Storage alanı.

create table if not exists public.proofs (
  id text primary key,
  task_id text not null references public.tasks(id) on delete cascade,
  photo_url text not null,
  location jsonb,
  confidence_score int not null check (confidence_score between 0 and 100),
  attempt_no int not null check (attempt_no > 0),
  created_at timestamptz not null default now()
);
create index if not exists proofs_task_id_idx on public.proofs(task_id);

alter table public.tasks
  add column if not exists proof_id text references public.proofs(id) on delete set null;

create table if not exists public.point_log (
  id uuid primary key default gen_random_uuid(),
  user_id text not null references public.users(id) on delete cascade,
  task_id text references public.tasks(id) on delete set null,
  category text not null,
  delta int not null,
  reason text not null,
  created_at timestamptz not null default now()
);
create index if not exists point_log_user_created_idx
  on public.point_log(user_id, created_at desc);

alter table public.proofs enable row level security;
alter table public.point_log enable row level security;

-- Bucket private kalır. Backend service_role ile yazar; authenticated politikaları
-- ileride doğrudan istemci erişimi gerekirse yalnız kullanıcının kendi klasörünü açar.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'proofs',
  'proofs',
  false,
  5242880,
  array['image/jpeg', 'image/png']
)
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists "proofs_select_own" on storage.objects;
create policy "proofs_select_own"
on storage.objects for select
to authenticated
using (
  bucket_id = 'proofs'
  and (storage.foldername(name))[1] = auth.uid()::text
);

drop policy if exists "proofs_insert_own" on storage.objects;
create policy "proofs_insert_own"
on storage.objects for insert
to authenticated
with check (
  bucket_id = 'proofs'
  and (storage.foldername(name))[1] = auth.uid()::text
);

drop policy if exists "proofs_update_own" on storage.objects;
create policy "proofs_update_own"
on storage.objects for update
to authenticated
using (
  bucket_id = 'proofs'
  and (storage.foldername(name))[1] = auth.uid()::text
)
with check (
  bucket_id = 'proofs'
  and (storage.foldername(name))[1] = auth.uid()::text
);

drop policy if exists "proofs_delete_own" on storage.objects;
create policy "proofs_delete_own"
on storage.objects for delete
to authenticated
using (
  bucket_id = 'proofs'
  and (storage.foldername(name))[1] = auth.uid()::text
);
