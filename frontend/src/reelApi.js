const BASE = "http://localhost:8000"

export async function fetchReelFrameworks() {
  const res = await fetch(`${BASE}/reels/frameworks`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function postReelRecommendations({ idea_prompt = null, top_n = 5 } = {}) {
  const res = await fetch(`${BASE}/reels/recommendations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ idea_prompt, top_n }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function postReelGenerate({ story_node_id, framework_id, idea_prompt = null }) {
  const res = await fetch(`${BASE}/reels/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ story_node_id, framework_id, idea_prompt }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function fetchReelScripts() {
  const res = await fetch(`${BASE}/reels/scripts`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function fetchReelScript(id) {
  const res = await fetch(`${BASE}/reels/scripts/${id}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function postReelScan() {
  const res = await fetch(`${BASE}/reels/scan`, {
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

export async function postReelOpenReferences() {
  const res = await fetch(`${BASE}/reels/open-references`, {
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
