# Blueprint v2.2 — OpenRouter Routing for script_writer + reel_extractor

**Model:** Sonnet (planning phase — scope too small to warrant Opus)
**Date:** 2026-05-29
**Feature:** Wire script_writer and reel_extractor through OpenRouter cascade; keep narrative_warehouse on Ollama.

---

## State

**Affected files:**
- `NOTION DIARY FETCHER/config.toml`
- `frameworks/instagram_frameworks/llm_client.py`
- `NOTION DIARY FETCHER/api/reel_routes.py`

**Unchanged (explicitly out of scope):**
- `narrative_warehouse/llm_client.py` — stays Ollama-only (privacy)
- `narrative_warehouse/stage1_extractor.py` — no change
- `openrouter/router.py` — no change
- `config/openrouter_models.yaml` — already has `generate_reel_script` + `extract_reel_framework` tasks ✅

**Current gap:**
- `llm_client.complete()` is hardcoded Ollama. Both `script_writer.py` CLI and `extract_reel.py` call it.
- `/generate` (non-streaming) only uses OpenRouter if `body.model` is explicitly passed — silent Ollama fallback otherwise.
- `/generate/stream` already uses OpenRouter unconditionally ✅

---

## Logic

### 1. `config.toml` — add `provider` field to two sections

```
[script_writer]
provider = "openrouter"        # ADD — routes complete() through cascade
ollama_model = "gemma-32k:latest"   # kept as tier-3 fallback in router
ollama_endpoint = "http://localhost:11434"

[reel_extractor]
provider = "openrouter"        # ADD — routes complete() through cascade
ollama_model = "gemma-32k:latest"
ollama_endpoint = "http://localhost:11434"

[narrative_warehouse]
provider = "ollama"            # ADD — explicit, local-only (privacy)
llm_provider = "ollama"        # existing key — keep
llm_model = "gemma-32k:latest" # existing key — keep
```

---

### 2. `frameworks/instagram_frameworks/llm_client.py`

**Module responsibility:** Thin LLM dispatch layer for instagram_frameworks. Reads `provider` from config, routes to OpenRouter cascade or Ollama.

```
complete(prompt, section, dry_run) -> str
  Key rules:
    - Read provider = cfg.get("provider", "ollama")
    - if provider == "openrouter": call openrouter.router.chat(task, messages, max_tokens=2048)
    - else: call _ollama_complete() as before
    - task_map: {"script_writer": "generate_reel_script", "reel_extractor": "extract_reel_framework"}
    - dry_run path unchanged (print + sys.exit)
    - import openrouter.router inside the branch (lazy — avoids import error without API key)
  Calls: openrouter.router.chat OR _ollama_complete (unchanged)
```

**Import path note:** `openrouter/` is at repo root. The caller must ensure `sys.path` includes repo root. `reel_routes.py` already does `sys.path.insert(0, str(_REPO_ROOT))` before importing `llm_client` — so the import will resolve.

---

### 3. `NOTION DIARY FETCHER/api/reel_routes.py` — `/generate` route only

**Module responsibility:** Fix the non-streaming `/generate` endpoint to default to OpenRouter (matching `/generate/stream` behaviour).

```
POST /reels/generate — generate(body: GenerateRequestBody) -> dict
  Key rules:
    - Load cfg = llm_client.load_config("script_writer")
    - cfg_provider = cfg.get("provider", "ollama")
    - Override logic: if body.provider == "ollama", force Ollama regardless of config
    - Default: use llm_chat("generate_reel_script", messages, max_tokens=2048, override_model=body.model or None)
    - Ollama path: script_writer.generate_script(prompt, cfg) — unchanged
    - Remove old conditional: `if body.model and body.provider != "ollama"`
  Calls: openrouter.router.chat (default) OR script_writer.generate_script (explicit ollama override)
```

**Diff summary:**
```python
# REMOVE:
if body.model and body.provider != "ollama":
    ...
else:
    text, model_used = script_writer.generate_script(prompt, cfg)

# REPLACE WITH:
cfg_provider = cfg.get("provider", "ollama")
if body.provider == "ollama" or cfg_provider == "ollama":
    text, model_used = script_writer.generate_script(prompt, cfg)
else:
    from openrouter.router import chat as llm_chat
    result = llm_chat(
        "generate_reel_script", messages,
        max_tokens=2048,
        override_model=body.model or None,
    )
    text = result["content"]
    model_used = result["model"]
```

---

## Specs

- Python 3.12, uv
- No new dependencies — `openrouter` package already installed
- No DB schema changes
- No frontend changes
- Do NOT touch `narrative_warehouse/` in any file

---

## Definition of Done

- [ ] `config.toml` has `provider = "openrouter"` under `[script_writer]` and `[reel_extractor]`
- [ ] `config.toml` has `provider = "ollama"` under `[narrative_warehouse]`
- [ ] `llm_client.complete()` branches on `provider`: openrouter → `router.chat()`, ollama → `_ollama_complete()`
- [ ] `/reels/generate` (non-streaming) uses OpenRouter by default; passes `body.provider == "ollama"` as explicit override
- [ ] `/reels/generate/stream` unchanged (already correct)
- [ ] `narrative_warehouse/llm_client.py` untouched

---

## ⚠️ User Verification Report

Before handing off to Gemma4, confirm:

1. `OPENROUTER_API_KEY` is set in `NOTION DIARY FETCHER/.env` — the cascade will hit the API key on first call
2. The free model IDs in `openrouter_models.yaml` (`openai/gpt-oss-120b:free`, `google/gemma-4-31b-it:free`, etc.) are still valid on OpenRouter
3. Ollama is running locally (`ollama serve`) as tier-3 fallback — if both OpenRouter models fail, the router will fall back to `gemma-32k:latest`

Report what's missing or failed before proceeding.
