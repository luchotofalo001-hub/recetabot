-- Correr en el SQL editor de Supabase.
create extension if not exists pgcrypto;

create table if not exists recipes (
  id uuid primary key default gen_random_uuid(),
  external_id text unique,
  title text not null,
  category text,
  url text,
  procedure text,
  ingredients text[] default '{}',
  amounts text[] default '{}',
  minutes int,
  vegetarian boolean default false,
  vegan boolean default false,
  tags text[] default '{}',
  custom boolean default false,
  incomplete boolean default false,
  created_at timestamptz default now()
);

create index if not exists recipes_custom_idx on recipes (custom);
create index if not exists recipes_title_idx on recipes (title);

create table if not exists feedback (
  id bigserial primary key,
  chat_id bigint not null,
  recipe_id uuid references recipes(id) on delete cascade,
  kind text not null check (kind in ('cooked', 'liked', 'failed')),
  created_at timestamptz default now()
);

create index if not exists feedback_chat_idx on feedback (chat_id, created_at desc);

create table if not exists chat_state (
  chat_id bigint primary key,
  payload jsonb not null default '{}',
  updated_at timestamptz default now()
);

create table if not exists learned_phrases (
  id bigserial primary key,
  pattern text unique not null,
  example text,
  parsed jsonb not null,
  hits int default 1,
  created_at timestamptz default now()
);

create table if not exists pantry (
  id bigserial primary key,
  chat_id bigint not null,
  name text not null,
  qty numeric,
  unit text,
  updated_at timestamptz default now(),
  unique (chat_id, name)
);
