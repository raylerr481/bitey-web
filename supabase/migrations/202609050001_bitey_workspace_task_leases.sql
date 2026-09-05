-- Durable workspace task leases for Bitey IA.
-- The backend uses the Supabase service role for these server-side RPCs.
-- Functions are deliberately not exposed to anon/authenticated callers.

alter table public.workspace_tasks
  add column if not exists execution_token text,
  add column if not exists started_at timestamptz,
  add column if not exists completed_at timestamptz;

create index if not exists workspace_tasks_running_stale_idx
  on public.workspace_tasks(status, updated_at)
  where status = 'running';

create or replace function public.claim_workspace_task(
  p_workspace_id uuid,
  p_task_id uuid,
  p_execution_token text
)
returns boolean
language plpgsql
security invoker
set search_path = public
as $$
begin
  if p_workspace_id is null or p_task_id is null or nullif(trim(p_execution_token), '') is null then
    return false;
  end if;

  update public.workspace_tasks
     set status = 'running',
         execution_token = p_execution_token,
         started_at = coalesce(started_at, now()),
         completed_at = null,
         updated_at = now()
   where id = p_task_id
     and workspace_id = p_workspace_id
     and status = 'queued'
     and execution_token is null;

  return found;
end;
$$;

create or replace function public.finish_workspace_task(
  p_workspace_id uuid,
  p_task_id uuid,
  p_execution_token text,
  p_status text
)
returns boolean
language plpgsql
security invoker
set search_path = public
as $$
begin
  if p_workspace_id is null or p_task_id is null or nullif(trim(p_execution_token), '') is null then
    return false;
  end if;

  if p_status not in ('completed', 'needs_review', 'failed') then
    return false;
  end if;

  update public.workspace_tasks
     set status = p_status,
         completed_at = now(),
         updated_at = now()
   where id = p_task_id
     and workspace_id = p_workspace_id
     and status = 'running'
     and execution_token = p_execution_token;

  return found;
end;
$$;

revoke execute on function public.claim_workspace_task(uuid, uuid, text) from public, anon, authenticated;
revoke execute on function public.finish_workspace_task(uuid, uuid, text, text) from public, anon, authenticated;
grant execute on function public.claim_workspace_task(uuid, uuid, text) to service_role;
grant execute on function public.finish_workspace_task(uuid, uuid, text, text) to service_role;
