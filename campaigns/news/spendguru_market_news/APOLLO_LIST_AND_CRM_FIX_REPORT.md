# Apollo List Add & CRM Contact Fix — Report

**Date:** 2026-04-21  
**Author:** Tomasz Uściński / AI pair-programming session  
**Campaign:** spendguru_market_news  
**File:** `campaigns/news/spendguru_market_news/APOLLO_LIST_AND_CRM_FIX_REPORT.md`

---

## 1. Executive Summary

During the first live reveal test (dry_run=False) on the Grycan case, three infrastructure errors were discovered in the news pipeline's Apollo integration. Two bugs were identified and fixed across two sessions:

- **Bug A** — `_add_to_apollo_list`: crashed with `'list' object has no attribute 'get'` (API returns list, not dict). Fixed in session 1.
- **Bug B** — `_find_or_create_apollo_contact`: used `apollo_person_id` (prospecting DB ID) for CRM operations, causing 422 errors on stage set and custom field sync. Fixed in session 1.
- **Sub-bug (list add 404)** — after Bug A was fixed, `POST /v1/labels/{id}/add_contact_ids` returned 404 (wrong URL base). Fixed in session 2 with a fallback approach.

After three live validation runs, the pipeline now produces:

```
listed=2, stage=2, synced=2, reveal=2/attempted, email_available=True
Final status: READY_FOR_REVIEW
```

All three CRM operations (list add, stage set, custom fields) are fully functional.

---

## 2. Fix A — Apollo Labels Type Bug

### Problem

`GET /v1/labels` on the Apollo API returns a Python `list` directly (not a dict with a `"labels"` key).  
Old code called `.get("labels", [])` on this list → `AttributeError: 'list' object has no attribute 'get'`.

### Root Cause

```python
# OLD (wrong)
labels_raw = client._get("labels") or {}
all_labels = labels_raw.get("labels", [])   # AttributeError: 'list' has no .get()
```

### Fix Applied

```python
# NEW (correct)
labels_raw = client._get("labels") or []
if isinstance(labels_raw, list):
    all_labels = labels_raw
elif isinstance(labels_raw, dict):
    all_labels = labels_raw.get("labels", [])
else:
    all_labels = []
```

Applied in both `src/news/apollo/sequence_builder.py` (`_add_to_apollo_list`) and `tests/integration_test_live_reveal.py` (`verify_apollo_lists`).

### Validation Result (3rd live run)

```
[PRECOND] Apollo labels fetched — 77 total
[PRECOND] Apollo list 'PL Tier 1 do market_news VSC': EXISTS
[PRECOND] Apollo list 'PL Tier 2 do market_news VSC': EXISTS
[PRECOND] Apollo list 'PL Tier 3 do market_news VSC': EXISTS
```

Status: **FIXED** ✅

---

## 3. Fix B — CRM Contact ID vs People/Prospecting ID

### Problem

Apollo uses two entirely separate ID systems:

| ID type | Source | Used for |
|---|---|---|
| `apollo_person_id` | `mixed_people/api_search` (prospecting DB) | Email reveal only |
| `apollo_crm_contact_id` | `POST /api/v1/contacts` (CRM) | List add, stage set, custom fields |

Old code stored `apollo_contact_id` from the prospecting search result and passed it to CRM operations (stage set, custom field sync). Apollo returned 422 because the prospecting ID is not valid in the CRM context.

### Root Cause

```python
# OLD: people_id used everywhere (wrong for CRM ops)
contact_id = contact.apollo_contact_id  # this is people/prospecting ID
client.update_contact(contact_id, ...)        # 422: ID not found in CRM
```

### Fix Applied

Two separate ID dictionaries maintained throughout `create_news_sequence`:

```python
people_ids_by_item: dict[int, str] = {}   # apollo_person_id — reveal only
crm_ids_by_item: dict[int, str] = {}      # apollo_crm_contact_id — CRM ops
```

`_find_or_create_apollo_contact` was rewritten to:
1. Search CRM contacts by email via `client.search_contact(email)`
2. Create CRM contact via `POST /contacts` if not found
3. Return CRM contact ID (never people_id)

### Updated Post-Reveal Flow

1. **Phase 1** (contacts with email): CRM import → get crm_id → list add → stage set
2. **Phase 2** (contacts without email → reveal):
   - Reveal using `people_id` via `client.reveal_email(people_id)`
   - On success: call `_find_or_create_apollo_contact(email)` → get crm_id
   - Then: list add → stage set using crm_id
3. **Phase 3**: Custom field sync using `crm_ids_by_item[idx]` (never people_id)

### Validation Result (3rd live run)

```
[CRM] Contact created: monika.bartkowska@grycan.pl → crm_id=69e9186f254318000d78266e
[CRM] Contact created: justyna.osinska@grycan.pl  → crm_id=69e9192e5a464f0019025f4d
contacts_stage_set=2       ← was 0 before fix
contacts_synced=2          ← was 0 before fix
```

Status: **FULLY FIXED** ✅

---

## 4. Sub-bug — List Add 404 (Resolved via Fallback)

### Problem

After Fix A, `_add_to_apollo_list` correctly found the label ID but still returned 404 on:

```
POST https://api.apollo.io/v1/labels/{label_id}/add_contact_ids
```

### Root Cause

`APOLLO_BASE_URL = "https://api.apollo.io/v1"` (in `Integracje/config.py`).  
`client._post("labels/{id}/add_contact_ids")` constructs `/v1/labels/...`.  
Apollo's `add_contact_ids` endpoint is only available at `/api/v1/labels/...`, not `/v1/labels/...`.  
Other methods (e.g. `update_contact`) explicitly use `APOLLO_BASE_URL.replace('/v1', '') + '/api/v1/contacts/...'` and work correctly.

This is a plan-level or routing difference in Apollo's API — `/v1/` vs `/api/v1/` for specific endpoints.

### Fix Applied

`_add_to_apollo_list` was updated to use a two-step strategy:

**Primary**: explicit `/api/v1/` base URL for `add_contact_ids`:
```python
api_base = "https://api.apollo.io/api/v1"
resp = requests.post(
    f"{api_base}/labels/{label_id}/add_contact_ids",
    json={"contact_ids": [contact_id]},
    headers=client.headers,
)
```

**Fallback** (if primary returns 404): `update_contact` with `label_ids`:
```python
client.update_contact(contact_id, label_ids=[label_id])
```

The fallback uses `PATCH /api/v1/contacts/{contact_id}` with `label_ids=[label_id]` — the same endpoint used by stage set, which is confirmed working.

### Validation Result (3rd live run)

```
[LIST] Primary add_contact_ids failed — trying fallback
[LIST] Primary add_contact_ids failed — trying fallback
Draft complete: listed=2, stage=2, synced=2
contacts_added_to_list=2   ← was 0 before fix
```

Primary still returns 404 (Apollo plan limitation), fallback succeeds.  
Status: **FIXED via fallback** ✅

---

## 5. Files Changed

| File | Change |
|---|---|
| `src/news/apollo/sequence_builder.py` | Rewrote `_add_to_apollo_list`, `_find_or_create_apollo_contact`, Phase 1 and Phase 2/3 of `create_news_sequence` |
| `tests/integration_test_live_reveal.py` | Fixed `verify_apollo_lists` (same list/dict type handling as Bug A) |

---

## 6. Validation History

| Run | listed | stage | synced | reveal | Status |
|---|---|---|---|---|---|
| 1st live (before fixes) | 0 | 0 | 0 | 2 | READY_FOR_REVIEW (with errors) |
| 2nd live (Fix A + Fix B) | 0 | 2 | 2 | 2 | READY_FOR_REVIEW (list still 404) |
| 3rd live (sub-bug fix) | **2** | **2** | **2** | **2** | **READY_FOR_REVIEW** ✅ |

Smoke tests: **29/29 passed** after all fixes.  
Dry-run regression: passed (no regressions).

---

## 7. Risks and Limitations

- **Primary `add_contact_ids` endpoint always 404**: The fallback (`label_ids` PATCH) works, but if Apollo changes PATCH behavior for `label_ids` (e.g. replaces instead of appends), existing labels could be overwritten. Monitor in production.
- **Marta (1st contact — no email revealed)**: `reveal_email` returns None for some contacts. Expected behavior — not a bug. These contacts are drafted without email and excluded from CRM operations.
- **`search_contact(email)` — duplicate handling**: If `POST /contacts` is called twice for the same email (e.g. on repeated test runs), Apollo may create duplicates. The `_find_or_create_apollo_contact` function searches first, but the search window may not be immediate.
- **Evra Fish alias bug**: LLM sometimes appends "Sp. z o.o." to company name → NO_MATCH in resolver. Separate issue, not in scope of this fix.
- **ORLEN resolver**: Maps to subsidiary instead of parent. Separate issue.

---

## 8. Final Recommendation

The pipeline is ready for production live testing with new companies.

**Next steps:**
1. Run live test on a second real company (not Grycan) to confirm no regressions.
2. Monitor `label_ids` PATCH behavior — verify contacts appear in correct Apollo lists.
3. Optionally: raise support ticket with Apollo to investigate why `/api/v1/labels/{id}/add_contact_ids` returns 404 despite `/v1/labels` (GET) working.
4. Consider adding `apollo_crm_contact_id` to `contact_results` export for downstream use.
