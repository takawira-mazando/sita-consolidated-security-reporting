# Vector Dataset Design — RBAC-Scoped Semantic Retrieval over the Warehouse

**Document ID:** G2-VEC-R1 · **Prepared:** 6 October 2026
**Status:** Design. Not built. Nothing in this document has been implemented.
**Parent addendum:** Addendum B Phase 13 (AI Report Generation) · `HOSI-UNIFIED` flight plan Phases 1-12
**Verification method:** every claim below was executed against the live `sita` instance on 6 October 2026.

---

## 1. What is being asked for

A **vector dataset** over the data warehouse, so that AI report generation can retrieve supporting evidence *semantically* rather than only by exact key — and the retrieval must be **strictly constrained by the caller's RBAC claims and tenant scope**.

In one line: **every vector row must be readable by exactly the same set of callers who can read the row it was derived from. No more, no fewer.**

---

## 2. The finding that governs the whole design

A vector dataset is a **second copy of warehouse data**, and it is a copy with a specific, dangerous property:

> **You cannot audit an embedding.** A leaked department name is visible in a `SELECT`. A leaked department name embedded in a 1024-dimension float vector is not — it is recoverable by inversion or nearest-neighbour probing, and no reviewer scanning the table will ever notice.

The existing compliance problem is that `compliance_snapshots` and `compliance_gaps` have **no tenancy columns**, so nothing can scope them (684 rows, verified). A vector dataset built naively reproduces that defect **and removes the ability to detect it**.

Therefore the governing rule:

> **Tenancy is stamped onto every vector row at write time, permanently. Retrieval filters on the stamp before ranking. It is never reconstructed, joined in, or inferred at query time.**

### 2.1 Filter-then-rank, never rank-then-filter

This is the single most important line in the design.

```
✅ CORRECT                                  ❌ WRONG
WHERE department_id IN (:scope)              SELECT ... ORDER BY embedding <=> :q LIMIT 50
ORDER BY embedding <=> :q LIMIT 50           -- then filter in Python
```

Rank-then-filter leaks in three ways even when the final output looks correct:

1. **Row-count oracle.** If the top-50 globally-nearest contains 40 out-of-scope rows, the scoped user sees 10. Repeating with varied queries reveals the size and density of other tenants' corpora. **Demonstrated on this database** — see the benchmark in §4.1: 2 of the global top-50 were out-of-scope.
2. **Semantic inference.** "What does Home Affairs' payment gateway look like" returns a Home Affairs vector at rank 1. If the scoped user sees *nothing*, they have learned the row exists — which is itself a disclosure about another department.
3. **Timing.** Distance computation over a corpus you cannot see is measurable.

Post-filtering in application code has a fourth failure mode: it is one `if` statement away from being deleted, and no test will fail when it is.

---

## 3. Verified state of the corpus — 6 October 2026

### 3.1 pgvector is not available

```
PostgreSQL 18.1, localhost:5432, database sita
  installed extensions      : plpgsql
  pg_available_extensions  : cube (1.5), earthdistance (1.2)
  vector                   : ABSENT
```

**`pgvector` cannot be assumed.** Any design that depends on `CREATE EXTENSION vector` is blocked on a server-level package install this team does not control. Section 7 gives the fallback.

### 3.2 Candidate corpus and its tenancy integrity

| Table | Rows | `department_id` NULL | `branch_id` NULL |
|---|---:|---:|---:|
| `warehouse.findings` | 2 244 | **207** | 319 |
| `warehouse.risk_scores` | 15 283 | 0 | 6 750 |
| `warehouse.alerts` | 551 | 0 | 219 |
| `warehouse.api_endpoints` | 2 752 | 0 | 1 469 |
| `warehouse.database_inventory` | 2 577 | — | — |

**207 findings rows have no department at all** — 202 from `source=compliance` with `app_name='unknown'`, plus 5 AppScan rows for one Home Affairs portal. These rows are unreachable by *every* scoped caller, because `tenant_filter()` requires `department_id IN (...)`. They are not "estate-wide data" — they are unattributed.

**8 550 rows across the four tables have a department but no branch.** For a branch-scoped caller, `AND(department_id IN (…), branch_id IN (…))` excludes them. Fail-closed is the correct behaviour, but it means branch admins see materially less than department admins, and the vector dataset must reproduce that asymmetry exactly rather than "helpfully" filling the gap.

### 3.3 The k-anonymity problem is severe

```
departments with fewer than 5 findings : 112 of 172
smallest cohorts                       : ec-public-works 1, ec-premier 1,
                                         ec-cogta 1, ec-health 1, ec-education 1
```

**112 of 172 departments have under 5 findings.** With a k-anonymity floor of 5 — the same floor G1 §5.2 requires for the copilot — **two thirds of the estate cannot have a per-department vector corpus at all.**

This is the finding that decides the granularity, and it is counter-intuitive: vectorising *per department* is the obvious design and it is the wrong one here.

### 3.4 The text is too short to embed meaningfully

```
findings.description : mean 37 chars, max 124
alerts.description   : mean 30 chars, max  40
```

Thirty-seven characters is roughly one clause. An embedding of "Reflected XSS in login form" is dominated by the words *XSS* and *login* — a lexical signal that exact-match `ILIKE` retrieves faster, more accurately, and without an inference call. **The semantic benefit does not currently exist for this corpus.**

### 3.5 PII surface

`warehouse.findings.raw_data` is populated on **all 2 244 rows** — the complete OEM payload. It is the single largest PII risk in the warehouse and G1 §5.2 already forbids sending it to any model. It must never enter a vector dataset either.

---

## 4. Design

### 4.1 Storage — `ai` schema, partitioned by stamp

```sql
CREATE SCHEMA IF NOT EXISTS ai;

-- pgvector path (requires CREATE EXTENSION vector, currently unavailable)
CREATE TABLE ai.embedding (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_table    varchar(40)  NOT NULL,
    source_id       varchar(36)  NOT NULL,

    -- TENANCY STAMP. Written once, never updated, never derived.
    department_id   varchar(36)  NOT NULL,
    branch_id       varchar(36),
    ministry_id     varchar(36),
    cluster_id      varchar(36),
    scope_hash      varchar(80)  NOT NULL,   -- the caller's scope this row is visible to
    disclosure_class varchar(32) NOT NULL DEFAULT 'tenant_scoped',

    chunk_text      text         NOT NULL,
    token_count     integer      NOT NULL,
    embedding       <vector>     NOT NULL,
    embedding_model varchar(100) NOT NULL,   -- pinned, never floating
    embedding_dim   integer      NOT NULL,

    created_at      timestamptz  NOT NULL DEFAULT now(),
    UNIQUE (source_table, source_id, chunk_no)
);

-- Mandatory index: every retrieval path filters on the stamp FIRST.
CREATE INDEX ai_embedding_scope_idx  ON ai.embedding (scope_hash);
CREATE INDEX ai_embedding_dept_idx   ON ai.embedding (department_id, branch_id);
-- Ann index is created per partition or with iterative scans. A single global
-- HNSW index over mixed-tenant rows is FORBIDDEN: it makes rank-then-filter
-- the only efficient plan, which is the leak.
```

**Fallback when pgvector is unavailable** — and this is the *recommended* POC path.

First, a correction. I initially claimed Postgres has a native array-distance operator (`<#>`). **It does not.** Tested directly against PostgreSQL 18.1 on 6 Oct 2026:

```
SELECT ARRAY[1,0,0] <#> ARRAY[0,1,0]   -> ProgrammingError (operator does not exist)
SELECT ARRAY[1,0,0] <-> ARRAY[0,1,0]   -> ProgrammingError
```

The working primitive is `unnest` with a pairwise sum of squares, which needs **no extension at all**:

```sql
CREATE TABLE ai.embedding (
    ... same columns ...
    embedding real[] NOT NULL          -- float32, from numpy
);

-- Exact L2, filter-first. sqrt() is applied only to the aggregate, so the
-- ordering key is the unsqrted sum of squares.
CREATE FUNCTION ai.embedding_l2(a real[], b real[]) RETURNS double
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT sqrt(sum((x - y) * (x - y)))
    FROM unnest(a) x, unnest(b) y;
$$;
```

**Measured on a 6 000-row stand-in with the real query shapes** (same database, same session):

| Query shape | Latency | Rows |
|---|---:|---:|
| **filter-first** (`WHERE department_id IN (...)` then `ORDER BY`) | **4.9 ms** | 10 |
| rank-first (`ORDER BY` then filter in Python) | 66.5 ms | 50 |

Two conclusions, both verified rather than asserted:

1. **Exact search is fast enough at this scale.** 4.9 ms for a filtered nearest-neighbour query over 6 000 rows. The corpus is ~5 500 embeddable rows, so exact search is viable with no ANN index, no extension, and no recall gap.
2. **The secure shape is also the 13× faster shape.** Filter-first does less work — it aggregates ~580 rows instead of 6 000. **There is no performance argument for rank-then-filter, only a correctness argument against it.** That is worth stating to anyone who later proposes the wrong shape for speed.

And the count-oracle, demonstrated rather than described:

```
rank-first over the full corpus, LIMIT 50, then count how many belong to another scope
  -> 2 of the global top-50 nearest are out-of-scope
filter-first returns none of them, and the residual count is never observable
```

**ANN revisited at ~500 k rows**, with one non-negotiable constraint: **a single global HNSW/IVFFlat index over mixed-tenant rows is forbidden**, because it makes rank-then-filter the only efficient plan — the leak becomes the default. If ANN is ever adopted, it must be per-partition or use iterative scans with the scope predicate pushed into the scan.

### 4.2 Write path — stamping is the control

```python
# app/ai/vector/ingest.py
async def ingest(source_table: str, db: AsyncSession, embedder: Embedder):
    """Embed rows into the vector dataset. NEVER callable on a scoped read path."""
    cap = capability(source_model(source_table))
    if cap is TableCapability.NEVER_READ:
        raise NeverReadableTable(source_table)      # users, action_audit
    if cap is not TableCapability.SCOPABLE:
        raise UnscopeableTable(source_table)        # compliance_*, tenant dimensions

    # Rows with no tenancy stamp are not embedded. They are not estate-wide;
    # they are unattributed, and embedding them would create a corpus that no
    # caller can be authorised to see and no reviewer can audit.
    rows = (await db.execute(
        select(Finding).where(Finding.department_id.isnot(None))
    )).scalars().all()

    for row in rows:
        text = redact(embeddable_text(row))          # raw_data NEVER included
        vec  = await embedder.embed(text)            # self-hosted only
        db.add(Embedding(
            source_table="findings", source_id=row.id,
            department_id=row.department_id, branch_id=row.branch_id,
            ministry_id=row.ministry_id, cluster_id=row.cluster_id,
            scope_hash=scope_hash_for(row),          # derived from the STAMP, not the caller
            disclosure_class="tenant_scoped",
            chunk_text=text, embedding=vec,
            embedding_model=embedder.model_id, embedding_dim=embedder.dim,
        ))
```

Three rules enforced here:

1. **Never-read tables are refused.** `identity.users` (email, `password_hash`, roles, full tenancy assignment) and `audit.action_audit` (actor + every prior user's scope) have **no embedding path whatsoever**.
2. **Unattributed rows are excluded**, not treated as estate-wide. 207 rows.
3. **`raw_data` never enters the text.** `redact()` runs before the embedder, and the embedder never receives the row object — only the redacted string. This is structural: there is no code path by which the raw payload could be embedded.

### 4.3 Read path — filter, then rank

```python
# app/ai/vector/search.py
async def search(scope: ReportScope, query: str, k: int, db: AsyncSession):
    """Semantic retrieval. scope is FIRST POSITIONAL — the S6 rule applies here too."""
    q = await embedder.embed(redact(query))

    stmt = select(Embedding.chunk_text, Embedding.source_table, Embedding.source_id,
                  ai.embedding_l2_distance(Embedding.embedding, pack(q)).label("dist"))
    # THE CONTROL. Scope filter is in the SQL, not in Python, and not optional.
    stmt = stmt.where(scope.tenant_filter(Embedding))     # delegates to auth.tenant_filter
    stmt = stmt.order_by("dist").limit(k)

    rows = (await db.execute(stmt)).all()
    return apply_k_anonymity_floor(rows, k)
```

- `scope.tenant_filter(model)` is the **existing** `app/api/auth.py:210` primitive. The vector dataset introduces no new scoping logic.
- `DisclosureClass` is attached per row, so an `ESTATE_WIDE` vector — if compliance tables are ever admitted — is labelled, not silently mixed.
- The **k-anonymity floor applies after retrieval**, suppressing any result whose cohort is below 5. With 112 of 172 departments under that threshold, this suppresses most per-department corpora, which is why §4.4 changes the granularity.

### 4.4 Granularity — estate-wide, not per-department

Given §3.3 and §3.4, the corpus is built **one estate-wide embedding set, retrieved under a mandatory scope filter** — the opposite of per-department partitioning.

| Option | Verdict |
|---|---|
| Per-department partitions | **Rejected.** 112 of 172 departments fall below the k=5 floor; two thirds of the corpus is unservable |
| Per-branch partitions | **Rejected.** 8 550 rows have no `branch_id`; branch admins would see near-empty corpora |
| **Estate-wide store, mandatory scope filter, k=5 floor after retrieval** | **Recommended.** One corpus, one control, no partition to get wrong |

The safety of this rests entirely on the filter being in the SQL and on the `scope` parameter being mandatory. That is why **S6 is extended to `app/ai/vector/`** — the signature test that every function reading `Embedding` takes `scope: ReportScope` first.

### 4.5 Model — self-hosted, pinned, no egress

| Requirement | Position |
|---|---|
| Embedding model | `bge-m3` (multilingual, 1024-dim) — the estate contains non-English asset names |
| Hosting | **Ollama, self-hosted, `localhost:11434`.** Same runtime as the generation path |
| Egress | **None.** A cloud embedding API would send warehouse text outside the environment, which the G1 §11 non-goals forbid absolutely |
| Pinning | `embedding_model` + `embedding_dim` on every row. **A mixed-dimension corpus is silently corrupt** — cosine across mismatched dims returns nonsense rather than erroring |
| Drift | Changing the model requires a full re-ingest. Enforced by a test asserting one distinct `(model, dim)` across the table |

### 4.6 Disclosure classification

| Class | Applies to | Behaviour |
|---|---|---|
| `TENANT_SCOPED` | findings, risk_scores, alerts, api_endpoints with a valid stamp | Filtered by `scope_hash` |
| `ESTATE_WIDE` | none admitted in v1 | Compliance tables are refused at ingest (unscopable) |
| `NEVER_READ` | `users`, `action_audit` | No embedding path exists |

---

## 5. What this design does **not** deliver

Stated plainly, because the temptation will be to demo it as a capability:

1. **It does not improve report quality on the current corpus.** Mean description length is 37 characters. Exact `ILIKE` beats it. The value is *future* corpus: narrative runbooks, remediation history, policy documents, incident write-ups — prose that actually needs semantic retrieval.
2. **It does not serve 112 of 172 departments.** The k=5 floor suppresses them. Serving them means either accepting the disclosure risk or aggregating at province level.
3. **It does not add a security property the platform lacks.** Row-level scoping already exists. This adds a *second* access path to the same data, which is a new surface, not a new guarantee.
4. **It does not touch `soc_shift_handover` or any report type.** Retrieval augments a fact pack; it does not generate one.

---

## 6. Verification

| Suite | Method | Pass criterion |
|---|---|---|
| **V1 Stamp integrity** | Every `Embedding` row has non-null `department_id` and a `scope_hash` | 100%. Zero unattributed embeddings |
| **V2 Filter-before-rank** | Static check on `app/ai/vector/search.py`; assert the scope predicate is in the statement before `order_by` | No rank-then-filter path exists in the module |
| **V3 S6 extension** | Signature inspection over `app/ai/vector/` | 100% scope-first-positional, same as `accessors.py` |
| **V4 Cross-tenant retrieval** | DHA `soc` queries for Home Affairs content; every returned row inspected | Zero rows outside the province-expanded set |
| **V5 Count oracle** | Scoped user runs the same query with 50 near-duplicate phrasings; record result-set sizes | Sizes do not vary with out-of-scope corpus density |
| **V6 Never-read refusal** | Attempt to ingest `users`, `action_audit` | Raises `NeverReadableTable` |
| **V7 Unscopable refusal** | Attempt to ingest `compliance_snapshots` | Raises `UnscopeableTable` |
| **V8 k-anonymity** | Query scoped to `ec-health` (1 finding) | Suppressed, not returned |
| **V9 Model homogeneity** | `SELECT count(DISTINCT (embedding_model, embedding_dim))` | Exactly 1 |
| **V10 Fact-pack integration** | Retrieval results fed into `context.py` | Every retrieved chunk carries a `DisclosureClass`; none is `NEVER_READ` |
| **V11 No raw_data** | Assert `raw_data` absent from every `chunk_text`; assert no embedding source path receives the row object | 100% |
| **V12 Non-interference** | `git diff main` | Only `app/ai/vector/`, `init-ai-vector.sql`, tests, one `main.py` line |

**V5 is the suite that will be skipped and the one that matters most.** A count oracle is invisible in functional testing — every response is individually correct. It is found only by varying the query against a known out-of-scope corpus.

---

## 7. Recommended scope for the 9-day window

**Recommendation: build this in Phase 13.2, not in the 6-16 October POC.**

Reasons, in order of weight:

1. **The corpus does not yet justify it** (§3.4). Embedding 37-character strings adds an inference call and a new table for no measurable retrieval gain.
2. **The POC is already over capacity** — 17.25 PD of developer effort against 14.0 PD, a **+3.25 PD shortfall**. Adding a vector pipeline makes that worse and would push the Gate C cut trigger.
3. **pgvector is unavailable**, so the design carries an unresolved infrastructure dependency.
4. **A second access path to warehouse data, added in the same window as the first, is how a tenancy defect gets introduced.** Ship the fact-pack path, prove it, then add retrieval.

What should happen on 15 October if a vector capability is expected: **say it is Phase 13.2.** A client who is told "Phase 13.2, design complete, evidence on paper" is in a materially better position than one shown a demonstration whose quality claim is contradicted by its own corpus statistics.

---

## 8. Effort

| # | Item | PD | Owner |
|---|---|---:|---|
| V1 | `init-ai-vector.sql` — `ai.embedding`, stamp columns, indexes, `embedding_l2_distance()` | 1.0 | Lead Developer |
| V2 | `redact()` — extend the pre-egress gate to embedding text; prove `raw_data` cannot pass | 1.5 | Head of AI Research |
| V3 | `ingest.py` — stamp write, refuse never-read and unscopable, re-ingest on model change | 2.0 | Lead Developer |
| V4 | `search.py` — filter-then-rank, `disclosure_class` tagging, k=5 floor | 1.5 | Lead Developer |
| V5 | S6 extension to `app/ai/vector/` | 0.5 | Lead Developer |
| V6 | Model homogeneity + migration guard | 0.5 | Head of AI Research |
| V7 | V1-V12 verification suites | 3.0 | Both |
| V8 | Corpus quality baseline — measure whether retrieval beats `ILIKE` | 1.0 | Head of AI Research |
| | **Total** | **11.0** | |

**V8 is not optional.** If semantic retrieval does not measurably beat lexical search on this corpus, the correct decision is not to build the pipeline — it is to keep `ILIKE` and spend the 11 PD on the five remaining report types instead.

---

*Vector dataset design for Addendum B Phase 13.2. All corpus, tenancy-integrity and extension claims executed live against PostgreSQL 18.1 `sita` on 6 October 2026. Nothing in this design has been implemented.*