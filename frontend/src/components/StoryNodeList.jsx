import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import StoryNodeCard from "./StoryNodeCard"
import { fetchAllStoryNodes } from "../narrativeApi"
import GlassPanel from "./ui/GlassPanel.jsx"
import Icon from "./ui/Icon.jsx"

const PER_PAGE = 20

export default function StoryNodeList() {
  const [nodes, setNodes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [minScore, setMinScore] = useState(0)
  const [narrativeFlag, setNarrativeFlag] = useState("All")
  const [search, setSearch] = useState("")
  const [sort, setSort] = useState("score")
  const [page, setPage] = useState(0)

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

  const sorted = [...filtered].sort((a, b) =>
    sort === "score" ? b.worth_score - a.worth_score : new Date(b.created_time) - new Date(a.created_time)
  )

  const total = sorted.length
  const start = page * PER_PAGE
  const pageItems = sorted.slice(start, start + PER_PAGE)
  const handleUpdate = updated => setNodes(ns => ns.map(n => n.id === updated.id ? updated : n))

  return (
    <div className="flex flex-col gap-4">
      {/* Filters bar */}
      <GlassPanel className="rounded-xl p-card_padding flex flex-wrap gap-4 items-center">
        {/* Min score */}
        <div className="flex items-center gap-3">
          <span className="font-label-caps text-label-caps text-on-surface-variant">MIN SCORE</span>
          <input
            type="range" min="0" max="1" step="0.01"
            value={minScore}
            onChange={e => { setMinScore(parseFloat(e.target.value)); setPage(0) }}
            className="w-24 accent-primary"
          />
          <span className="font-label-caps text-label-caps text-primary min-w-[36px]">{minScore.toFixed(2)}</span>
        </div>

        {/* Flag filter */}
        <div className="flex gap-1">
          {[["All", "All"], ["Normal", "Normal"], ["Low Narrative Potential", "Low"]].map(([value, label]) => (
            <button
              key={value}
              onClick={() => { setNarrativeFlag(value); setPage(0) }}
              className={`px-3 py-1.5 rounded-lg font-label-caps text-label-caps transition-all ${
                narrativeFlag === value
                  ? "bg-primary text-on-primary"
                  : "glass-panel text-on-surface-variant hover:text-on-surface"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative flex-1 min-w-[180px]">
          <Icon name="search" size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant" />
          <input
            type="text"
            placeholder="Search..."
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(0) }}
            className="w-full glass-panel rounded-lg pl-9 pr-4 py-2 font-body text-body text-on-surface focus:ring-1 focus:ring-primary outline-none border-black/5"
          />
        </div>

        {/* Sort */}
        <select
          value={sort}
          onChange={e => setSort(e.target.value)}
          className="glass-panel rounded-lg px-4 py-2 font-label-caps text-label-caps text-on-surface appearance-none focus:border-primary outline-none border-black/5"
        >
          <option value="score">Score ↓</option>
          <option value="date">Date ↓</option>
        </select>

        <span className="font-label-caps text-label-caps text-outline ml-auto">{total} stories</span>
      </GlassPanel>

      {loading && (
        <div className="flex flex-col gap-3">
          {[...Array(3)].map((_, i) => (
            <GlassPanel key={i} className="rounded-xl p-card_padding animate-pulse">
              <div className="h-4 bg-surface-container rounded w-1/3 mb-3" />
              <div className="h-3 bg-surface-container rounded w-full mb-2" />
              <div className="h-3 bg-surface-container rounded w-3/4" />
            </GlassPanel>
          ))}
        </div>
      )}

      {error && (
        <GlassPanel className="rounded-xl p-card_padding border-error/20">
          <div className="flex items-center gap-2 text-error font-label-caps text-label-caps">
            <Icon name="error" size={14} /> {error}
          </div>
        </GlassPanel>
      )}

      {!loading && !error && pageItems.map((node, i) => (
        <motion.div
          key={node.id}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.03 }}
        >
          <StoryNodeCard node={node} onUpdate={handleUpdate} />
        </motion.div>
      ))}

      {!loading && total > PER_PAGE && (
        <div className="flex justify-center items-center gap-3 mt-2">
          <button
            onClick={() => setPage(p => Math.max(0, p - 1))}
            disabled={page === 0}
            className="glass-panel px-4 py-2 rounded-lg font-label-caps text-label-caps text-on-surface-variant disabled:opacity-40 hover:text-primary transition-colors"
          >
            ← Prev
          </button>
          <span className="font-label-caps text-label-caps text-on-surface-variant">
            {start + 1}–{Math.min(start + PER_PAGE, total)} of {total}
          </span>
          <button
            onClick={() => setPage(p => start + PER_PAGE < total ? p + 1 : p)}
            disabled={start + PER_PAGE >= total}
            className="glass-panel px-4 py-2 rounded-lg font-label-caps text-label-caps text-on-surface-variant disabled:opacity-40 hover:text-primary transition-colors"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  )
}
