import { useState, useEffect, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { fetchIdeas, createIdea, deleteIdea } from "../ideasApi.js"
import IdeaDetail from "./IdeaDetail.jsx"
import GlassPanel from "./ui/GlassPanel.jsx"
import Icon from "./ui/Icon.jsx"

export default function IdeasTab() {
  const [ideas, setIdeas] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [search, setSearch] = useState("")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [deletingId, setDeletingId] = useState(null)

  const loadIdeas = useCallback(async () => {
    try {
      const data = await fetchIdeas()
      setIdeas(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadIdeas()
  }, [loadIdeas])

  // Listen for "New Idea" sidebar button
  useEffect(() => {
    const handler = () => handleNewIdea()
    window.addEventListener("create-idea", handler)
    return () => window.removeEventListener("create-idea", handler)
  }, [])

  const handleNewIdea = async () => {
    try {
      const idea = await createIdea()
      setIdeas(prev => [idea, ...prev])
      setSelectedId(idea.id)
    } catch (e) {
      setError(e.message)
    }
  }

  const handleIdeaUpdated = (updated) => {
    setIdeas(prev => prev.map(i => i.id === updated.id ? { ...i, ...updated } : i))
  }

  const handleDeleteIdea = async (e, ideaId) => {
    e.stopPropagation()
    if (!window.confirm("Delete this idea and all its drafts?")) return
    setDeletingId(ideaId)
    try {
      await deleteIdea(ideaId)
      setIdeas(prev => prev.filter(i => i.id !== ideaId))
      if (selectedId === ideaId) setSelectedId(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setDeletingId(null)
    }
  }

  const filtered = ideas.filter(i =>
    !search || i.title.toLowerCase().includes(search.toLowerCase()) || i.body.toLowerCase().includes(search.toLowerCase())
  )

  const selectedIdea = ideas.find(i => i.id === selectedId)

  return (
    <div className="flex gap-0 h-[calc(100vh-160px)] relative">
      {/* Decorative glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3/4 h-3/4 bg-gradient-to-r from-amber-500/5 to-violet-500/5 blur-[100px] z-0 pointer-events-none" />

      {/* Left rail */}
      <div className="relative z-10 w-[38%] flex flex-col gap-3 pr-4 border-r border-black/5">
        {/* Search */}
        <div className="relative">
          <Icon name="search" size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search ideas..."
            className="w-full pl-9 pr-4 py-2.5 bg-white/40 border border-black/5 rounded-lg font-body text-body text-on-surface focus:ring-1 focus:ring-primary focus:border-primary outline-none transition-all placeholder:text-outline-variant"
          />
        </div>

        {/* New Idea button */}
        <button
          onClick={handleNewIdea}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg border border-dashed border-primary/30 text-primary font-label-caps text-label-caps hover:bg-primary/5 transition-colors"
        >
          <Icon name="add" size={16} />
          New Idea
        </button>

        {error && (
          <div className="flex items-center gap-2 text-error font-label-caps text-label-caps text-xs">
            <Icon name="error" size={12} /> {error}
          </div>
        )}

        {/* Idea list */}
        <div className="flex-1 overflow-y-auto flex flex-col gap-2 pr-1">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 gap-2 text-center">
              <Icon name="lightbulb" size={28} className="text-outline-variant" />
              <span className="font-body text-body text-on-surface-variant text-sm">
                {search ? "No matching ideas" : "Capture your first idea"}
              </span>
            </div>
          ) : (
            filtered.map((idea, i) => {
              const isActive = selectedId === idea.id
              return (
                <motion.div
                  key={idea.id}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                >
                  <div className="group relative">
                    <button
                      onClick={() => setSelectedId(idea.id)}
                      className={`relative w-full text-left px-4 py-3 rounded-lg transition-all ${
                        isActive ? "bg-white shadow-sm" : "hover:bg-white/60"
                      }`}
                    >
                      {isActive && (
                        <motion.div
                          layoutId="activeIdeaPill"
                          className="absolute inset-0 rounded-lg"
                          style={{
                            background: "linear-gradient(90deg, rgba(70,72,212,0.08) 0%, rgba(129,39,207,0.08) 100%)",
                            border: "1px solid rgba(70,72,212,0.12)",
                          }}
                          transition={{ type: "spring", stiffness: 400, damping: 35 }}
                        />
                      )}
                      <div className="relative z-10 pr-7">
                        <p className={`font-body text-body truncate ${isActive ? "text-primary" : "text-on-surface"}`}>
                          {idea.title || <span className="italic text-on-surface-variant">Untitled</span>}
                        </p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="font-label-caps text-[10px] text-on-surface-variant">
                            {idea.draft_count} {idea.draft_count === 1 ? "draft" : "drafts"}
                          </span>
                          <span className="text-outline-variant">·</span>
                          <span className="font-label-caps text-[10px] text-on-surface-variant">
                            {formatRecency(idea.updated_at)}
                          </span>
                        </div>
                      </div>
                    </button>
                    <button
                      onClick={(e) => handleDeleteIdea(e, idea.id)}
                      disabled={deletingId === idea.id}
                      className="absolute right-2 top-1/2 -translate-y-1/2 z-20 opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded text-outline-variant hover:text-error hover:bg-error/10 disabled:opacity-30"
                      title="Delete idea"
                    >
                      <Icon name={deletingId === idea.id ? "sync" : "delete"} size={14} className={deletingId === idea.id ? "animate-spin" : ""} />
                    </button>
                  </div>
                </motion.div>
              )
            })
          )}
        </div>
      </div>

      {/* Detail pane */}
      <div className="relative z-10 flex-1 pl-6">
        <AnimatePresence mode="wait">
          <motion.div
            key={selectedId ?? "empty"}
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -4 }}
            transition={{ duration: 0.2 }}
            className="h-full"
          >
            <IdeaDetail
              ideaId={selectedId}
              onIdeaUpdated={handleIdeaUpdated}
            />
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  )
}

function formatRecency(isoStr) {
  if (!isoStr) return ""
  const diff = Date.now() - new Date(isoStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins}m`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h`
  const days = Math.floor(hrs / 24)
  if (days < 7) return `${days}d`
  return `${Math.floor(days / 7)}w`
}
