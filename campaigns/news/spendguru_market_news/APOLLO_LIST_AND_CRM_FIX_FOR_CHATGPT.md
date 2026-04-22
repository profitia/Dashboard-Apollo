# Apollo List & CRM Fix — Summary for ChatGPT Context

**Date:** 2026-04-21  
**Campaign:** spendguru_market_news  
**Pipeline:** `src/news/apollo/sequence_builder.py`

---

## What Was Broken (Before Fixes)

1. **`_add_to_apollo_list` crashed** with `AttributeError: 'list' object has no attribute 'get'`  
   → Apollo `GET /v1/labels` returns a Python `list` directly, not `{"labels": [...]}`.

2. **CRM stage set + custom field sync returned 422**  
   → Code was passing `apollo_person_id` (from prospecting search `mixed_people/api_search`) to CRM endpoints. Apollo uses two completely separate ID systems:
   - `apollo_person_id` — prospecting/search DB, used ONLY for email reveal (`POST /people/match`)
   - `apollo_crm_contact_id` — CRM, used for stage set, list add, custom fields

3. **`POST /v1/labels/{id}/add_contact_ids` returned 404**  
   → `APOLLO_BASE_URL = "https://api.apollo.io/v1"`. This endpoint only works at `/api/v1/`, not `/v1/`. Other methods (e.g. `update_contact`) explicitly use `/api/v1/` and work fine.

---

## What Was Fixed

### Bug A — Labels list/dict type handling
```python
# Before (crashes):
labels_raw = client._get("labels") or {}
all_labels = labels_raw.get("labels", [])

# After (handles both list and dict):
labels_raw = client._get("labels") or []
if isinstance(labels_raw, list):
    all_labels = labels_raw
elif isinstance(labels_raw, dict):
    all_labels = labels_raw.get("labels", [])
```

### Bug B — Separate people_id vs crm_contact_id dictionaries
```python
# Two dictionaries maintained in create_news_sequence:
people_ids_by_item: dict[int, str] = {}    # reveal only (from search)
crm_ids_by_item: dict[int, str] = {}       # CRM ops (from POST /contacts)

# _find_or_create_apollo_contact:
# 1. Requires email
# 2. search_contact(email) → find existing CRM contact
# 3. POST /contacts → create if not found
# 4. Returns CRM contact ID
```

### Sub-bug — `add_contact_ids` 404 → fallback to `label_ids` PATCH
```python
# Primary (still returns 404 due to Apollo plan limit):
requests.post("https://api.apollo.io/api/v1/labels/{label_id}/add_contact_ids", ...)

# Fallback (works):
client.update_contact(contact_id, label_ids=[label_id])
# = PATCH /api/v1/contacts/{contact_id} with {"label_ids": [label_id]}
```

---

## Current State After All Fixes

| Metric | Before | After |
|---|---|---|
| `contacts_added_to_list` | 0 (crash → 404) | **2** ✅ |
| `contacts_stage_set` | 0 (422) | **2** ✅ |
| `contacts_synced` (custom fields) | 0 (422) | **2** ✅ |
| `reveal_count` | 2 | 2 (unchanged) |
| `Final status` | READY_FOR_REVIEW | **READY_FOR_REVIEW** ✅ |

Smoke tests: 29/29 ✅

---

## Flow After Fixes (No Email → Reveal Path)

```
1. Contact found in Apollo search (no email) → store people_id
2. Phase 1 skipped (no email)
3. Reveal: people.match(people_id) → email obtained
4. CRM import: search_contact(email) or POST /contacts → crm_id
5. List add: update_contact(crm_id, label_ids=[label_id])  ← fallback
6. Stage set: update_contact(crm_id, contact_stage_id=stage_id)
7. Custom fields: update_contact_custom_fields(crm_id, field_values)
8. Notification email sent → READY_FOR_REVIEW
```

---

## Files Changed

- `src/news/apollo/sequence_builder.py` — `_add_to_apollo_list`, `_find_or_create_apollo_contact`, `create_news_sequence` (Phase 1, 2, 3)
- `tests/integration_test_live_reveal.py` — `verify_apollo_lists`

---

## Known Remaining Issues

- Primary `POST /api/v1/labels/{id}/add_contact_ids` still returns 404 (Apollo routing/plan). Fallback works.
- Some contacts (e.g. Marta in Grycan test) return no email on reveal — expected, not a bug.
- Evra Fish alias LLM bug (adds "Sp. z o.o." → NO_MATCH) — separate issue, not in scope.
