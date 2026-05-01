# Blueprint v1.1 — Part 2/2: React Frontend
# Notion Diary UI — React + Vite

**Prereq:** Part 1 (FastAPI) must be running on port 8000.
**Execution target:** Qwen via Continue

---

## STATE

New files to create:
```
ui/                        # Vite React app root
ui/package.json
ui/vite.config.js
ui/index.html
ui/src/main.jsx
ui/src/App.jsx
ui/src/api.js
ui/src/components/PageList.jsx
ui/src/components/PageDetail.jsx
```

---

## SPECS

- Vite + React (no TypeScript — plain JSX)
- No UI library — plain HTML + inline styles or minimal CSS
- API base URL: http://localhost:8000
- Two views: list → detail (no router needed, use useState)

---

## DATA FLOW

```
App
  state: selectedPageId (null = show list)

  if selectedPageId == null:
    render PageList
      fetches GET /pages on mount
      renders list of titles + dates
      onClick(page.id) -> sets selectedPageId

  if selectedPageId != null:
    render PageDetail
      fetches GET /pages/{selectedPageId} on mount
      renders title, date, blocks in order
      Back button -> sets selectedPageId to null
```

---

## COMPONENT SIGNATURES

```
api.js
  BASE = "http://localhost:8000"
  fetchPages() -> Promise<PageSummary[]>
  fetchPage(id) -> Promise<PageDetail>

App.jsx
  state: selectedPageId = null
  renders: PageList | PageDetail based on selectedPageId

PageList.jsx
  props: onSelect(id: string) -> void
  state: pages = [], loading, error
  effect: fetchPages() on mount
  renders: clickable list of {title, created_time}

PageDetail.jsx
  props: pageId: string, onBack() -> void
  state: page = null, loading, error
  effect: fetchPage(pageId) on mount
  renders:
    - Back button
    - Page title + date
    - Blocks in order: skip blocks where plain_text == null
      show block_type as label + plain_text as content
```

---

## PACKAGE.JSON DEPS

```json
{
  "dependencies": { "react": "^18", "react-dom": "^18" },
  "devDependencies": { "vite": "^5", "@vitejs/plugin-react": "^4" }
}
```

---

## RUN COMMAND

```bash
cd ui
npm install
npm run dev
# opens at http://localhost:5173
```

---

## DEFINITION OF DONE

- [ ] `api/main.py` exists, `uvicorn main:app --reload` runs on port 8000
- [ ] `GET /pages` returns JSON array
- [ ] `GET /pages/{id}` returns page + blocks
- [ ] `ui/` Vite project scaffolded
- [ ] `npm run dev` opens in browser
- [ ] Page list renders with titles and dates
- [ ] Clicking a page shows block content
- [ ] Back button returns to list
- [ ] No console errors when API is running
