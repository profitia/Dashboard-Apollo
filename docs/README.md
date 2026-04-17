# Apollo Outreach Analytics — Dashboard

Static dashboard for Apollo campaign and sequence performance metrics.  
Hosted via GitHub Pages from the `docs/` folder.

## Refreshing data

Run the following commands locally (requires `.env` with `DATABASE_URL`):

```bash
# 1. Sync latest sequences from Apollo API
python src/apollo_sync/sync_sequences.py

# 2. Sync latest messages from Apollo API
python src/apollo_sync/sync_messages.py

# 3. Export analytics views to static JSON
python src/apollo_sync/export_dashboard_data.py
```

This writes `docs/data/apollo_dashboard.json` — a snapshot of the analytics views.  
**This file must never contain secrets, credentials, or PII.**

## Local preview

```bash
python -m http.server 8000 -d docs
```

Then open [http://localhost:8000](http://localhost:8000).

## Publishing via GitHub Pages

1. Push `docs/` to the `main` branch.
2. Go to **GitHub repo → Settings → Pages**.
3. Set **Source**: Deploy from a branch.
4. Set **Branch**: `main`, **Folder**: `/docs`.
5. Save. The dashboard will be available at `https://<org>.github.io/<repo>/`.

## Data file

`docs/data/apollo_dashboard.json` contains a point-in-time snapshot of:

- `sequence_performance` — per-sequence metrics (messages, opens, clicks, replies, rates)
- `message_status_summary` — message status distribution
- `reply_type_summary` — reply type distribution
- `sequence_status_summary` — messages grouped by sequence status

The file is generated locally and committed to the repo. It does not contain database credentials or API keys.
