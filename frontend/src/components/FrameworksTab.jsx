import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { fetchFrameworksList, fetchFramework, putFramework, deleteFramework } from "../frameworksApi.js"
import GlassPanel from "./ui/GlassPanel.jsx"
import PrimaryButton from "./ui/PrimaryButton.jsx"
import Icon from "./ui/Icon.jsx"

export default function FrameworksTab() {
  const [linkedin, setLinkedin] = useState([])
  const [reels, setReels] = useState([])
  const [activeUid, setActiveUid] = useState(null)
  const [detail, setDetail] = useState(null)
  const [yamlText, setYamlText] = useState("")
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [editTitle, setEditTitle] = useState("")
  const [editDescription, setEditDescription] = useState("")
  const [savingInfo, setSavingInfo] = useState(false)
  const [saving, setSaving] = useState(false)
  const [deletingUid, setDeletingUid] = useState(null)
  const [parseError, setParseError] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchFrameworksList()
      .then(data => { setLinkedin(data.linkedin || []); setReels(data.reels || []) })
      .catch(e => setError(e.message))
  }, [])

  // Replace a top-level scalar YAML field in place (no re-serialisation)
  const updateYamlField = (text, key, value) => {
    const escaped = String(value).replace(/\\/g, "\\\\").replace(/"/g, '\\"')
    const re = new RegExp(`^(${key}:\\s*).*$`, "m")
    const line = `${key}: "${escaped}"`
    return re.test(text) ? text.replace(re, line) : `${text}\n${line}`
  }

  const handleSelect = async (channel, id, uid) => {
    if (activeUid === uid) return
    setActiveUid(uid)
    setDetail(null)
    setYamlText("")
    setParseError(null)
    setLoadingDetail(true)
    try {
      const d = await fetchFramework(channel, id)
      setDetail(d)
      setYamlText(d.yaml_text || "")
      setEditTitle(d.source_file || "")
      setEditDescription(d.description || "")
    } catch (e) {
      setError(e.message)
    } finally {
      setLoadingDetail(false)
    }
  }

  const isInfoDirty = detail && (
    editTitle !== (detail.source_file || "") ||
    editDescription !== (detail.description || "")
  )

  const handleSaveInfo = async () => {
    if (!detail || savingInfo) return
    setSavingInfo(true)
    setParseError(null)
    try {
      let updated_yaml = yamlText
      updated_yaml = updateYamlField(updated_yaml, "source_file", editTitle)
      updated_yaml = updateYamlField(updated_yaml, "description", editDescription)
      const updated = await putFramework(detail.channel, detail.id, updated_yaml)
      setDetail(updated)
      setYamlText(updated.yaml_text || "")
      setEditTitle(updated.source_file || "")
      setEditDescription(updated.description || "")
      const patch = { description: updated.description, hook_type: updated.hook_type }
      if (detail.channel === "linkedin") setLinkedin(prev => prev.map(f => f.id === detail.id ? { ...f, ...patch } : f))
      else setReels(prev => prev.map(f => f.id === detail.id ? { ...f, ...patch } : f))
    } catch (e) {
      setParseError(e.message)
    } finally {
      setSavingInfo(false)
    }
  }

  const isDirty = detail && yamlText !== (detail.yaml_text || "")

  const handleSave = async () => {
    if (!detail || saving) return
    setSaving(true)
    setParseError(null)
    try {
      const updated = await putFramework(detail.channel, detail.id, yamlText)
      setDetail(updated)
      setYamlText(updated.yaml_text || "")
      // refresh the list item description
      if (detail.channel === "linkedin") {
        setLinkedin(prev => prev.map(f => f.id === detail.id ? { ...f, description: updated.description, hook_type: updated.hook_type } : f))
      } else {
        setReels(prev => prev.map(f => f.id === detail.id ? { ...f, description: updated.description, hook_type: updated.hook_type } : f))
      }
    } catch (e) {
      setParseError(e.message)
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    if (!detail) return
    setYamlText(detail.yaml_text || "")
    setParseError(null)
  }

  const handleDelete = async () => {
    if (!detail) return
    if (!window.confirm(`Delete framework "${detail.id}"? This removes the YAML file and DB row.`)) return
    setDeletingUid(detail.uid)
    try {
      await deleteFramework(detail.channel, detail.id)
      if (detail.channel === "linkedin") setLinkedin(prev => prev.filter(f => f.id !== detail.id))
      else setReels(prev => prev.filter(f => f.id !== detail.id))
      setDetail(null)
      setYamlText("")
      setActiveUid(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setDeletingUid(null)
    }
  }

  const renderList = (items, channel, color) => (
    <div className="flex flex-col gap-1">
      {items.map(f => {
        const uid = `${channel}-${f.id}`
        const isActive = activeUid === uid
        return (
          <button
            key={uid}
            onClick={() => handleSelect(channel, f.id, uid)}
            className={`group relative w-full text-left px-3 py-2.5 rounded-lg transition-all font-body text-body ${
              isActive
                ? "bg-primary/8 border border-primary/15 text-on-surface"
                : "hover:bg-white/60 text-on-surface-variant hover:text-on-surface"
            }`}
          >
            <p className="text-[13px] font-medium truncate">{f.source_file || f.id}</p>
            <p className="font-label-caps text-[10px] text-on-surface-variant mt-0.5 truncate">
              {[f.hook_type, f.tone].filter(Boolean).map(s => s.replace(/_/g, " ")).join(" · ")}
            </p>
          </button>
        )
      })}
    </div>
  )

  return (
    <div className="flex gap-6 h-[calc(100vh-160px)]">
      {/* --- Left: master list --- */}
      <div className="w-64 flex-shrink-0 flex flex-col gap-4 overflow-y-auto pr-1">
        {error && (
          <div className="flex items-center gap-2 text-error font-label-caps text-[10px] px-1">
            <Icon name="error" size={12} /> {error}
          </div>
        )}

        {linkedin.length > 0 && (
          <div>
            <div className="flex items-center gap-2 px-1 mb-2">
              <span className="font-label-caps text-[10px] text-on-surface-variant">LINKEDIN</span>
              <span className="text-[10px] text-outline-variant">{linkedin.length}</span>
            </div>
            {renderList(linkedin, "linkedin", "primary")}
          </div>
        )}

        {reels.length > 0 && (
          <div>
            <div className="flex items-center gap-2 px-1 mb-2">
              <span className="font-label-caps text-[10px] text-on-surface-variant">REELS</span>
              <span className="text-[10px] text-outline-variant">{reels.length}</span>
            </div>
            {renderList(reels, "reels", "secondary")}
          </div>
        )}

        {linkedin.length === 0 && reels.length === 0 && (
          <p className="font-label-caps text-[10px] text-on-surface-variant px-1">No frameworks loaded</p>
        )}
      </div>

      {/* --- Right: detail --- */}
      <div className="flex-1 min-w-0">
        <AnimatePresence mode="wait">
          {!activeUid ? (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center justify-center h-full gap-3 text-center"
            >
              <Icon name="schema" size={36} className="text-outline-variant" />
              <span className="font-body text-body text-on-surface-variant">Select a framework to view and edit</span>
            </motion.div>
          ) : loadingDetail ? (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex items-center justify-center h-full gap-3"
            >
              <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              <span className="font-label-caps text-label-caps text-on-surface-variant">Loading...</span>
            </motion.div>
          ) : detail ? (
            <motion.div
              key={detail.uid}
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="flex flex-col gap-4 h-full"
            >
              {/* Header */}
              <GlassPanel className="rounded-xl p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0 flex flex-col gap-3">
                    {/* Read-only badges */}
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-label-caps uppercase ${detail.channel === "linkedin" ? "bg-primary/10 text-primary" : "bg-secondary/10 text-secondary"}`}>
                        {detail.channel}
                      </span>
                      {detail.hook_type && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-label-caps bg-surface-container-low text-on-surface-variant">
                          {detail.hook_type.replace(/_/g, " ")}
                        </span>
                      )}
                      {detail.tone && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-label-caps bg-surface-container-low text-on-surface-variant">
                          {detail.tone}
                        </span>
                      )}
                      <span className="font-label-caps text-[10px] text-outline-variant">{detail.id}</span>
                    </div>

                    {/* Editable title (source_file) */}
                    <div className="flex flex-col gap-1">
                      <label className="font-label-caps text-[10px] text-on-surface-variant">TITLE</label>
                      <input
                        type="text"
                        value={editTitle}
                        onChange={e => setEditTitle(e.target.value)}
                        placeholder="e.g. Bold claim — career pivot"
                        className="w-full bg-white/40 border border-black/5 rounded-lg px-3 py-2 font-body text-body text-on-surface focus:ring-1 focus:ring-primary focus:border-primary outline-none transition-all placeholder:text-outline-variant"
                      />
                    </div>

                    {/* Editable description */}
                    <div className="flex flex-col gap-1">
                      <label className="font-label-caps text-[10px] text-on-surface-variant">DESCRIPTION</label>
                      <textarea
                        value={editDescription}
                        onChange={e => setEditDescription(e.target.value)}
                        rows={3}
                        placeholder="Describe when and how to use this framework..."
                        className="w-full bg-white/40 border border-black/5 rounded-lg px-3 py-2 font-body text-body text-on-surface focus:ring-1 focus:ring-primary focus:border-primary outline-none resize-none transition-all placeholder:text-outline-variant"
                      />
                    </div>

                    {/* Save info button */}
                    {isInfoDirty && (
                      <motion.button
                        onClick={handleSaveInfo}
                        disabled={savingInfo}
                        whileTap={{ scale: 0.98 }}
                        className="self-start flex items-center gap-1.5 text-primary hover:bg-primary/5 px-3 py-1.5 rounded-lg transition-colors font-label-caps text-label-caps border border-primary/20 disabled:opacity-40"
                      >
                        <Icon name={savingInfo ? "sync" : "save"} size={14} className={savingInfo ? "animate-spin" : ""} />
                        {savingInfo ? "Saving..." : "Save info"}
                      </motion.button>
                    )}
                  </div>

                  <button
                    onClick={handleDelete}
                    disabled={deletingUid === detail.uid}
                    className="flex-shrink-0 p-2 rounded-lg text-outline-variant hover:text-error hover:bg-error/10 transition-colors disabled:opacity-30"
                    title="Delete framework"
                  >
                    <Icon name={deletingUid === detail.uid ? "sync" : "delete"} size={16} className={deletingUid === detail.uid ? "animate-spin" : ""} />
                  </button>
                </div>
              </GlassPanel>

              {/* YAML editor */}
              <GlassPanel className="rounded-xl flex flex-col flex-1 overflow-hidden">
                <div className="flex items-center justify-between px-5 py-3 border-b border-black/5">
                  <span className="font-label-caps text-label-caps text-on-surface-variant">
                    YAML{isDirty ? " *" : ""}
                  </span>
                  <div className="flex items-center gap-2">
                    {isDirty && (
                      <button
                        onClick={handleReset}
                        className="px-3 py-1.5 rounded-lg font-label-caps text-label-caps text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low transition-colors border border-black/5"
                      >
                        Reset
                      </button>
                    )}
                    <PrimaryButton
                      onClick={handleSave}
                      disabled={!isDirty || saving}
                      icon={saving ? "sync" : "save"}
                      className="!py-1.5 !px-4 text-label-caps"
                    >
                      {saving ? "Saving..." : "Save"}
                    </PrimaryButton>
                  </div>
                </div>

                {parseError && (
                  <div className="mx-5 mt-3 px-3 py-2 bg-error/8 border border-error/20 rounded-lg font-label-caps text-[10px] text-error">
                    {parseError}
                  </div>
                )}

                <textarea
                  value={yamlText}
                  onChange={e => { setYamlText(e.target.value); setParseError(null) }}
                  spellCheck={false}
                  className="flex-1 w-full p-5 bg-transparent font-mono-script text-mono-script text-on-surface leading-relaxed resize-none outline-none border-none min-h-[300px]"
                />
              </GlassPanel>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>
    </div>
  )
}
