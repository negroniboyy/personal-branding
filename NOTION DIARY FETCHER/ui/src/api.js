const BASE = "http://localhost:8000"

export async function fetchPages() {
  const res = await fetch(`${BASE}/pages`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function fetchPage(id) {
  const res = await fetch(`${BASE}/pages/${id}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}