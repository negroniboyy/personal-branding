import { useState, useEffect, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { fetchIdea, patchIdea, generateLinkedInDraft, generateReelScript, deleteIdeaDraft } from "../ideasApi.js"
import GlassPanel from "./ui/GlassPanel.jsx"
import PrimaryButton from "./ui/PrimaryButton.jsx"
import Icon from "./ui/Icon.jsx"

const CW_BASE = "http://localhost:8000"

function fwLabel(fw, channel) {
  const parts = channel === "linkedin"
    ? [fw.hook_type, fw.tone, fw.cta]
    : [fw.hook_type, fw.tone, fw.cta_type]
  return parts.filter(Boolean).map(s => s.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())).join(" · ")
}

export default function IdeaDetail({ ideaId, onIdeaUpdated }) {
  const [idea, setIdea] = useState(null)
  const [drafts, setDrafts] = useState([])
  const [title, setTitle] = useState("")
  const [body, setBody] = useState("")
  const [generatingLinkedIn, setGeneratingLinkedIn] = useState(false)
  const [generatingReel, setGeneratingReel] = useState(false)
  const [expandedId, setExpandedId] = useState(null)
  const [copiedId, setCopiedId] = useState(null)
  const [deletingDraftId, setDeletingDraftId] = useState(null)
  const [error, setError] = useState(null)
  const saveTimer = useRef(null)

  const [linkedinFrameworks, setLinkedinFrameworks] = useState([])
  const [reelFrameworks, setReelFrameworks] = useState([])
  const [selectedLinkedInFwId, setSelectedLinkedInFwId] = useState("")
  const [selectedReelFwId, setSelectedReelFwId] = useState("")

  useEffect(() => {
    fetch(`${CW_BASE}/content-writer/frameworks`)
      .then(r => r.ok ? r.json() : [])
      .then(setLinkedinFrameworks)
      .catch(() => {})
    fetch(`${CW_BASE}/reels/frameworks`)
      .then(r => r.ok ? r.json() : [])
      .then(setReelFrameworks)
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!ideaId) return
    setError(null)
    fetchIdea(ideaId).then(({ idea, drafts }) => {
      setIdea(idea)
      setTitle(idea.title)
      setBody(idea.body)
      setDrafts(drafts)
    }).catch(e => setError(e.message))
  }, [ideaId])

  const save = async (newTitle, newBody) => {
    if (!ideaId) return
    try {
      const updated = await patchIdea(ideaId, { title: newTitle, body: newBody })
      setIdea(updated)
      onIdeaUpdated?.(updated)
    } catch (e) {
      setError(e.message)
    }
  }

  const scheduleSave = (newTitle, newBody) => {
    clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => save(newTitle, newBody), 600)
  }

  const handleTitleChange = (e) => {
    setTitle(e.target.value)
    scheduleSave(e.target.value, body)
  }

  const handleBodyChange = (e) => {
    setBody(e.target.value)
    scheduleSave(title, e.target.value)
  }

  const handleGenerate = async (channel) => {
    setError(null)
    const setGenerating = channel === "linkedin" ? setGeneratingLinkedIn : setGeneratingReel
    const fn = channel === "linkedin" ? generateLinkedInDraft : generateReelScript
    const fwId = channel === "linkedin" ? selectedLinkedInFwId : selectedReelFwId
    setGenerating(true)
    try {
      const payload = { idea_prompt: body || title || null }
      if (fwId) payload.framework_id = fwId
      const draft = await fn(ideaId, payload)
      setDrafts(prev => [draft, ...prev])
      onIdeaUpdated?.({ ...idea, draft_count: (idea?.draft_count ?? 0) + 1 })
    } catch (e) {
      setError(e.message)
    } finally {
      setGenerating(false)
    }
  }

  const handleCopy = (draft) => {
    navigator.clipboard.writeText(draft.generated_text)
    setCopiedId(draft.id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const handleDeleteDraft = async (e, draft) => {
    e.stopPropagation()
    if (!window.confirm(`Delete this ${draft.channel === "linkedin" ? "LinkedIn" : "Reel"} draft?`)) return
    setDeletingDraftId(draft.id)
    try {
      await deleteIdeaDraft(ideaId, draft.id, draft.channel)
      setDrafts(prev => prev.filter(d => d.id !== draft.id))
      onIdeaUpdated?.({ ...idea, draft_count: Math.max(0, (idea?.draft_count ?? 1) - 1) })
    } catch (err) {
      setError(err.message)
    } finally {
      setDeletingDraftId(null)
    }
  }

  if (!ideaId) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-24 gap-3 text-center">
        <Icon name="lightbulb" size={36} className="text-outline-variant" />
        <span className="font-body text-body text-on-surface-variant">Select an idea or create a new one</span>
      </div>
    )
  }

  if (!idea) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-5 h-full overflow-y-auto pr-1">
      {/* Title */}
      <input
        value={title}
        onChange={handleTitleChange}
        placeholder="Idea title..."
        className="w-full bg-transparent border-b border-black/10 pb-2 font-h2 text-h2 text-on-surface focus:outline-none focus:border-primary transition-colors placeholder:text-outline-variant"
      />

      {/* Body */}
      <textarea
        value={body}
        onChange={handleBodyChange}
        placeholder="Expand on this idea..."
        rows={5}
        className="w-full bg-white/40 border border-black/5 rounded-lg p-4 font-mono-script text-mono-script text-on-surface focus:ring-1 focus:ring-primary focus:border-primary outline-none resize-none transition-all placeholder:text-outline-variant"
      />

      {/* Generate section: framework picker + button per channel */}
      <div className="flex gap-4 flex-wrap">
        {/* LinkedIn */}
        <div className="flex-1 flex flex-col gap-2 min-w-[160px]">
          <label className="font-label-caps text-label-caps text-on-surface-variant">LINKEDIN FRAMEWORK</label>
          <select
            value={selectedLinkedInFwId}
            onChange={e => setSelectedLinkedInFwId(e.target.value)}
            className="glass-panel rounded-lg px-3 py-2 font-body text-body text-on-surface appearance-none focus:border-primary outline-none border-black/5 text-sm"
          >
            <option value="">Auto-pick</option>
            {linkedinFrameworks.map(f => (
              <option key={f.id} value={f.id}>{fwLabel(f, "linkedin")}</option>
            ))}
          </select>
          {selectedLinkedInFwId && linkedinFrameworks.find(f => f.id === selectedLinkedInFwId)?.description && (
            <p className="font-label-caps text-[10px] text-on-surface-variant px-1 italic leading-snug">
              {linkedinFrameworks.find(f => f.id === selectedLinkedInFwId).description}
            </p>
          )}
          <motion.button
            onClick={() => handleGenerate("linkedin")}
            disabled={generatingLinkedIn}
            whileTap={{ scale: 0.98 }}
            className="glass-panel text-primary py-3 px-5 rounded-xl font-label-caps text-label-caps flex items-center justify-center gap-2 hover:bg-white transition-colors border-primary/20 disabled:opacity-40"
          >
            <Icon name={generatingLinkedIn ? "sync" : "edit_note"} size={16} className={generatingLinkedIn ? "animate-spin" : ""} />
            {generatingLinkedIn ? "Generating..." : "+ LinkedIn Draft"}
          </motion.button>
        </div>

        {/* Reel */}
        <div className="flex-1 flex flex-col gap-2 min-w-[160px]">
          <label className="font-label-caps text-label-caps text-on-surface-variant">REEL FRAMEWORK</label>
          <select
            value={selectedReelFwId}
            onChange={e => setSelectedReelFwId(e.target.value)}
            className="glass-panel rounded-lg px-3 py-2 font-body text-body text-on-surface appearance-none focus:border-primary outline-none border-black/5 text-sm"
          >
            <option value="">Auto-pick</option>
            {reelFrameworks.map(f => (
              <option key={f.id} value={f.id}>{fwLabel(f, "reel")}</option>
            ))}
          </select>
          {selectedReelFwId && reelFrameworks.find(f => f.id === selectedReelFwId)?.description && (
            <p className="font-label-caps text-[10px] text-on-surface-variant px-1 italic leading-snug">
              {reelFrameworks.find(f => f.id === selectedReelFwId).description}
            </p>
          )}
          <motion.button
            onClick={() => handleGenerate("reel")}
            disabled={generatingReel}
            whileTap={{ scale: 0.98 }}
            className="glass-panel text-secondary py-3 px-5 rounded-xl font-label-caps text-label-caps flex items-center justify-center gap-2 hover:bg-white transition-colors border-secondary/20 disabled:opacity-40"
          >
            <Icon name={generatingReel ? "sync" : "movie_edit"} size={16} className={generatingReel ? "animate-spin" : ""} />
            {generatingReel ? "Generating..." : "+ Reel Script"}
          </motion.button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-error font-label-caps text-label-caps">
          <Icon name="error" size={14} /> {error}
        </div>
      )}

      {/* Drafts list */}
      <div className="flex flex-col gap-2">
        <h3 className="font-label-caps text-label-caps text-on-surface-variant">
          DRAFTS ({drafts.length})
        </h3>

        {drafts.length === 0 ? (
          <p className="font-body text-body text-on-surface-variant py-4 text-center">
            No drafts yet — generate one above
          </p>
        ) : (
          drafts.map((d, i) => (
            <motion.div
              key={`${d.channel}-${d.id}`}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
            >
              <GlassPanel className="rounded-xl overflow-hidden">
                <div
                  role="button"
                  tabIndex={0}
                  onClick={() => setExpandedId(expandedId === d.id ? null : d.id)}
                  onKeyDown={e => e.key === "Enter" && setExpandedId(expandedId === d.id ? null : d.id)}
                  className="w-full flex items-center justify-between p-4 text-left hover:bg-white/60 transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-label-caps uppercase ${
                      d.channel === "linkedin"
                        ? "bg-primary/10 text-primary border border-primary/20"
                        : "bg-secondary/10 text-secondary border border-secondary/20"
                    }`}>
                      {d.channel === "linkedin" ? "LinkedIn" : "Reel"}
                    </span>
                    <span className="font-label-caps text-[10px] text-on-surface-variant">
                      {d.created_at?.slice(0, 16)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <motion.button
                      onClick={e => { e.stopPropagation(); handleCopy(d) }}
                      whileTap={{ scale: 0.95 }}
                      className="flex items-center gap-1 text-on-surface-variant hover:text-primary px-2 py-1 rounded transition-colors font-label-caps text-[10px]"
                    >
                      <Icon name={copiedId === d.id ? "check" : "content_copy"} size={14} />
                      {copiedId === d.id ? "Copied" : "Copy"}
                    </motion.button>
                    <motion.button
                      onClick={e => handleDeleteDraft(e, d)}
                      disabled={deletingDraftId === d.id}
                      whileTap={{ scale: 0.95 }}
                      className="flex items-center gap-1 text-on-surface-variant hover:text-error px-2 py-1 rounded transition-colors disabled:opacity-30"
                      title="Delete draft"
                    >
                      <Icon name={deletingDraftId === d.id ? "sync" : "delete"} size={14} className={deletingDraftId === d.id ? "animate-spin" : ""} />
                    </motion.button>
                    <Icon name={expandedId === d.id ? "expand_less" : "expand_more"} size={18} className="text-on-surface-variant" />
                  </div>
                </div>

                <AnimatePresence>
                  {expandedId === d.id && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden border-t border-black/5"
                    >
                      <pre className="p-4 font-mono-script text-mono-script text-on-surface whitespace-pre-wrap break-words leading-relaxed text-sm">
                        {d.generated_text}
                      </pre>
                    </motion.div>
                  )}
                </AnimatePresence>
              </GlassPanel>
            </motion.div>
          ))
        )}
      </div>
    </div>
  )
}
