const BASE = "http://localhost:8001"

async function _fetch(path, opts = {}) {
  const res = await fetch(`${BASE}${path}`, opts)
  if (!res.ok) {
    const body = await res.text()
    throw new Error(body || `HTTP ${res.status}`)
  }
  return res.json()
}

export const fetchIdeas = () => _fetch("/ideas")

export const createIdea = () =>
  _fetch("/ideas", { method: "POST" })

export const fetchIdea = (id) => _fetch(`/ideas/${id}`)

export const patchIdea = (id, { title, body }) =>
  _fetch(`/ideas/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, body }),
  })

export const generateLinkedInDraft = (id, payload = {}) =>
  _fetch(`/ideas/${id}/drafts/linkedin`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })

export const generateReelScript = (id, payload = {}) =>
  _fetch(`/ideas/${id}/drafts/reel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
