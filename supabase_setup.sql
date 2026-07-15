-- Spusťte celý soubor v Supabase: SQL Editor > New query > Run.
create extension if not exists pgcrypto;

create table if not exists public.nutrix_users (
    id uuid primary key default gen_random_uuid(),
    username text not null unique check (username = lower(username)),
    password_hash text not null,
    created_at timestamptz not null default now()
);

create table if not exists public.daily_metrics (
    user_id uuid not null references public.nutrix_users(id) on delete cascade,
    date date not null,
    calories numeric not null default 0,
    protein numeric not null default 0,
    carbohydrates numeric not null default 0,
    fat numeric not null default 0,
    primary key (user_id, date)
);

-- Žádné přímé přístupy z internetu. Aplikace používá tajný serverový klíč.
alter table public.nutrix_users enable row level security;
alter table public.daily_metrics enable row level security;

-- Ruční vytvoření uživatelů: změňte jméno a heslo a příkaz spusťte pro každý účet.
-- Nikdy neukládejte heslo přímo do tabulky; crypt() vytvoří bezpečný bcrypt hash.
-- insert into public.nutrix_users (username, password_hash)
-- values ('martin', crypt('SemVlozteSilneHeslo', gen_salt('bf')));
