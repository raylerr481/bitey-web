-- Bitey IA Workspace: Skywork-style project/task/artifact layer.
-- Supabase remains the canonical persistence layer; no new database platform is introduced.

create table if not exists public.workspaces (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  description text not null default '',
  mode text not null default 'general',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.workspace_tasks (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  title text not null,
  prompt text not null default '',
  capability text not null default 'chat',
  status text not null default 'queued',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.workspace_artifacts (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  name text not null,
  artifact_type text not null default 'document',
  status text not null default 'draft',
  content text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists workspace_tasks_workspace_idx on public.workspace_tasks(workspace_id, created_at desc);
create index if not exists workspace_artifacts_workspace_idx on public.workspace_artifacts(workspace_id, updated_at desc);

comment on table public.workspaces is 'Bitey IA persistent workspaces; general cognitive workspace, not a separate brain.';
comment on table public.workspace_tasks is 'Bounded work units routed by Bitey Cognitive Core.';
comment on table public.workspace_artifacts is 'Generated or user-created workspace artifacts such as documents, slides, sheets and code.';
