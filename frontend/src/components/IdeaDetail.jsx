import { useState, useEffect, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { fetchIdea, patchIdea, generateLinkedInDraft, generateReelScript, deleteIdeaDraft, setIdeaTier } from "../ideasApi.js"
import GlassPanel from "./ui/GlassPanel.jsx"
import Icon from "./ui/Icon.jsx"
import { useJob } from "../lib/useJob.js"

const TIER_OPTIONS = [
  { value: "scripted-headshot", label: "Scripted headshot" },
  { value: "raw-talking-head", label: "Raw talking head" },
  { value: "beat-edit", label: "Beat edit" },
]

export default function IdeaDetail({ ideaId, onIdeaUpdated }) {
  const [idea, setIdea] = useState(null)
  const [drafts, setDrafts] = useState([])
  const [title, setTitle] = useState("")
  const [body, setBody] = useState("")
  const [linkedinJobId, setLinkedinJobId] = useState(null)
  const [reelJobId, setReelJobId] = useState(null)
  const [expandedId, setExpandedId] = useState(null)
  const [copiedId, setCopiedId] = useState(null)
  const [deletingDraftId, setDeletingDraftId] = useState(null)
  const [error, setError] = useState(null)
  const [savingTier, setSavingTier] = useState(false)
  const saveTimer = useRef(null)

  const handleDraftDone = (draft) => {
    setDrafts(prev => [draft, ...prev])
    onIdeaUpdated?.({ ...idea, draft_count: (idea?.draft_count ?? 0) + 1 })
  }

  const { job: linkedinJob } = useJob(linkedinJobId, {
    onDone: (draft) => { handleDraftDone(draft); setLinkedinJobId(null) },
    onError: (msg) => { setError(msg); setLinkedinJobId(null) },
  })
  const { job: reelJob } = useJob(reelJobId, {
    onDone: (draft) => { handleDraftDone(draft); setReelJobId(null) },
    onError: (msg) => { setError(msg); setReelJobId(null) },
  })
  const generatingLinkedIn = !!linkedinJobId
  const generatingReel = !!reelJobId

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
    const fn = channel === "linkedin" ? generateLinkedInDraft : generateReelScript
    const setJobId = channel === "linkedin" ? setLinkedinJobId : setReelJobId
    try {
      const { job_id } = await fn(ideaId, { idea_prompt: body || title || null })
      setJobId(job_id)
    } catch (e) {
      setError(e.message)
    }
  }

  const handleTierChange = async (e) => {
    const tier = e.target.value
    setSavingTier(true)
    setError(null)
    try {
      const updated = await setIdeaTier(ideaId, tier)
      setIdea(updated)
      onIdeaUpdated?.(updated)
    } catch (err) {
      setError(err.message)
    } finally {
      setSavingTier(false)
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

  const isNotionLinked = !!idea.notion_page_id
  const hasReelDraft = drafts.some(d => d.channel === "reel")

  return (
    <div className="flex flex-col gap-5 md:h-full md:overflow-y-auto md:pr-1">
      {isNotionLinked && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="px-2 py-0.5 rounded bg-black/5 font-label-caps text-[10px] text-on-surface-variant">
            Synced from Notion — edit content there
          </span>
          {idea.pillar && (
            <span className="px-2 py-0.5 rounded bg-primary/10 text-primary font-label-caps text-[10px]">
              {idea.pillar}
            </span>
          )}
          {(idea.channels || []).map(ch => (
            <span key={ch} className="px-2 py-0.5 rounded bg-black/5 font-label-caps text-[10px] text-on-surface-variant">
              {ch}
            </span>
          ))}
        </div>
      )}

      {/* Tier picker — a PBS-side production decision, editable even when the idea's content is Notion-linked */}
      <div className="flex items-center gap-2">
        <span className="font-label-caps text-[10px] text-on-surface-variant">REEL TIER</span>
        <select
          value={idea.tier || "scripted-headshot"}
          onChange={handleTierChange}
          disabled={savingTier}
          className="bg-white/40 border border-black/10 rounded-lg px-2 py-1 font-label-caps text-[10px] text-on-surface focus:ring-1 focus:ring-primary outline-none disabled:opacity-50"
        >
          {TIER_OPTIONS.map(t => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
        {savingTier && <div className="w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin" />}
      </div>

      {/* Title */}
      <input
        value={title}
        onChange={handleTitleChange}
        readOnly={isNotionLinked}
        placeholder="Idea title..."
        className="w-full bg-transparent border-b border-black/10 pb-2 font-h2 text-h2 text-on-surface focus:outline-none focus:border-primary transition-colors placeholder:text-outline-variant disabled:opacity-70"
      />

      {/* Body */}
      <textarea
        value={body}
        onChange={handleBodyChange}
        readOnly={isNotionLinked}
        placeholder="Write your draft here — this becomes the source material. The framework will shape it."
        rows={5}
        className="w-full bg-white/40 border border-black/5 rounded-lg p-4 font-mono-script text-mono-script text-on-surface focus:ring-1 focus:ring-primary focus:border-primary outline-none resize-none transition-all placeholder:text-outline-variant"
      />

      {/* Generate section: the LLM picks the framework — no dropdown needed */}
      <div className="flex gap-4 flex-wrap">
        <motion.button
          onClick={() => handleGenerate("linkedin")}
          disabled={generatingLinkedIn}
          whileTap={{ scale: 0.98 }}
          className="flex-1 min-w-[160px] glass-panel text-primary py-3 px-5 rounded-xl font-label-caps text-label-caps flex items-center justify-center gap-2 hover:bg-white transition-colors border-primary/20 disabled:opacity-40"
        >
          <Icon name={generatingLinkedIn ? "sync" : "edit_note"} size={16} className={generatingLinkedIn ? "animate-spin" : ""} />
          {generatingLinkedIn ? (linkedinJob?.status === "running" ? "Generating..." : "Queued...") : "+ LinkedIn Draft"}
        </motion.button>

        <motion.button
          onClick={() => handleGenerate("reel")}
          disabled={generatingReel}
          whileTap={{ scale: 0.98 }}
          className="flex-1 min-w-[160px] glass-panel text-secondary py-3 px-5 rounded-xl font-label-caps text-label-caps flex items-center justify-center gap-2 hover:bg-white transition-colors border-secondary/20 disabled:opacity-40"
        >
          <Icon name={generatingReel ? "sync" : "movie_edit"} size={16} className={generatingReel ? "animate-spin" : ""} />
          {generatingReel
            ? (reelJob?.status === "running" ? "Generating..." : "Queued...")
            : (hasReelDraft ? "Regenerate Reel" : "+ Reel Script")}
        </motion.button>
      </div>
      <p className="font-label-caps text-[10px] text-on-surface-variant -mt-2 px-1">
        You can leave this page — generation keeps running and the draft will be here when you're back.
      </p>

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
                    {d.channel === "reel" && (
                      <span className="px-1.5 py-0.5 rounded bg-black/5 font-label-caps text-[9px] text-on-surface-variant">
                        v{d.version || 1}
                      </span>
                    )}
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
                      {d.framework_id && (
                        <p className="px-4 pt-3 font-label-caps text-[10px] text-on-surface-variant italic leading-snug">
                          Framework: {d.framework_id}{d.framework_pick_reason ? ` — ${d.framework_pick_reason}` : ""}
                        </p>
                      )}
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
