# Celery Worker Sequential Processing Bottleneck

**Date:** 2026-02-03
**Status:** Resolved
**Severity:** High
**Component:** Celery Worker Configuration

## Problem Description

When multiple documents are submitted for processing, they are processed sequentially instead of concurrently. This causes significant delays:

- 2 documents × 30 seconds each = 60 seconds total (sequential)
- 10 documents × 30 seconds each = 5 minutes total (sequential)

Users experience long wait times when submitting multiple documents, even though the server has capacity to handle concurrent requests.

## Root Cause Analysis

### 1. Solo Pool Configuration

The Celery worker was configured with `--pool=solo`:

```javascript
// ecosystem.config.js (line 74)
args: '-m celery -A app.tasks.celery_app worker --loglevel=info --pool=solo',
```

**Solo pool characteristics:**
- Single-threaded, synchronous task execution
- Only ONE task can run at a time
- Next task waits for current task to complete entirely

### 2. Single Worker Instance

```javascript
instances: 1,  // Only one worker process
```

Combined with solo pool, this means absolute sequential processing.

### 3. Low Prefetch Multiplier

```python
# celery_app.py (line 27)
worker_prefetch_multiplier=1,
```

Worker fetches only 1 task at a time, preventing any queue optimization.

## Key Insight: I/O-Bound Workload

Document extraction tasks are **I/O-bound**, not CPU-bound:

```
Task Timeline:
├── Send request to LLM API    (~0.5s)
├── Wait for LLM response      (~25s)  ← 80% of time spent WAITING
├── Process response           (~2s)
└── Save to database           (~0.5s)
```

The worker spends most of its time waiting for external API responses, using minimal CPU and memory. This is ideal for **concurrent I/O handling**.

## Solution

### Attempt 1: Gevent Pool (Failed)

Initially tried gevent for I/O-bound efficiency:

```javascript
args: '--pool=gevent --concurrency=20'
```

**Problem:** Tasks use `asyncio.run()` which conflicts with gevent's event loop:
```
RuntimeError: asyncio.run() cannot be called from a running event loop
```

Files using `asyncio.run()`:
- `app/tasks/extractor.py` (4 locations)
- `app/tasks/markdown_extractor.py`
- `app/tasks/markdown_generator.py`
- `app/tasks/email_tasks.py` (4 locations)

### Attempt 2: Prefork Pool (Success)

Switched to prefork (process-based) pool which avoids event loop conflicts:

```javascript
// ecosystem.config.js - FINAL
args: '-m celery -A app.tasks.celery_app worker --loglevel=info --pool=prefork --concurrency=2',
max_memory_restart: '900M',
```

**Why concurrency=2:**
- Matches CPU cores (2 vCPU)
- Each worker process uses ~300-500MB
- Total ~640MB fits within memory limits
- 4 workers caused memory pressure (2.5GB+ used)

### 2. Increase Prefetch Multiplier

```python
# celery_app.py
worker_prefetch_multiplier=4,  # Allow prefetching for better queue throughput
```

## Files Changed

| File | Change |
|------|--------|
| `ecosystem.config.js` | Changed pool from `solo` to `prefork --concurrency=2` |
| `app/tasks/celery_app.py` | Increased `worker_prefetch_multiplier` from 1 to 4 |
| `pyproject.toml` | Added `gevent` dependency (unused, can be removed) |

## Lessons Learned

### Gevent + Asyncio Incompatibility

Gevent and asyncio don't mix well. If your tasks use `asyncio.run()`, you cannot use gevent pool.

**Options when tasks use asyncio:**
1. **Prefork pool** (recommended) - Each worker is a separate process, no event loop conflict
2. **`nest_asyncio`** - Patches asyncio to allow nested loops (adds complexity)
3. **Refactor to sync** - Remove asyncio (not practical for async APIs)

## Server Constraints

Analysis of production server (2026-02-03):

| Resource | Value | Implication |
|----------|-------|-------------|
| CPU | 2 cores (Xeon 2.2GHz) | Limited parallelism |
| RAM | 3.8GB total | Must be conservative |
| Available RAM | ~2.1GB | Tight budget |
| Swap | 1GB (heavily used) | Memory pressure exists |

**Decision:** Set concurrency=20 (not 50) to avoid memory pressure.

## Performance Comparison

| Scenario | Before (solo) | After (prefork-2) | Improvement |
|----------|---------------|-------------------|-------------|
| 1 document | 30s | 30s | Same |
| 2 documents | 60s | ~30s | 2x faster |
| 4 documents | 120s | ~60s | 2x faster |
| 10 documents | 300s | ~150s | 2x faster |

**Note:** With prefork-2, throughput is 2x the solo pool. For higher concurrency,
the server would need more RAM (8GB+ recommended for prefork-4 or gevent).

## Why Not Other Solutions?

### Prefork Pool (Multiple Processes)
- Each process uses ~200MB memory
- 4 workers = 800MB just for Celery
- Good for CPU-bound tasks, overkill for I/O-bound

### Multiple Worker Instances (PM2)
- Same memory concern as prefork
- Harder to manage/monitor
- Gevent achieves same result with less overhead

### Serverless (Lambda)
- Charges by duration (GB-seconds)
- Waiting 25s for LLM = paying for 25s of idle time
- Cost-inefficient for I/O-bound waiting

## Deployment

```bash
# Restart the Celery worker to apply changes
pm2 restart ai-document-processing-celery-worker

# Verify gevent pool is active
pm2 logs ai-document-processing-celery-worker --lines 20
# Should show: "celery@hostname ready" with gevent pool
```

## Monitoring

Watch for:
- Memory usage staying under 600MB for Celery worker
- Total system memory not exceeding 3GB (leave buffer)
- No greenlet exhaustion warnings
- Task completion times remaining consistent

### Tuning Guide

| Server RAM | Recommended Concurrency |
|------------|------------------------|
| 2GB | 10 |
| 4GB | 20 |
| 8GB | 50 |
| 16GB+ | 100+ |

Current server (3.8GB) → concurrency=20 is appropriate.

## Related Documentation

- [Celery Concurrency Documentation](https://docs.celeryq.dev/en/stable/userguide/concurrency/index.html)
- [Gevent Pool Best Practices](https://docs.celeryq.dev/en/stable/userguide/concurrency/gevent.html)
- [Stateless Job Processing Architecture](../docs/architecture/2025-11-02-stateless-job-processing.md)
