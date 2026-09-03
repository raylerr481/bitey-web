-- Bitey IA cognitive schema security baseline
-- IMPORTANT: review and apply in the dedicated Bitey IA Supabase project only.
-- Do NOT apply this file to the BiteFixes Supabase project.
-- Enabling RLS without policies intentionally blocks client-role access.

alter table bitey.cognitive_sessions enable row level security;
alter table bitey.memories enable row level security;
alter table bitey.knowledge_nodes enable row level security;
alter table bitey.knowledge_edges enable row level security;
alter table bitey.evidence enable row level security;
alter table bitey.evaluations enable row level security;
alter table bitey.capabilities enable row level security;
alter table bitey.providers enable row level security;
alter table bitey.learning_events enable row level security;
alter table bitey.module_contracts enable row level security;

-- No anon/authenticated policies are created here.
-- Bitey backend access uses the server-side service-role key.
-- Add narrowly scoped policies later only if a client must read a specific view.
