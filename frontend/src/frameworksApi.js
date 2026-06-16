import { API_BASE as BASE } from "./apiBase"

export async function fetchFrameworksList() {
  const res = await fetch(`${BASE}/frameworks`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function fetchFramework(channel, id) {
  const res = await fetch(`${BASE}/frameworks/${channel}/${encodeURIComponent(id)}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function putFramework(channel, id, yaml_text) {
  const res = await fetch(`${BASE}/frameworks/${channel}/${encodeURIComponent(id)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ yaml_text }),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function deleteFramework(channel, id) {
  const res = await fetch(`${BASE}/frameworks/${channel}/${encodeURIComponent(id)}`, {
    method: "DELETE",
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}
