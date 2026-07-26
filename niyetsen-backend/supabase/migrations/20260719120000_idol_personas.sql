-- FAZ 7.7 (Dalga 4.3): İdol Modu persona dosyaları — Supabase depolama.
-- Markdown (knowledge/idoller.md) tohum kalır; ASIL KAYNAK artık DB'dir.
-- Böylece yeni idol eklemek deploy gerektirmez (Şahin panelden/scriptten besler).

create table if not exists public.idol_personas (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,                 -- "greenlights-yolu", "first-principles-yolu"
  path_name text not null,                   -- SUNUM ADI (felsefe): "Greenlights Yolu"
  tagline text not null default '',
  category text not null default 'genel',    -- girisimci|sporcu|bilim|sanat|tarih|genel
  -- Kişi adı YALNIZ kaynak/ilham göstergesi olarak tutulur; arayüzde paket adı
  -- kullanılır, kişi adı "ilham alır" cümlesinde geçer (kişilik hakları + Apple 5.2.1).
  inspired_by text not null default '',
  source_note text not null default '',
  -- Persona dossier (15 alanlı model): why_important, core_beliefs, mindset,
  -- habits, daily_routine, sports_or_physical_practice, reading_profile,
  -- books_read_or_recommended, decision_style, failure_and_recovery,
  -- public_quotes, lessons_for_users, sources ...
  dossier jsonb not null default '{}'::jsonb,
  tags text[] not null default '{}',
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idol_personas_active_idx
  on public.idol_personas(is_active, category);

alter table public.idol_personas enable row level security;

-- RAG parçaları: 80-150 kelimelik bloklar, embedding önbelleğiyle birlikte.
-- pgvector kurulu değilse embedding float8[] olarak saklanır (kosinüs kodda).
create table if not exists public.persona_chunks (
  id uuid primary key default gen_random_uuid(),
  persona_id uuid not null references public.idol_personas(id) on delete cascade,
  section text not null,                     -- overview|mindset|habits|books|lessons...
  chunk_index int not null default 0,
  text text not null,
  embedding float8[],                        -- null: keyword fallback kullanılır
  created_at timestamptz not null default now()
);

create index if not exists persona_chunks_persona_idx
  on public.persona_chunks(persona_id, section);

alter table public.persona_chunks enable row level security;
