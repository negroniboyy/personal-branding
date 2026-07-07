import { useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  postGenerate,
  fetchDrafts,
  fetchDraft,
  patchDraft,
  deleteDraft,
  openDraftsFolder,
} from "../contentWriterApi.js"
import GlassPanel from "./ui/GlassPanel.jsx"
import PrimaryButton from "./ui/PrimaryButton.jsx"
import Icon from "./ui/Icon.jsx"
import { ModelSelector } from "./ModelSelector.jsx"
import { useJob } from "../lib/useJob.js"

export default function ContentWriter() {
  const [ideaPrompt, setIdeaPrompt] = useState("")
  const [drafts, setDrafts] = useState([])
  const [activeDraft, setActiveDraft] = useState(null)
  const [jobId, setJobId] = useState(null)
  const [editedText, setEditedText] = useState("")
  const [saving, setSaving] = useState(false)
  const [deletingId, setDeletingId] = useState(null)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState(null)
  const [selectedModel, setSelectedModel] = useState("google/gemma-4-26b-a4b-it")

  const { job } = useJob(jobId, {
    onDone: (draft) => {
      setActiveDraft(draft)
      setEditedText(draft.generated_text)
      setJobId(null)
      loadDrafts()
    },
    onError: (msg) => { setError(msg); setJobId(null) },
  })
  const generating = !!jobId

  const loadDrafts = async () => {
    try { setDrafts(await fetchDrafts()) } catch { /* non-blocking */ }
  }

  useEffect(() => { loadDrafts() }, [])

  const canGenerate = ideaPrompt.trim()

  const handleGenerate = async () => {
    if (!canGenerate) return
    setError(null)
    setActiveDraft(null)
    try {
      const { job_id } = await postGenerate({
        idea_prompt: ideaPrompt || null,
        model: selectedModel,
        provider: "openrouter",
      })
      setJobId(job_id)
    } catch (e) {
      setError(e.message)
    }
  }

  const handleSelectDraft = async (id) => {
    try {
      const d = await fetchDraft(id)
      setActiveDraft(d)
      setEditedText(d.generated_text)
    } catch (e) { setError(e.message) }
  }

  const handleSave = async () => {
    if (!activeDraft || saving) return
    setSaving(true)
    setError(null)
    try {
      await patchDraft(activeDraft.draft_id ?? activeDraft.id, editedText)
      setActiveDraft(prev => ({ ...prev, generated_text: editedText }))
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteDraft = async (e, draftId) => {
    e.stopPropagation()
    if (!window.confirm("Delete this draft?")) return
    setDeletingId(draftId)
    setError(null)
    try {
      await deleteDraft(draftId)
      // eslint-disable-next-line eqeqeq
      setDrafts(prev => prev.filter(d => d.id != draftId))
      // eslint-disable-next-line eqeqeq
      if ((activeDraft?.draft_id ?? activeDraft?.id) == draftId) {
        setActiveDraft(null)
        setEditedText("")
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setDeletingId(null)
    }
  }

  const handleOpenFolder = async () => {
    setError(null)
    try { await openDraftsFolder() } catch (e) { setError(e.message) }
  }

  const handleCopy = () => {
    if (!activeDraft?.generated_text) return
    navigator.clipboard.writeText(activeDraft.generated_text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="flex flex-col gap-8 relative">
      {/* Decorative glow blob */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3/4 h-3/4 bg-gradient-to-r from-indigo-500/5 to-violet-500/5 blur-[100px] z-0 pointer-events-none" />

      {/* --- Input section --- */}
      <section className="relative z-10 flex flex-col gap-4">
        {/* Idea hint */}
        <GlassPanel className="rounded-xl p-card_padding">
          <label className="font-label-caps text-label-caps text-on-surface-variant block mb-3">IDEA HINT</label>
          <textarea
            value={ideaPrompt}
            onChange={e => setIdeaPrompt(e.target.value)}
            placeholder="Type your content kernel here..."
            rows={4}
            className="w-full bg-white/40 border border-black/5 rounded-lg p-4 font-mono-script text-mono-script text-on-surface focus:ring-1 focus:ring-primary focus:border-primary outline-none resize-none transition-all placeholder:text-outline-variant"
          />
        </GlassPanel>

        {/* Actions row */}
        <div className="flex gap-3 flex-wrap items-center">
          <ModelSelector
            task="generate_linkedin_post"
            value={selectedModel}
            onChange={setSelectedModel}
          />
          <PrimaryButton
            onClick={handleGenerate}
            disabled={generating || !canGenerate}
            icon={generating ? "hourglass_top" : "temp_preferences_custom"}
            className="flex-1"
          >
            {generating ? (job?.status === "running" ? "Generating..." : "Queued...") : "Generate Draft"}
          </PrimaryButton>
        </div>
        <p className="font-label-caps text-[10px] text-on-surface-variant -mt-2 px-1">
          The framework is picked automatically. You can leave this page — generation keeps running.
        </p>

        {error && (
          <div className="flex items-center gap-2 text-error font-label-caps text-label-caps">
            <Icon name="error" size={14} /> {error}
          </div>
        )}
      </section>

      {/* --- Canvas --- */}
      <section className="relative z-10">
        {(() => {
          const isDirty = activeDraft && editedText !== activeDraft.generated_text
          return (
            <GlassPanel className="rounded-xl overflow-hidden min-h-[400px] relative">
              <div className="flex items-center justify-between px-6 py-4 border-b border-black/5 bg-gradient-to-r from-indigo-50/50 to-violet-50/50">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full shadow-[0_0_8px_rgba(70,72,212,0.4)] ${activeDraft ? "bg-primary animate-pulse" : "bg-outline-variant"}`} />
                  <span className="font-label-caps text-label-caps text-on-surface">
                    GENERATED DRAFT{isDirty ? " *" : ""}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {activeDraft && (
                    <>
                      <motion.button
                        onClick={handleOpenFolder}
                        whileTap={{ scale: 0.95 }}
                        title="Open drafts folder"
                        className="flex items-center gap-1.5 text-on-surface-variant hover:text-primary px-3 py-1.5 rounded-lg transition-colors font-label-caps text-label-caps border border-black/5 hover:border-primary/20"
                      >
                        <Icon name="folder_open" size={15} />
                        Folder
                      </motion.button>
                      <motion.button
                        onClick={handleSave}
                        whileTap={{ scale: 0.95 }}
                        disabled={!isDirty || saving}
                        className="flex items-center gap-1.5 text-primary hover:bg-primary/5 px-3 py-1.5 rounded-lg transition-colors font-label-caps text-label-caps border border-primary/20 disabled:opacity-30"
                      >
                        <Icon name={saving ? "sync" : "save"} size={15} className={saving ? "animate-spin" : ""} />
                        {saving ? "Saving..." : "Save"}
                      </motion.button>
                      <motion.button
                        onClick={(e) => handleDeleteDraft(e, activeDraft.draft_id ?? activeDraft.id)}
                        whileTap={{ scale: 0.95 }}
                        disabled={deletingId === (activeDraft.draft_id ?? activeDraft.id)}
                        className="flex items-center gap-1.5 text-outline-variant hover:text-error hover:bg-error/5 px-3 py-1.5 rounded-lg transition-colors font-label-caps text-label-caps border border-black/5 hover:border-error/20 disabled:opacity-30"
                      >
                        <Icon name="delete" size={15} />
                      </motion.button>
                    </>
                  )}
                  <motion.button
                    onClick={handleCopy}
                    whileTap={{ scale: 0.95 }}
                    disabled={!activeDraft}
                    className="flex items-center gap-2 text-primary hover:bg-primary/5 px-3 py-1.5 rounded-lg transition-colors font-label-caps text-label-caps border border-primary/20 backdrop-blur-sm disabled:opacity-30"
                  >
                    <Icon name={copied ? "check" : "content_copy"} size={16} />
                    {copied ? "Copied!" : "Copy"}
                  </motion.button>
                </div>
              </div>

              <div className="p-8">
                <AnimatePresence mode="wait">
                  {generating ? (
                    <motion.div key="generating" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center justify-center py-16 gap-3">
                      <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                      <span className="font-label-caps text-label-caps text-on-surface-variant">Generating your draft...</span>
                    </motion.div>
                  ) : activeDraft ? (
                    <motion.div key="draft" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
                      {activeDraft.framework_id && (
                        <p className="font-label-caps text-[10px] text-on-surface-variant italic mb-3">
                          Framework: {activeDraft.framework_id}
                          {activeDraft.framework_pick_reason ? ` — ${activeDraft.framework_pick_reason}` : ""}
                        </p>
                      )}
                      <textarea
                        value={editedText}
                        onChange={e => setEditedText(e.target.value)}
                        className="w-full min-h-[300px] bg-transparent font-mono-script text-mono-script text-on-surface leading-relaxed resize-y outline-none border-none whitespace-pre-wrap"
                        spellCheck={false}
                      />
                    </motion.div>
                  ) : (
                    <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center justify-center py-16 gap-2 text-center">
                      <Icon name="edit_note" size={32} className="text-outline-variant" />
                      <span className="font-body text-body text-on-surface-variant">Write an idea and click Generate Draft</span>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {activeDraft && (
                <div className="absolute bottom-4 right-6 flex items-center gap-2 flex-wrap justify-end">
                  <span className="px-3 py-1 glass-panel text-[10px] font-label-caps text-primary uppercase border-primary/10">
                    Draft #{activeDraft.draft_id ?? activeDraft.id}
                  </span>
                  <span className="px-3 py-1 glass-panel text-[10px] font-label-caps text-secondary uppercase border-secondary/10">
                    {activeDraft.model_used}
                  </span>
                  {activeDraft.latency_ms != null && (
                    <span className="px-3 py-1 glass-panel text-[10px] font-label-caps text-on-surface-variant border-black/5">
                      {activeDraft.latency_ms}ms · {activeDraft.tokens?.total ?? 0}t · ${(activeDraft.cost_usd ?? 0).toFixed(6)}
                    </span>
                  )}
                </div>
              )}
            </GlassPanel>
          )
        })()}
      </section>

      {/* --- Recent drafts --- */}
      {drafts.length > 0 && (
        <section className="relative z-10 flex flex-col gap-3">
          <h3 className="font-label-caps text-label-caps text-on-surface-variant px-2">RECENT DRAFTS</h3>
          <div className="flex flex-col gap-3">
            {drafts.slice(0, 10).map((d, i) => (
              <motion.div
                key={d.id}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
              >
                <GlassPanel
                  as="div"
                  onClick={() => handleSelectDraft(d.id)}
                  className={`group relative w-full text-left hover:border-primary/30 hover:bg-white p-card_padding rounded-xl flex items-center justify-between transition-all cursor-pointer ${activeDraft?.id === d.id ? "border-primary/30 bg-white" : ""}`}
                >
                  <div className="flex items-center gap-4">
                    <div className="bg-primary/5 border border-primary/10 p-2 rounded-lg">
                      <Icon name="description" size={20} className="text-primary" />
                    </div>
                    <div>
                      <p className="font-body text-body text-on-surface">Draft #{d.id}</p>
                      <p className="font-label-caps text-[10px] text-on-surface-variant mt-0.5">
                        {d.created_at?.slice(0, 16)} · {d.model_used?.toUpperCase()}
                      </p>
                    </div>
                  </div>
                  <Icon name="chevron_right" size={20} className="text-on-surface-variant group-hover:opacity-0 transition-opacity" />
                  <button
                    onClick={(e) => handleDeleteDraft(e, d.id)}
                    disabled={deletingId === d.id}
                    className="absolute right-3 top-1/2 -translate-y-1/2 z-20 opacity-0 group-hover:opacity-100 transition-opacity p-2 rounded-lg text-outline-variant hover:text-error hover:bg-error/10 disabled:opacity-30"
                    title="Delete draft"
                  >
                    <Icon name={deletingId === d.id ? "sync" : "delete"} size={16} className={deletingId === d.id ? "animate-spin" : ""} />
                  </button>
                </GlassPanel>
              </motion.div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
