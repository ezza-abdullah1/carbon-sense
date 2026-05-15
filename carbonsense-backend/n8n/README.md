# n8n Workflows — CarbonSense Recommendations

Three workflows live in this directory, mapped to the three jobs n8n owns in
the new recommendation pipeline:

| File | Trigger | Purpose |
|------|---------|---------|
| `workflow_generate_recommendations.json` | Webhook `POST /webhook/generate-recs` | Cache lookup → embed query → pgvector retrieval → re-rank → Claude Sonnet 4.6 via OpenRouter → cache write → respond |
| `workflow_weekly_scraper.json` | Cron `0 2 * * 0` (Sun 02:00 UTC) | Fetch policy URLs → parse → chunk → embed → upsert into `policy_chunks` |
| `workflow_feedback.json` | Webhook `POST /webhook/feedback` | Validate → derive `anon_id` → upsert into `recommendation_feedback` → Slack alert on low ratings |

## 1. Prerequisites

1. **Supabase project** with the schema in
   `carbonsense-backend/supabase/migrations/0001_init.sql` applied. Get the
   project URL and the **service role** key (not the anon key — service role
   bypasses RLS).
2. **OpenAI API key** for `text-embedding-3-small`.
3. **OpenRouter API key** with credit/limits for `anthropic/claude-sonnet-4-6`.
4. **(Optional) Slack incoming webhook URL** for low-rating alerts.

## 2. Seed the data corpus first

Before running the generate workflow, populate `data_chunks` with the existing
JSON datasets. From the Django backend root:

```bash
pip install -r requirements.txt
cp .env.example .env  # then fill in SUPABASE_*, OPENAI_API_KEY
python manage.py seed_data_chunks --dry-run        # sanity check
python manage.py seed_data_chunks                  # real run, ~700 chunks, ~$0.01
```

This is a one-time setup. Re-run only if the underlying JSON files change.

## 3. Import the workflows into n8n

In your n8n instance:

1. Click **Workflows → Import from File** and load each `.json` in this
   directory.
2. Set the following **environment variables** at the n8n instance level
   (Settings → Variables or via env on self-hosted):

   | Name | Value |
   |------|-------|
   | `CARBONSENSE_SHARED_SECRET` | Same value as Django's `N8N_SHARED_SECRET`. Used for header auth on webhooks. |
   | `SUPABASE_URL` | `https://<project-ref>.supabase.co` |
   | `SUPABASE_SERVICE_KEY` | Supabase service role key |
   | `OPENAI_API_KEY` | `sk-…` |
   | `OPENROUTER_API_KEY` | `sk-or-v1-…` |
   | `FEEDBACK_DAILY_SALT_PREFIX` | Any random string, e.g. `cs-anon-2026` |
   | `SLACK_WEBHOOK_URL` | (optional) for `workflow_feedback.json` |

3. **Activate** each workflow. The webhooks publish at:
   - `https://<your-n8n-host>/webhook/generate-recs`
   - `https://<your-n8n-host>/webhook/feedback`

   (During testing use `/webhook-test/` URLs that n8n shows in the editor —
   those only fire while the editor is open.)

## 4. Point Django at n8n

In `carbonsense-backend/.env`:

```env
RECOMMENDATIONS_BACKEND=n8n
N8N_WEBHOOK_BASE=https://<your-n8n-host>/webhook
N8N_SHARED_SECRET=<same value as CARBONSENSE_SHARED_SECRET above>
```

Then run the Django migration so the local feedback buffer table exists:

```bash
python manage.py migrate recommendations
```

## 5. Smoke test

```bash
# Should hit n8n, retrieve from pgvector, call Claude, return six-key JSON
curl -X POST http://localhost:8000/api/recommendations/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "area_id": "gulberg_transport",
    "area_name": "Gulberg",
    "sector": "transport",
    "coordinates": {"lat": 31.5204, "lng": 74.3587}
  }'

# Submit feedback (run_id comes from the response above)
curl -X POST http://localhost:8000/api/recommendations/feedback \
  -H 'Content-Type: application/json' \
  -d '{
    "run_id": "<uuid-from-prev-response>",
    "rating": 4,
    "helpful_action_indices": [0, 2],
    "feedback_text": "BRT extension recommendation was spot on"
  }'
```

## 6. Operational notes

### Cost guardrails

- The generate workflow checks the Supabase cache **first**. Cache TTL is
  30 days. Tune `expires_at` in the "Cache write" node if you want longer.
- Claude Sonnet is configured with `max_tokens: 1800`, `temperature: 0.4`,
  and prompt caching via `cache_control: ephemeral` on the static system +
  framework blocks. On a cache hit Anthropic charges 10% of normal input
  cost for the cached portion.
- The scraper dedupes by `content_hash` before embedding, so re-running the
  weekly cron over unchanged sources costs nothing.

### Cache lookup RPC

The generate workflow optionally calls a Supabase RPC named `cache_lookup`.
Create it if you want server-side cache checks (otherwise the workflow still
works — the `IF Cache hit?` branch just always falls through to fresh
generation, and the cache write at the end still populates the table for
future requests through the Django cache table):

```sql
create or replace function cache_lookup(p_area_id text, p_sector text)
returns table (id uuid, response jsonb)
language sql stable as $$
  select id, response
  from recommendation_runs
  where area_id = p_area_id
    and sector  = p_sector
    and expires_at > now()
  order by generated_at desc
  limit 1;
$$;
```

### Anonymity model

- The Django view computes `anon_id = sha256(ip + user_agent + daily_salt)`
  before forwarding. n8n's `Validate + derive anon_id` node recomputes it if
  the field is missing, so direct calls to the webhook are also anonymous.
- The salt rotates daily, so the same browser cannot be linked across days.
- The unique index `(run_id, anon_id)` plus `Prefer: resolution=merge-duplicates`
  lets a user upgrade their rating (3★ → 5★) but blocks vote spam in a day.

### Scraper TODO

The `workflow_weekly_scraper.json` PDF branch is stubbed. To actually parse
PDFs:

1. Insert an **Extract from File** node between **Fetch URL** and **Parse +
   chunk** for the PDF branch (set "operation: Extract Text from PDF").
2. Or replace the whole fetch+parse with the dedicated **HTTP → Extract from
   File** combo n8n ships, feeding plain text into the chunker.

### Failure modes

| Symptom | Cause | Action |
|---------|-------|--------|
| Django returns `template_fallback` | n8n unreachable, secret mismatch, or `RECOMMENDATIONS_BACKEND ≠ 'n8n'` | Check n8n execution log; verify `X-Carbonsense-Token` matches both sides |
| LLM call times out | Claude Sonnet is slow on long retrieved evidence | Lower `max_tokens` to 1500 or truncate chunks more aggressively in the re-rank node |
| Empty `policy_block` in prompts | `policy_chunks` is empty | Run the scraper workflow manually to backfill, or add more URLs to the Source list |
| Feedback buffered locally | Django couldn't reach n8n | Write a periodic management command that re-POSTs rows where `forwarded_to_n8n=False` |
