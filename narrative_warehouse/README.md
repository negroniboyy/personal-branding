# Narrative Warehouse

Processes Notion diary entries into structured story ideas — a channel-agnostic story idea database ready to be adapted into LinkedIn posts, Instagram content, video scripts, and more.

 Terminal 1 — Backend:                                                                                                                                       
  cd "/Users/maxkiyuna/Documents/personal_brand/NOTION DIARY FETCHER"                                                                                         
  uv run uvicorn api.main:app --host 127.0.0.1 --port 8000                                                                                                    
                                                                                                                                                              
  Terminal 2 — Frontend:                                                                                                                                      
  cd "/Users/maxkiyuna/Documents/personal_brand/frontend"                                                                                                     
  npm run dev                                                                                                                                                                                                                                                                                    
  Then open http://localhost:5173 — you'll see the Diary and Narrative Warehouse tabs.

---

## Quick Start

### 1. Ensure Ollama is running (for local LLM)

```bash
ollama list
# if empty or gemma4:e2b not listed:
ollama pull gemma4:e2b
ollama serve  # keep running in background
```

### 2. Run extraction (Stage 1)

```bash
cd "/Users/maxkiyuna/Documents/personal_brand/NOTION DIARY FETCHER"
PYTHONPATH=/Users/maxkiyuna/Documents/personal_brand python3 -m narrative_warehouse.stage1_extractor --provider ollama --model gemma4:e2b
```

This reads all pages with `processed_status = 0`, calls the LLM to extract story variables, and writes to the `story_nodes` table. Subsequent runs only process new entries.

### 3. Run synthesis (Stage 2)

```bash
PYTHONPATH=/Users/maxkiyuna/Documents/personal_brand python3 -m narrative_warehouse.stage2_synthesizer
# or for a specific week:
python3 -m narrative_warehouse.stage2_synthesizer --week-start 2026-01-20
```

This clusters recent story nodes into threads, computes sentiment delta, and writes to `weekly_index` and `threads` tables.

---

## Architecture

```
NOTION DIARY FETCHER/          ← existing diary sync (pages → blocks)
narrative_warehouse/            ← this subsystem
  ├── db.py                     ← schema migration
  ├── config.py                 ← config.toml reader
  ├── llm_client.py             ← Minimax + Ollama LLM abstraction
  ├── normalizer.py             ← conflict node normalization
  ├── stage1_extractor.py       ← daily extraction (CLI + API)
  ├── stage2_synthesizer.py     ← weekly synthesis (CLI + API)
  └── api_routes.py             ← FastAPI routes (/narrative/*)
```

---

## Configuration

Edit `NOTION DIARY FETCHER/config.toml`:

```toml
[narrative_warehouse]
llm_provider = "ollama"
llm_model = "gemma4:e2b"

[minimax]
api_key = ""
base_url = "https://api.minimax.io"
model_name = "MiniMax-Text-01"

[ollama]
base_url = "http://localhost:11434"
default_model = "gemma4:e2b"
```

**Provider priority:** CLI flags > `NARRATIVE_LLM_PROVIDER` / `NARRATIVE_LLM_MODEL` env vars > config.toml

**Minimax (cloud, free tier):** Set env var `MINIMAX_API_KEY`, then:
```bash
python3 -m narrative_warehouse.stage1_extractor --provider minimax --model MiniMax-Text-01
```

---

## Database Schema

### `pages` (altered)
```sql
ALTER TABLE pages ADD COLUMN processed_status INTEGER DEFAULT 0;
-- 0 = unprocessed, 1 = extraction complete
```

### `story_nodes` — one per diary page after LLM extraction

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | e.g. `sn_a1b2c3d4e5f6` |
| `page_id` | TEXT FK | reference to pages.id |
| `created_time` | TEXT | page creation timestamp |
| `user_state` | TEXT | 2-10 word mindset/situation |
| `conflict_node` | TEXT | reusable phrase, e.g. `creative-block` |
| `desired_outcome` | TEXT | 2-10 word goal |
| `the_bridge` | TEXT | 2-10 word solution belief |
| `thematic_tags` | TEXT | JSON array, e.g. `["career", "growth"]` |
| `worth_score` | REAL | 0.0–1.0 narrative potential |
| `narrative_flag` | TEXT | `Normal` or `Low Narrative Potential` |
| `llm_model_used` | TEXT | e.g. `ollama:gemma4:e2b` |
| `processed_at` | TEXT | ISO8601 timestamp |

### `weekly_index` — one per week of synthesis

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | e.g. `weekly_2026-04-20` |
| `week_start` | TEXT | Monday date |
| `week_end` | TEXT | Sunday date |
| `total_entries` | INT | story nodes that week |
| `thread_count` | INT | distinct conflict nodes |
| `open_loops` | INT | unresolved conflicts |
| `closed_loops` | INT | resolved conflicts |
| `sentiment_delta` | REAL | early-vs-late week score shift |
| `thread_summary_json` | TEXT | JSON array of thread objects |
| `generated_at` | TEXT | ISO8601 timestamp |

### `threads` — recurring conflict themes

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | e.g. `thread_a1b2c3` |
| `conflict_node` | TEXT UNIQUE | normalized conflict phrase |
| `display_name` | TEXT | human-readable, e.g. `Creative Block` |
| `first_seen` | TEXT | first occurrence |
| `last_seen` | TEXT | most recent occurrence |
| `occurrence_count` | INT | total times seen |
| `current_status` | TEXT | `Emerging` / `Open` / `Closing` / `Closed` |
| `closed_week_start` | TEXT | when marked Closed |

---

## The 4 Variables — What Gets Extracted

Each diary page is analyzed to extract:

1. **User_State** — What mindset/situation are you in? (2-10 words)
2. **Conflict_Node** — The core tension or problem (2-10 words, reusable phrase for clustering)
3. **Desired_Outcome** — What you want to achieve (2-10 words)
4. **The_Bridge** — What you believe will get you there (2-10 words)

Plus 2-3 thematic tags and a worth_score (0.0–1.0).

**Worth_score guide:**
- `0.9–1.0`: Explicit struggle, clear goal, emotional tension
- `0.7–0.89`: Some tension, identifiable desire
- `0.4–0.69`: Vague/abstract, no clear conflict
- `0.1–0.39`: Pure factual log → flagged `Low Narrative Potential`

---

## Query Examples

### View all story nodes (sorted by worth_score)
```bash
PYTHONPATH=/Users/maxkiyuna/Documents/personal_brand python3 -c "
import sys; sys.path.insert(0, '..')
from narrative_warehouse.db import get_db
conn = get_db(ro=True)
rows = conn.execute('SELECT user_state, conflict_node, desired_outcome, the_bridge, worth_score, narrative_flag, thematic_tags, created_time FROM story_nodes ORDER BY worth_score DESC').fetchall()
for r in rows:
    print(f\"[{r['worth_score']:.2f}] {r['created_time'][:10]} | {r['user_state']}\")
    print(f\"  conflict={r['conflict_node']} | outcome={r['desired_outcome']} | bridge={r['the_bridge']}\")
    print(f\"  tags={r['thematic_tags']} | {r['narrative_flag']}\")
    print()
conn.close()
"
```

### View all threads by status
```bash
PYTHONPATH=/Users/maxkiyuna/Documents/personal_brand python3 -c "
import sys; sys.path.insert(0, '..')
from narrative_warehouse.db import get_db
conn = get_db(ro=True)
threads = conn.execute('SELECT display_name, conflict_node, occurrence_count, current_status, first_seen, last_seen FROM threads ORDER BY current_status, last_seen DESC').fetchall()
for t in threads:
    print(f\"[{t['current_status']:10}] {t['display_name']:40} x{t['occurrence_count']}  ({t['first_seen'][:10]} → {t['last_seen'][:10]})\")
conn.close()
"
```

### View weekly summaries with thread details
```bash
PYTHONPATH=/Users/maxkiyuna/Documents/personal_brand python3 -c "
import sys; sys.path.insert(0, '..')
from narrative_warehouse.db import get_db; import json
conn = get_db(ro=True)
weeks = conn.execute('SELECT * FROM weekly_index ORDER BY week_start DESC').fetchall()
for w in weeks:
    arrow = '↑' if w['sentiment_delta'] > 0.05 else '↓' if w['sentiment_delta'] < -0.05 else '→'
    print(f\"{w['week_start']} → {w['week_end']}  [{w['total_entries']} entries | {w['thread_count']} threads | {w['open_loops']} open / {w['closed_loops']} closed | sentiment {arrow}{abs(w['sentiment_delta']):.3f}]\")
    threads = json.loads(w['thread_summary_json'])
    for t in threads:
        print(f\"  • [{t['current_status']}] {t['display_name']} (x{t['occurrence_count']}, score={t['avg_worth_score']:.2f})\")
    print()
conn.close()
"
```

### Filter story nodes by minimum score
```bash
PYTHONPATH=/Users/maxkiyuna/Documents/personal_brand python3 -c "
import sys; sys.path.insert(0, '..')
from narrative_warehouse.db import get_db
conn = get_db(ro=True)
rows = conn.execute('SELECT * FROM story_nodes WHERE worth_score >= 0.9 ORDER BY created_time DESC').fetchall()
for r in rows:
    print(f\"[{r['worth_score']:.2f}] {r['created_time'][:10]} | {r['user_state']} | {r['conflict_node']}\")
conn.close()
"
```

---

## Via FastAPI

Start the server:
```bash
cd "/Users/maxkiyuna/Documents/personal_brand/NOTION DIARY FETCHER"
uv run uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Then:

```bash
# Extract (Stage 1)
curl -X POST http://localhost:8000/narrative/extract \
  -H "Content-Type: application/json" \
  -d '{"provider": "ollama", "model": "gemma4:e2b"}'

# Synthesize (Stage 2)
curl -X POST http://localhost:8000/narrative/synthesize \
  -H "Content-Type: application/json" \
  -d '{"week_start": "2026-04-20"}'

# List story nodes with filters
curl "http://localhost:8000/narrative/story-nodes?min_score=0.8&limit=20"
curl "http://localhost:8000/narrative/story-nodes?narrative_flag=Normal&limit=20"

# List threads by status
curl "http://localhost:8000/narrative/threads?status=Open"
curl "http://localhost:8000/narrative/threads?limit=50"

# List weekly summaries
curl "http://localhost:8000/narrative/weekly-index?limit=10"
```

---

## Thread Status Logic

A thread's status evolves as more entries are processed:

- **Emerging** — seen once in the week
- **Open** — seen 2+ times, sentiment not clearly improving
- **Closing** — 2+ occurrences, sentiment delta ≥ +0.15 (scores rising through the week)
- **Closed** — no re-occurrence for 1+ weeks after being Open

The sentiment delta compares early-week avg worth_score vs late-week. Positive = improving/conflict being resolved. Negative = worsening/conflict intensifying.

---

## Re-extracting

To re-process already-extracted pages (e.g. after updating the LLM prompt):

```bash
# Reset processed_status on all pages
PYTHONPATH=/Users/maxkiyuna/Documents/personal_brand python3 -c "
import sys; sys.path.insert(0, '..')
from narrative_warehouse.db import get_db
conn = get_db(ro=False)
conn.execute('UPDATE pages SET processed_status = 0')
conn.commit()
conn.close()
print('Reset all pages to unprocessed')
"

# Now run extraction again
python3 -m narrative_warehouse.stage1_extractor --provider ollama --model gemma4:e2b
```