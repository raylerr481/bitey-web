-- Bitey IA independent cognitive architecture.
-- This registry describes cognition independently from any external LLM/provider.

create table if not exists public.bitey_cognitive_architectures (
  id bigint generated always as identity primary key,
  architecture_key text not null unique,
  version text not null,
  status text not null default 'active',
  description text,
  stages jsonb not null default '[]'::jsonb,
  policies jsonb not null default '{}'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_bitey_cognitive_architectures_status
  on public.bitey_cognitive_architectures(status);

alter table public.bitey_cognitive_architectures enable row level security;

insert into public.bitey_cognitive_architectures
  (architecture_key, version, status, description, stages, policies, metadata)
values
  (
    'bitey-independent-cognitive-core',
    '1.0.0',
    'active',
    'Provider-independent cognitive architecture for Bitey IA.',
    '[
      {"order":1,"key":"perception","purpose":"normalize and understand the incoming interaction"},
      {"order":2,"key":"intention","purpose":"infer domain, intent and constraints"},
      {"order":3,"key":"context","purpose":"assemble conversation, memory and available evidence"},
      {"order":4,"key":"planning","purpose":"select a cognitive plan and specialized capability"},
      {"order":5,"key":"evidence","purpose":"retrieve or validate evidence when required"},
      {"order":6,"key":"risk","purpose":"apply safety, permission and execution boundaries"},
      {"order":7,"key":"decision","purpose":"select response, tool or module action"},
      {"order":8,"key":"generation","purpose":"use native cognition or an external model for language generation"},
      {"order":9,"key":"evaluation","purpose":"score outcome and detect contradictions or failure"},
      {"order":10,"key":"memory_learning","purpose":"persist useful experience and update mastery"}
    ]'::jsonb,
    '{
      "cost_mode":"free_only",
      "external_models_optional":true,
      "native_fallback_required":true,
      "financial_live_execution":"disabled",
      "news_auto_execution":"disabled",
      "secrets_never_persisted_as_plaintext":true
    }'::jsonb,
    '{"owner":"bitey_ia","role":"independent_cognitive_architecture","provider_agnostic":true}'::jsonb
  )
on conflict (architecture_key) do update set
  version = excluded.version,
  status = excluded.status,
  description = excluded.description,
  stages = excluded.stages,
  policies = excluded.policies,
  metadata = excluded.metadata,
  updated_at = now();

-- Register the native model in the existing model registry without storing credentials.
insert into public.bitey_ai_models
  (company_id, provider, model_name, transport, endpoint_url, credential_env, capabilities, cost_class, priority, enabled, metadata)
select
  null,
  'bitey_native',
  'bitey-native-cognitive-v1',
  'in_process',
  null,
  null,
  '["perception","intent","planning","risk","decision","fallback","multilingual"]'::jsonb,
  'free',
  1000,
  true,
  '{"independent":true,"network_required":false,"api_key_required":false,"architecture":"bitey-independent-cognitive-core"}'::jsonb
where not exists (
  select 1 from public.bitey_ai_models
  where provider = 'bitey_native' and model_name = 'bitey-native-cognitive-v1'
);
