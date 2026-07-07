import { useState, useEffect, useRef } from "react"
import { motion } from "framer-motion"
import { fetchPages, triggerSync, fetchSyncStatus } from "../api.js"
import GlassPanel from "./ui/GlassPanel.jsx"
import Icon from "./ui/Icon.jsx"

export default function PageList({ onSelect }) {
  const [pages, setPages] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [syncing, setSyncing] = useState(false)
  const [syncMsg, setSyncMsg] = useState(null)
  const pollRef = useRef(null)

  useEffect(() => {
    fetchPages()
      .then(data => { setPages(data); setLoading(false) })
      .catch(err => { setError(err.message); setLoading(false) })
  }, [])

  function clearMsg() {
    setTimeout(() => setSyncMsg(null), 5000)
  }

  async function onSyncClick() {
    if (syncing) return
    setSyncing(true)
    setSyncMsg(null)
    try {
      const res = await triggerSync()
      if (res.status === "busy") {
        setSyncMsg("Sync already running…")
        clearMsg()
        setSyncing(false)
        return
      }
    } catch (e) {
      setSyncMsg(`Sync failed: ${e.message}`)
      clearMsg()
      setSyncing(false)
      return
    }

    pollRef.current = setInterval(async () => {
      try {
        const s = await fetchSyncStatus()
        if (s.status === "ok") {
          clearInterval(pollRef.current)
          const fresh = await fetchPages()
          setPages(fresh)
          setSyncMsg(`+${s.added} new`)
          clearMsg()
          setSyncing(false)
        } else if (s.status === "error") {
          clearInterval(pollRef.current)
          setSyncMsg(`Sync failed: ${s.error}`)
          clearMsg()
          setSyncing(false)
        }
      } catch {
        clearInterval(pollRef.current)
        setSyncing(false)
      }
    }, 2000)
  }

  useEffect(() => () => clearInterval(pollRef.current), [])

  if (loading) return (
    <div className="flex flex-col gap-3">
      <div className="font-label-caps text-label-caps text-on-surface-variant mb-2">DIARY</div>
      {[...Array(4)].map((_, i) => (
        <GlassPanel key={i} className="rounded-xl p-card_padding animate-pulse">
          <div className="h-4 bg-surface-container rounded w-3/4 mb-2" />
          <div className="h-3 bg-surface-container rounded w-1/4" />
        </GlassPanel>
      ))}
    </div>
  )

  if (error) return (
    <GlassPanel className="rounded-xl p-card_padding border-error/20">
      <div className="flex items-center gap-2 text-error font-label-caps text-label-caps">
        <Icon name="error" size={16} />
        {error}
      </div>
    </GlassPanel>
  )

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between mb-2">
        <span className="font-label-caps text-label-caps text-on-surface-variant">DIARY</span>
        <div className="flex items-center gap-3">
          {syncMsg && (
            <span className="font-label-caps text-label-caps text-primary">{syncMsg}</span>
          )}
          <button
            onClick={onSyncClick}
            disabled={syncing}
            className="flex items-center gap-1 font-label-caps text-label-caps text-on-surface-variant hover:text-primary disabled:opacity-40 transition-colors"
          >
            <Icon name="refresh" size={14} className={syncing ? "animate-spin" : ""} />
            Sync
          </button>
          <span className="font-label-caps text-label-caps text-outline">{pages.length} entries</span>
        </div>
      </div>

      <div className="flex flex-col gap-3">
        {pages.map((page, i) => (
          <motion.div
            key={page.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04, duration: 0.25 }}
          >
            <GlassPanel
              as="button"
              onClick={() => onSelect(page.id)}
              className="group w-full text-left hover:border-primary/30 hover:bg-white p-card_padding rounded-xl flex items-center justify-between transition-all cursor-pointer"
            >
              <div className="flex items-center gap-4">
                <div className="bg-primary/5 border border-primary/10 p-2 rounded-lg flex-shrink-0">
                  <Icon name="description" size={20} className="text-primary" />
                </div>
                <div>
                  <p className="font-body text-body text-on-surface">{page.title || "Untitled"}</p>
                  <p className="font-label-caps text-[10px] text-on-surface-variant mt-0.5">
                    {new Date(page.created_time).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }).toUpperCase()}
                  </p>
                </div>
              </div>
              <Icon
                name="chevron_right"
                size={20}
                className="text-on-surface-variant group-hover:text-primary transition-colors flex-shrink-0"
              />
            </GlassPanel>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
