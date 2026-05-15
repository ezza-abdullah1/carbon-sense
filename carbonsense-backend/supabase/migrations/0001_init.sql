-- ============================================================================
-- CarbonSense Supabase schema — RAG corpus + recommendation cache + feedback
-- ----------------------------------------------------------------------------
-- Run this against your Supabase project's SQL editor (or via the Supabase
-- CLI: `supabase db push`). Idempotent: safe to re-run.
-- ============================================================================

create extension if not exists vector;
create extension if not exists pgcrypto;

-- ----------------------------------------------------------------------------
-- 1. Scraped policy documents (filled by n8n weekly scraper workflow)
-- ----------------------------------------------------------------------------
create table if not exists policy_chunks (
  id              uuid primary key default gen_random_uuid(),
  source_url      text not null,
  source_title    text,
  source_org      text,
  geo_scope       text,                       -- lahore | punjab | pakistan | south-asia | global
  sector_tags     text[] default '{}'::text[],
  framework_tags  text[] default '{}'::text[],-- paris | c40 | sbti | ipcc-ar6 | unep | iea
  chunk_index     int,
  chunk_text      text not null,
  content_hash    text not null,              -- sha256(chunk_text), used for dedupe
  embedding       vector(1536),               -- text-embedding-3-small
  metadata        jsonb default '{}'::jsonb,
  scraped_at      timestamptz default now(),
  unique (source_url, chunk_index)
);

create index if not exists policy_chunks_embedding_idx
  on policy_chunks using ivfflat (embedding vector_cosine_ops) with (lists = 100);
create index if not exists policy_chunks_geo_idx on policy_chunks(geo_scope);
create index if not exists policy_chunks_sector_idx
  on policy_chunks using gin(sector_tags);
create index if not exists policy_chunks_content_hash_idx
  on policy_chunks(content_hash);

-- ----------------------------------------------------------------------------
-- 2. Emission data corpus (filled by `python manage.py seed_data_chunks`)
-- ----------------------------------------------------------------------------
create table if not exists data_chunks (
  id              uuid primary key default gen_random_uuid(),
  source_dataset  text not null,              -- transport_v16 | buildings_v15 | waste_v2_3 | spatial_v1.2
  uc_code         text,
  uc_name         text,
  sector          text,                       -- transport | buildings | waste | aggregate
  chunk_type      text,                       -- uc_profile | sector_total | risk_summary | peer_band
  chunk_text      text not null,
  numeric_facts   jsonb default '{}'::jsonb,
  embedding       vector(1536),
  ingested_at     timestamptz default now(),
  unique (source_dataset, uc_code, sector, chunk_type)
);

create index if not exists data_chunks_embedding_idx
  on data_chunks using ivfflat (embedding vector_cosine_ops) with (lists = 50);
create index if not exists data_chunks_uc_idx on data_chunks(uc_name);
create index if not exists data_chunks_sector_idx on data_chunks(sector);

-- ----------------------------------------------------------------------------
-- 3. Recommendation runs (cache + audit trail)
-- ----------------------------------------------------------------------------
create table if not exists recommendation_runs (
  id                       uuid primary key default gen_random_uuid(),
  area_id                  text not null,
  area_name                text not null,
  sector                   text not null,
  coordinates              jsonb,
  emissions_summary        jsonb,
  retrieved_chunk_ids      uuid[] default '{}'::uuid[],
  retrieved_data_chunk_ids uuid[] default '{}'::uuid[],
  prompt_used              text,
  response                 jsonb not null,
  llm_model                text,
  source                   text default 'n8n-rag',
  generated_at             timestamptz default now(),
  expires_at               timestamptz
);

create index if not exists recommendation_runs_lookup_idx
  on recommendation_runs(area_id, sector, expires_at desc);

-- ----------------------------------------------------------------------------
-- 4. Anonymous feedback
-- ----------------------------------------------------------------------------
create table if not exists recommendation_feedback (
  id                       uuid primary key default gen_random_uuid(),
  run_id                   uuid references recommendation_runs(id) on delete cascade,
  rating                   int check (rating between 1 and 5),
  feedback_text            text,
  helpful_action_indices   int[] default '{}'::int[],
  unhelpful_action_indices int[] default '{}'::int[],
  anon_id                  text not null,     -- sha256(ip + ua + daily_salt)
  submitted_at             timestamptz default now()
);

create unique index if not exists recommendation_feedback_unique_voter
  on recommendation_feedback(run_id, anon_id);

-- ----------------------------------------------------------------------------
-- 5. Hybrid retrieval: returns policy + data chunks in one call
-- ----------------------------------------------------------------------------
create or replace function match_chunks(
  query_embedding vector(1536),
  policy_count    int default 8,
  data_count      int default 4,
  geo_filter      text default null,
  sector_filter   text default null
) returns table (
  source       text,
  id           uuid,
  chunk_text   text,
  meta         jsonb,
  similarity   float
) language plpgsql stable as $$
begin
  return query
  (
    select 'policy'::text as source,
           pc.id,
           pc.chunk_text,
           jsonb_build_object(
             'title', pc.source_title,
             'org',   pc.source_org,
             'url',   pc.source_url,
             'geo',   pc.geo_scope,
             'sectors', pc.sector_tags,
             'frameworks', pc.framework_tags
           ) as meta,
           (1 - (pc.embedding <=> query_embedding))::float as similarity
    from policy_chunks pc
    where (geo_filter is null
           or pc.geo_scope = geo_filter
           or pc.geo_scope = 'global')
      and (sector_filter is null
           or sector_filter = any(pc.sector_tags))
    order by pc.embedding <=> query_embedding
    limit policy_count
  )
  union all
  (
    select 'data'::text as source,
           dc.id,
           dc.chunk_text,
           jsonb_build_object(
             'uc',      dc.uc_name,
             'uc_code', dc.uc_code,
             'sector',  dc.sector,
             'type',    dc.chunk_type,
             'facts',   dc.numeric_facts
           ) as meta,
           (1 - (dc.embedding <=> query_embedding))::float as similarity
    from data_chunks dc
    where (sector_filter is null
           or dc.sector = sector_filter
           or dc.sector = 'aggregate')
    order by dc.embedding <=> query_embedding
    limit data_count
  );
end;
$$;

-- ----------------------------------------------------------------------------
-- 6. Optional: row-level security defaults (lock down public access)
-- ----------------------------------------------------------------------------
alter table policy_chunks            enable row level security;
alter table data_chunks              enable row level security;
alter table recommendation_runs      enable row level security;
alter table recommendation_feedback  enable row level security;

-- Service-role key bypasses RLS automatically. The anon key gets no access by
-- default — n8n and Django should authenticate with the service role key.
