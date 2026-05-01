const BASE = "http://localhost:8000"

export async function triggerExtract(provider = null, model = null) {
  const body = {}
  if (provider) body.provider = provider
  if (model) body.model = model
  const res = await fetch(`${BASE}/narrative/extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function triggerSynthesize(weekStart = null) {
  const body = weekStart ? { week_start: weekStart } : {}
  const res = await fetch(`${BASE}/narrative/synthesize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function fetchStoryNodes({ since, until, minScore, narrativeFlag, limit = 20, offset = 0 } = {}) {
  const params = new URLSearchParams()
  if (since) params.set("since", since)
  if (until) params.set("until", until)
  if (minScore !== undefined) params.set("min_score", minScore)
  if (narrativeFlag) params.set("narrative_flag", narrativeFlag)
  params.set("limit", limit)
  params.set("offset", offset)
  const res = await fetch(`${BASE}/narrative/story-nodes?${params}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function fetchAllStoryNodes(minScore = 0) {
  const all = []
  let offset = 0
  const limit = 200
  while (true) {
    const res = await fetch(`${BASE}/narrative/story-nodes?min_score=${minScore}&limit=${limit}&offset=${offset}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    all.push(...data.items)
    if (all.length >= data.total) break
    offset += limit
  }
  return all
}

export async function updateStoryNode(id, fields) {
  const res = await fetch(`${BASE}/narrative/story-nodes/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(fields),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function fetchWeeklyIndex(limit = 20) {
  const res = await fetch(`${BASE}/narrative/weekly-index?limit=${limit}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function fetchThreads(status = null, limit = 50) {
  const params = new URLSearchParams({ limit })
  if (status) params.set("status", status)
  const res = await fetch(`${BASE}/narrative/threads?${params}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}