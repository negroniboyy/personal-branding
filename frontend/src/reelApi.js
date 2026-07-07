import { API_BASE as BASE } from "./apiBase"

export async function postReelGenerate({ idea_prompt = null, model = null, provider = null }) {
  const res = await fetch(`${BASE}/reels/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ idea_prompt, model, provider }),
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

export async function fetchReelScriptVersions(id) {
  const res = await fetch(`${BASE}/reels/scripts/${id}/versions`)
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

export async function patchReelScript(id, generated_text) {
  const res = await fetch(`${BASE}/reels/scripts/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ generated_text }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function patchReelScriptMeta(id, meta) {
  const res = await fetch(`${BASE}/reels/scripts/${id}/meta`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(meta),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function postReelPackage(id, model = null) {
  const res = await fetch(`${BASE}/reels/scripts/${id}/package`, {
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

export async function deleteReelScript(id) {
  const res = await fetch(`${BASE}/reels/scripts/${id}`, { method: "DELETE" })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function postReelOpenScripts() {
  const res = await fetch(`${BASE}/reels/open-scripts-folder`, {
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
