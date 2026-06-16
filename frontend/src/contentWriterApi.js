import { API_BASE as BASE } from "./apiBase"

export async function fetchFrameworks() {
  const res = await fetch(`${BASE}/content-writer/frameworks`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function postRecommendations({ idea_prompt = null, top_n = 20, domain = null } = {}) {
  const res = await fetch(`${BASE}/content-writer/recommendations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ idea_prompt, top_n, domain }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function postGenerate({ story_node_id, framework_id, idea_prompt = null, provider = "openrouter", model = "openai/gpt-oss-120b:free" }) {
  const res = await fetch(`${BASE}/content-writer/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ story_node_id, framework_id, idea_prompt, provider, model }),
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
