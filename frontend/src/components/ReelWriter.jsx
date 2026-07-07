import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  postReelGenerate,
  fetchReelScripts,
  fetchReelScript,
  patchReelScript,
  deleteReelScript,
  postReelOpenScripts,
  postReelScan,
  postReelOpenReferences,
} from "../reelApi.js"
import GlassPanel from "./ui/GlassPanel.jsx"
import PrimaryButton from "./ui/PrimaryButton.jsx"
import Icon from "./ui/Icon.jsx"
import { ModelSelector } from "./ModelSelector.jsx"
import { useJob } from "../lib/useJob.js"

function ScanJobRow({ file, jobId, onSettled }) {
  const { job, error } = useJob(jobId, {
    onDone: () => onSettled(),
    onError: () => onSettled(),
  })
  const status = job?.status || "queued"
  const icon = status === "done" ? "check_circle" : status === "failed" ? "error" : "sync"
  const color = status === "done" ? "text-primary" : status === "failed" ? "text-error" : "text-on-surface-variant"
  return (
    <li className={`font-mono-script text-mono-script flex items-center gap-2 ${color}`}>
      <Icon name={icon} size={14} className={status !== "done" && status !== "failed" ? "animate-spin" : ""} />
      {file}
      {status === "failed" && `: ${job?.error || error || "failed"}`}
    </li>
  )
}

export default function ReelWriter() {
  const [ideaPrompt, setIdeaPrompt] = useState("")
  const [scripts, setScripts] = useState([])
  const [activeScript, setActiveScript] = useState(null)
  const [jobId, setJobId] = useState(null)
  const [scanJobs, setScanJobs] = useState(null)
  const [settledCount, setSettledCount] = useState(0)
  const [editedText, setEditedText] = useState("")
  const [saving, setSaving] = useState(false)
  const [deletingId, setDeletingId] = useState(null)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState(null)
  const [selectedModel, setSelectedModel] = useState("qwen/qwen3-235b-a22b-thinking-2507")

  const { job } = useJob(jobId, {
    onDone: (result) => {
      setActiveScript(result)
      setEditedText(result.generated_text)
      setJobId(null)
      loadScripts()
    },
    onError: (msg) => { setError(msg); setJobId(null) },
  })
  const generating = !!jobId
  const scanning = scanJobs != null && settledCount < scanJobs.length

  const loadScripts = async () => {
    try { setScripts(await fetchReelScripts()) } catch { /* non-blocking */ }
  }

  useEffect(() => { loadScripts() }, [])

  const canGenerate = ideaPrompt.trim()

  const handleGenerate = async () => {
    if (!canGenerate) return
    setError(null)
    setActiveScript(null)
    try {
      const { job_id } = await postReelGenerate({
        idea_prompt: ideaPrompt || null,
        model: selectedModel,
        provider: "openrouter",
      })
      setJobId(job_id)
    } catch (e) {
      setError(e.message)
    }
  }

  const handleSelectScript = async (id) => {
    try {
      const s = await fetchReelScript(id)
      const script = { script_id: s.id, generated_text: s.generated_text, story_node_id: s.story_node_id, framework_id: s.framework_id, framework_pick_reason: s.framework_pick_reason, model_used: s.model_used, created_at: s.created_at }
      setActiveScript(script)
      setEditedText(s.generated_text)
    } catch (e) { setError(e.message) }
  }

  const handleSave = async () => {
    if (!activeScript || saving) return
    setSaving(true)
    setError(null)
    try {
      await patchReelScript(activeScript.script_id, editedText)
      setActiveScript(prev => ({ ...prev, generated_text: editedText }))
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteScript = async (e, scriptId) => {
    e.stopPropagation()
    if (!window.confirm("Delete this script?")) return
    setDeletingId(scriptId)
    setError(null)
    try {
      await deleteReelScript(scriptId)
      // eslint-disable-next-line eqeqeq
      setScripts(prev => prev.filter(s => s.id != scriptId))
      // eslint-disable-next-line eqeqeq
      if (activeScript?.script_id == scriptId) {
        setActiveScript(null)
        setEditedText("")
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setDeletingId(null)
    }
  }

  const handleOpenScripts = async () => {
    setError(null)
    try { await postReelOpenScripts() } catch (e) { setError(e.message) }
  }

  const handleOpenReferences = async () => {
    setError(null)
    try { await postReelOpenReferences() } catch (e) { setError(e.message) }
  }

  const handleScan = async () => {
    setError(null)
    setSettledCount(0)
    try {
      const r = await postReelScan()
      setScanJobs(r.jobs)
      if (r.jobs.length === 0) setSettledCount(0)
    } catch (e) {
      setError(e.message)
    }
  }

  const handleScanSettled = () => {
    setSettledCount(c => {
      const next = c + 1
      if (scanJobs && next >= scanJobs.length) loadScripts()
      return next
    })
  }

  const handleCopy = () => {
    if (!activeScript?.generated_text) return
    navigator.clipboard.writeText(activeScript.generated_text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="flex flex-col gap-8 relative">
      {/* Decorative glow blob */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3/4 h-3/4 bg-gradient-to-r from-violet-500/5 to-pink-500/5 blur-[100px] z-0 pointer-events-none" />

      {/* --- Input section --- */}
      <section className="relative z-10 flex flex-col gap-4">
        <GlassPanel className="rounded-xl p-card_padding">
          <label className="font-label-caps text-label-caps text-on-surface-variant block mb-3">IDEA HINT</label>
          <textarea
            value={ideaPrompt}
            onChange={e => setIdeaPrompt(e.target.value)}
            placeholder="e.g. the moment you stopped chasing approval..."
            rows={4}
            className="w-full bg-white/40 border border-black/5 rounded-lg p-4 font-mono-script text-mono-script text-on-surface focus:ring-1 focus:ring-primary focus:border-primary outline-none resize-none transition-all placeholder:text-outline-variant"
          />
        </GlassPanel>

        <div className="flex gap-3 flex-wrap items-center">
          <ModelSelector
            task="generate_reel_script"
            value={selectedModel}
            onChange={setSelectedModel}
          />
          <PrimaryButton
            onClick={handleGenerate}
            disabled={generating || !canGenerate}
            icon={generating ? "hourglass_top" : "movie_edit"}
            className="flex-1"
          >
            {generating ? (job?.status === "running" ? "Generating..." : "Queued...") : "Generate Reel Script"}
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
          const isDirty = activeScript && editedText !== activeScript.generated_text
          return (
            <GlassPanel className="rounded-xl overflow-hidden min-h-[400px] relative">
              <div className="flex items-center justify-between px-6 py-4 border-b border-black/5 bg-gradient-to-r from-violet-50/50 to-pink-50/50">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full shadow-[0_0_8px_rgba(129,39,207,0.4)] ${activeScript ? "bg-secondary animate-pulse" : "bg-outline-variant"}`} />
                  <span className="font-label-caps text-label-caps text-on-surface">
                    REEL SCRIPT{isDirty ? " *" : ""}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {activeScript && (
                    <>
                      <motion.button
                        onClick={handleOpenScripts}
                        whileTap={{ scale: 0.95 }}
                        title="Open scripts folder"
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
                        onClick={(e) => handleDeleteScript(e, activeScript.script_id)}
                        whileTap={{ scale: 0.95 }}
                        disabled={deletingId === activeScript.script_id}
                        className="flex items-center gap-1.5 text-outline-variant hover:text-error hover:bg-error/5 px-3 py-1.5 rounded-lg transition-colors font-label-caps text-label-caps border border-black/5 hover:border-error/20 disabled:opacity-30"
                      >
                        <Icon name="delete" size={15} />
                      </motion.button>
                    </>
                  )}
                  <motion.button
                    onClick={handleCopy}
                    whileTap={{ scale: 0.95 }}
                    disabled={!activeScript}
                    className="flex items-center gap-2 text-secondary hover:bg-secondary/5 px-3 py-1.5 rounded-lg transition-colors font-label-caps text-label-caps border border-secondary/20 backdrop-blur-sm disabled:opacity-30"
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
                      <div className="w-6 h-6 border-2 border-secondary border-t-transparent rounded-full animate-spin" />
                      <span className="font-label-caps text-label-caps text-on-surface-variant">Generating your reel script...</span>
                    </motion.div>
                  ) : activeScript ? (
                    <motion.div key="script" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
                      {activeScript.framework_id && (
                        <p className="font-label-caps text-[10px] text-on-surface-variant italic mb-3">
                          Framework: {activeScript.framework_id}
                          {activeScript.framework_pick_reason ? ` — ${activeScript.framework_pick_reason}` : ""}
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
                      <Icon name="movie_edit" size={32} className="text-outline-variant" />
                      <span className="font-body text-body text-on-surface-variant">Write an idea and click Generate Reel Script</span>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {activeScript && (
                <div className="absolute bottom-4 right-6 flex items-center gap-2 flex-wrap justify-end">
                  <span className="px-3 py-1 glass-panel text-[10px] font-label-caps text-secondary uppercase border-secondary/10">
                    Script #{activeScript.script_id}
                  </span>
                  <span className="px-3 py-1 glass-panel text-[10px] font-label-caps text-on-surface-variant uppercase">
                    {activeScript.model_used}
                  </span>
                  {activeScript.latency_ms != null && (
                    <span className="px-3 py-1 glass-panel text-[10px] font-label-caps text-on-surface-variant border-black/5">
                      {activeScript.latency_ms}ms · {activeScript.tokens?.total ?? 0}t · ${(activeScript.cost_usd ?? 0).toFixed(6)}
                    </span>
                  )}
                </div>
              )}
            </GlassPanel>
          )
        })()}
      </section>

      {/* --- MP4 Ingest panel --- */}
      <section className="relative z-10">
        <GlassPanel className="rounded-xl p-card_padding">
          <div className="flex items-center gap-2 mb-4">
            <Icon name="video_library" size={18} className="text-on-surface-variant" />
            <h3 className="font-label-caps text-label-caps text-on-surface-variant">MP4 INGEST</h3>
          </div>

          <div className="flex gap-3 flex-wrap mb-4">
            <motion.button
              onClick={handleOpenReferences}
              whileTap={{ scale: 0.98 }}
              className="flex items-center gap-2 glass-panel text-on-surface-variant hover:text-primary px-4 py-2.5 rounded-xl font-label-caps text-label-caps transition-colors border-black/5"
            >
              <Icon name="folder_open" size={16} />
              Open folder
            </motion.button>
            <motion.button
              onClick={handleScan}
              disabled={scanning}
              whileTap={{ scale: 0.98 }}
              className="flex items-center gap-2 glass-panel text-on-surface-variant hover:text-secondary px-4 py-2.5 rounded-xl font-label-caps text-label-caps transition-colors border-black/5 disabled:opacity-40"
            >
              <Icon name={scanning ? "sync" : "radar"} size={16} className={scanning ? "animate-spin" : ""} />
              {scanning ? "Scanning..." : "Scan folder"}
            </motion.button>
          </div>

          <p className="font-label-caps text-[10px] text-on-surface-variant leading-relaxed mb-4">
            Drop .mp4 files into the references folder, then scan to extract frameworks. Successful extractions
            delete the source file. Each file runs as a background job — you can leave this page while it works
            through the queue.
          </p>

          <AnimatePresence>
            {scanJobs && scanJobs.length > 0 && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="p-4 bg-surface-container-low rounded-lg"
              >
                <div className="flex items-center gap-4 font-label-caps text-label-caps mb-2">
                  <span className="text-on-surface-variant">Queued: <span className="text-on-surface">{scanJobs.length}</span></span>
                  <span className="text-on-surface-variant">Settled: <span className="text-on-surface">{settledCount}</span></span>
                </div>
                <ul className="space-y-1">
                  {scanJobs.map(({ file, job_id }) => (
                    <ScanJobRow key={job_id} file={file} jobId={job_id} onSettled={handleScanSettled} />
                  ))}
                </ul>
              </motion.div>
            )}
            {scanJobs && scanJobs.length === 0 && (
              <p className="font-label-caps text-label-caps text-on-surface-variant">No .mp4 files found in the references folder.</p>
            )}
          </AnimatePresence>
        </GlassPanel>
      </section>

      {/* --- Recent scripts --- */}
      {scripts.length > 0 && (
        <section className="relative z-10 flex flex-col gap-3">
          <h3 className="font-label-caps text-label-caps text-on-surface-variant px-2">RECENT SCRIPTS</h3>
          <div className="flex flex-col gap-3">
            {scripts.slice(0, 10).map((s, i) => (
              <motion.div key={s.id} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
                <GlassPanel
                  as="div"
                  onClick={() => handleSelectScript(s.id)}
                  className={`group relative w-full text-left hover:border-secondary/30 hover:bg-white p-card_padding rounded-xl flex items-center justify-between transition-all cursor-pointer ${activeScript?.script_id === s.id ? "border-secondary/30 bg-white" : ""}`}
                >
                  <div className="flex items-center gap-4">
                    <div className="bg-secondary/5 border border-secondary/10 p-2 rounded-lg">
                      <Icon name="movie_edit" size={20} className="text-secondary" />
                    </div>
                    <div>
                      <p className="font-body text-body text-on-surface">Script #{s.id}</p>
                      <p className="font-label-caps text-[10px] text-on-surface-variant mt-0.5">
                        {s.created_at?.slice(0, 16)} · {s.model_used?.toUpperCase()}
                      </p>
                    </div>
                  </div>
                  <Icon name="chevron_right" size={20} className="text-on-surface-variant group-hover:opacity-0 transition-opacity" />
                  <button
                    onClick={(e) => handleDeleteScript(e, s.id)}
                    disabled={deletingId === s.id}
                    className="absolute right-3 top-1/2 -translate-y-1/2 z-20 opacity-0 group-hover:opacity-100 transition-opacity p-2 rounded-lg text-outline-variant hover:text-error hover:bg-error/10 disabled:opacity-30"
                    title="Delete script"
                  >
                    <Icon name={deletingId === s.id ? "sync" : "delete"} size={16} className={deletingId === s.id ? "animate-spin" : ""} />
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
