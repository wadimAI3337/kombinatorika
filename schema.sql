-- ============================================================
--  Таблица облачных сохранений для «Комбинаторики».
--  Открой Supabase → SQL Editor → New query, вставь это целиком
--  и нажми Run. Выполнять нужно один раз.
-- ============================================================

create table if not exists public.saves (
  user_id    uuid primary key references auth.users (id) on delete cascade,
  data       jsonb       not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

-- Row Level Security: каждый видит и правит только свою строку.
-- Именно поэтому публичный ключ anon можно спокойно держать в репозитории.
alter table public.saves enable row level security;

drop policy if exists "saves: читать своё"  on public.saves;
drop policy if exists "saves: создавать своё" on public.saves;
drop policy if exists "saves: менять своё"  on public.saves;

create policy "saves: читать своё"
  on public.saves for select
  using (auth.uid() = user_id);

create policy "saves: создавать своё"
  on public.saves for insert
  with check (auth.uid() = user_id);

create policy "saves: менять своё"
  on public.saves for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- ============================================================
--  «Реализация перевеса»: общий кэш разобранных партий.
--  Одну и ту же партию (скажем, из базы Карпова) Stockfish
--  считает один раз — дальше её разбор берут все из кэша.
--  Можно выполнить отдельно, если таблица saves уже есть.
-- ============================================================

create table if not exists public.real_cache (
  gid        text primary key,
  data       jsonb       not null,
  created_by uuid        default auth.uid(),
  created_at timestamptz not null default now()
);

alter table public.real_cache enable row level security;

drop policy if exists "real_cache: читать всем"        on public.real_cache;
drop policy if exists "real_cache: добавлять с входом" on public.real_cache;

create policy "real_cache: читать всем"
  on public.real_cache for select
  using (true);

create policy "real_cache: добавлять с входом"
  on public.real_cache for insert
  with check (auth.uid() is not null);
