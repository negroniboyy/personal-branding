import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import StoryNodeCard from "./StoryNodeCard"
import { fetchAllStoryNodes } from "../narrativeApi"
import GlassPanel from "./ui/GlassPanel.jsx"
import Icon from "./ui/Icon.jsx"

const PER_PAGE = 20
const MIN_SCORE = 0.8

export default function StoryNodeList({ onCreate }) {
  const [nodes, setNodes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState("")
  const [sort, setSort] = useState("score")
  const [page, setPage] = useState(0)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const all = await fetchAllStoryNodes(MIN_SCORE)
      setNodes(all)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const filtered = nodes.filter(n => {
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
        <span className="font-label-caps text-label-caps text-primary bg-primary/5 border border-primary/10 px-2 py-1 rounded">
          SCORE ≥ 0.80
        </span>

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
          <StoryNodeCard node={node} onUpdate={handleUpdate} onCreate={onCreate} />
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
