import { API_BASE as BASE } from "./apiBase"

export async function postGenerate({ idea_prompt = null, provider = "openrouter", model = null }) {
  const res = await fetch(`${BASE}/content-writer/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ idea_prompt, provider, model }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function fetchDrafts() {
  const res = await fetch(`${BASE}/content-writer/drafts`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function fetchDraft(id) {
  const res = await fetch(`${BASE}/content-writer/drafts/${id}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function patchDraft(id, generated_text) {
  const res = await fetch(`${BASE}/content-writer/drafts/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ generated_text }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function patchDraftMeta(id, meta) {
  const res = await fetch(`${BASE}/content-writer/drafts/${id}/meta`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(meta),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function postDraftPackage(id, model = null) {
  const res = await fetch(`${BASE}/content-writer/drafts/${id}/package`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model }),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function deleteDraft(id) {
  const res = await fetch(`${BASE}/content-writer/drafts/${id}`, { method: "DELETE" })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function openDraftsFolder() {
  const res = await fetch(`${BASE}/content-writer/open-folder`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || `HTTP ${res.status}`)
  }
  return res.json()
}
