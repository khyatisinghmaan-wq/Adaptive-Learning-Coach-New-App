# Adaptive Learning Coach (ALC) – Prototype V1

A minimal **Flask** app demonstrating the core flow required for your **Milestone #3**:
- Chat (mock RAG) with sources
- 3‑item pulse survey
- Micro‑lessons + completion tracker
- Aggregated metrics with **n ≥ 5** rule and 90‑day retention
- Alias‑based demo login (no PII)

## Quick Start (Replit)
1. Create a new Replit using the **Flask (Python)** template.
2. Upload all files/folders from this repo into the Replit project.
3. Replit auto‑installs `requirements.txt` and runs `main.py`.
4. Use the Live URL as your **MVP link**.

## Quick Start (Local)
```bash
pip install -r requirements.txt
python main.py
# Visit http://127.0.0.1:5000
```

## Routes
- `/` → Home
- `/login` → Alias-based login
- `/chat` → Mock RAG Q&A (returns a source paragraph from the KB)
- `/survey` → 3-item Likert survey (stores to SQLite)
- `/lessons` → Micro-lessons and completion toggles
- `/metrics` → Aggregated charts + privacy guard (**n ≥ 5**)

## Data & Privacy
- SQLite DB: `data/alc.db`
- Aggregation: team-level only, **no individual leaderboards**
- Retention: raw events older than 90 days are purged on startup
- Secrets: none required for this mock (no external APIs used)

## Notes
- The mock RAG uses tiny markdown knowledge base files in `data/kb`.
- Update the KB content or plug in a real API later.
- Screenshots for your report can be taken from `/chat`, `/survey`, `/lessons`, `/metrics` after running.
