# Redis Production Plan

## Current State

Redis is used **exclusively for rate limiting** (sliding window via sorted sets at `app/middleware/rate_limit.py:40-68`). The `get_redis()` singleton at `app/core/redis.py` reads `REDIS_URL` from the environment.

When Redis is unavailable (connection fails or `REDIS_URL` is empty), the rate limiter falls back to `InMemoryRateLimiter` — acceptable for single-instance dev but **not safe for production**:
- **No cross-instance state** — if you horizontally scale to >1 server, each has its own counter, so 3 instances each allow 100 req/min = 300/min effective cap.
- **Lost on restart** — in-memory counters reset after every deploy.
- **Memory leak risk** — no TTL-like pruning beyond what `check()` does on access.

## Current Config

```
REDIS_URL=redis://localhost:6379/0
```

Works in Docker Compose (service `redis:7-alpine` spins up next to the app). Fails in bare-metal / cloud deployment where no local Redis exists.

## Options

### Option A: Upstash Redis (Recommended)

**Profile:** Serverless Redis, 10 MB free tier, $0.30/GB-month after.
**Why:** No server to manage, supports `redis://` protocol via TLS, global replication, free tier covers rate limiting for any college-sized app.
**Integration:** `REDIS_URL=rediss://default:<token>@<region>.upstash.io:6379` — `redis-py` connects directly, zero code changes.
**Effort:** 5 minutes (sign up → create db → copy URL → set env var).

### Option B: Redis Cloud (by Redis)

**Profile:** 30 MB free tier, managed by Redis Ltd.
**Why:** Larger free tier, same `rediss://` protocol, well-known provider.
**Trade-off:** Slightly more restrictive rate limits on free tier, requires credit card.
**Effort:** 10 minutes.

### Option C: Vercel KV (if on Vercel)

**Profile:** Baked into Vercel ecosystem, uses Upstash under the hood.
**Why:** If the app is already on Vercel, zero-signup integration.
**Trade-off:** Ties you to Vercel. Not applicable if deploying elsewhere.
**Effort:** 2 minutes (enable KV in Vercel dashboard).

### Option D: Keep in-memory fallback (single-instance only)

**Profile:** No external service, zero cost.
**Why:** Fine if you only ever run 1 server instance and accept counter resets on deploy.
**Trade-off:** No horizontal scaling, counters reset on every restart.
**Effort:** Zero.

### Option E: Self-hosted Redis on VPS

**Profile:** Run `redis:7-alpine` on your VM, same as Docker Compose.
**Why:** Full control, no third-party dependency.
**Trade-off:** You manage backups, patching, monitoring, RAM limits.
**Effort:** 30 minutes + ongoing maintenance.

## Recommended Path

**Go with Option A (Upstash Redis) unless you're on Vercel (then Option C).**

| Criterion | Upstash | Redis Cloud | Vercel KV | In-memory | Self-hosted |
|---|---|---|---|---|---|
| Free tier | 10 MB | 30 MB | n/a (billed) | ∞ | ∞ |
| Zero ops | ✓ | ✓ | ✓ | ✓ | ✗ |
| Horizontal scale | ✓ | ✓ | ✓ | ✗ | ✓ |
| TLS built-in | ✓ | ✓ | ✓ | — | manual |
| Setup time | 5m | 10m | 2m | 0 | 30m |

## Implementation Steps (for Upstash)

1. **Sign up** at https://upstash.com (no credit card for free tier).
2. **Create a Redis database** — select `ap-northeast-1` region to match Supabase (reduces latency).
3. **Copy the `REDIS_URL`** — it looks like `rediss://default:<token>@<region>.upstash.io:6379`.
4. **Set as env var** in your deployment environment (not in `.env`):
   ```
   REDIS_URL=rediss://default:<token>@ap1-adequate-marmot-12345.upstash.io:6379
   ```
5. **Verify** — start the app, check the startup log says `"Redis client initialized — rate limiter will use Redis backend"`.
6. **Test rate limiting** — hit a protected endpoint 101 times in 60s, confirm 429 on the 101st.

## Fallback Behavior

If `REDIS_URL` is absent or the connection fails, the app degrades gracefully to in-memory. This is acceptable during development but should log a warning so you catch it before production.
