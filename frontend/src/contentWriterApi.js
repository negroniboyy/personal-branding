const BASE = "http://localhost:8000"

export async function fetchFrameworks() {
  const res = await fetch(`${BASE}/content-writer/frameworks`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function postRecommendations({ idea_prompt = null, top_n = 5 } = {}) {
  const res = await fetch(`${BASE}/content-writer/recommendations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ idea_prompt, top_n }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function postGenerate({ story_node_id, framework_id, idea_prompt = null, provider = "ollama", model = "gemma3:latest" }) {
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
