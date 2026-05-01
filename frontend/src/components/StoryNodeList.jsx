import { useState, useEffect } from "react"
import StoryNodeCard from "./StoryNodeCard"
import { fetchAllStoryNodes } from "../narrativeApi"

export default function StoryNodeList() {
  const [nodes, setNodes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [minScore, setMinScore] = useState(0)
  const [narrativeFlag, setNarrativeFlag] = useState("All")
  const [search, setSearch] = useState("")
  const [sort, setSort] = useState("score")
  const [page, setPage] = useState(0)
  const PER_PAGE = 20

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const all = await fetchAllStoryNodes(minScore)
      setNodes(all)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [minScore])

  const filtered = nodes.filter(n => {
    if (narrativeFlag !== "All" && n.narrative_flag !== narrativeFlag) return false
    if (search) {
      const q = search.toLowerCase()
      return (
        (n.user_state || "").toLowerCase().includes(q) ||
        (n.conflict_node || "").toLowerCase().includes(q) ||
        (n.desired_outcome || "").toLowerCase().includes(q)
      )
    }
    return true
  })

  const sorted = [...filtered].sort((a, b) => {
    if (sort === "score") return b.worth_score - a.worth_score
    return new Date(b.created_time) - new Date(a.created_time)
  })

  const total = sorted.length
  const start = page * PER_PAGE
  const pageItems = sorted.slice(start, start + PER_PAGE)

  const handleUpdate = (updated) => {
    setNodes(ns => ns.map(n => n.id === updated.id ? updated : n))
  }

  return (
    <div>
      <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <label style={{ fontSize: 13, fontWeight: 600 }}>Min Score:</label>
          <input
            type="range" min="0" max="1" step="0.01"
            value={minScore}
            onChange={e => { setMinScore(parseFloat(e.target.value)); setPage(0) }}
            style={{ width: 120 }}
          />
          <span style={{ fontWeight: 700, minWidth: 40, fontSize: 13 }}>{minScore.toFixed(2)}</span>
        </div>

        <div style={{ display: "flex", gap: 4 }}>
          {["All", "Normal", "Low Narrative Potential"].map(f => (
            <button key={f} onClick={() => { setNarrativeFlag(f); setPage(0) }}
              style={{
                padding: "4px 10px", borderRadius: 4, border: "1px solid",
                background: narrativeFlag === f ? "#1565c0" : "#fff",
                color: narrativeFlag === f ? "#fff" : "#444",
                borderColor: narrativeFlag === f ? "#1565c0" : "#ccc",
                cursor: "pointer", fontSize: 12
              }}>
              {f === "All" ? "All" : f === "Normal" ? "Normal" : "Low Potential"}
            </button>
          ))}
        </div>

        <input
          type="text" placeholder="Search user_state, conflict..."
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(0) }}
          style={{ padding: "6px 10px", border: "1px solid #ccc", borderRadius: 4, fontSize: 13, width: 220 }}
        />

        <select value={sort} onChange={e => setSort(e.target.value)} style={{ padding: "6px 10px", border: "1px solid #ccc", borderRadius: 4, fontSize: 13 }}>
          <option value="score">Sort: Score ↓</option>
          <option value="date">Sort: Date ↓</option>
        </select>

        <span style={{ fontSize: 12, color: "#888" }}>{total} stories</span>
      </div>

      {loading && <div style={{ textAlign: "center", padding: 40, color: "#888" }}>Loading...</div>}
      {error && <div style={{ color: "red", padding: 20 }}>Error: {error}</div>}

      {!loading && !error && pageItems.map(node => (
        <StoryNodeCard key={node.id} node={node} onUpdate={handleUpdate} />
      ))}

      {!loading && total > PER_PAGE && (
        <div style={{ display: "flex", justifyContent: "center", gap: 12, marginTop: 20 }}>
          <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}
            style={{ padding: "6px 16px", borderRadius: 4, border: "1px solid #ccc", cursor: "pointer" }}>
            Prev
          </button>
          <span style={{ padding: "6px 12px", fontSize: 13, color: "#666" }}>
            {start + 1}–{Math.min(start + PER_PAGE, total)} of {total}
          </span>
          <button onClick={() => setPage(p => start + PER_PAGE < total ? p + 1 : p)} disabled={start + PER_PAGE >= total}
            style={{ padding: "6px 16px", borderRadius: 4, border: "1px solid #ccc", cursor: "pointer" }}>
            Next
          </button>
        </div>
      )}
    </div>
  )
}