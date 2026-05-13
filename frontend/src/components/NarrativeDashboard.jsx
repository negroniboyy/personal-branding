import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { triggerExtract, triggerSynthesize, fetchWeeklyIndex, fetchThreads } from "../narrativeApi"
import GlassPanel from "./ui/GlassPanel.jsx"
import PrimaryButton from "./ui/PrimaryButton.jsx"
import Icon from "./ui/Icon.jsx"

const LAST_SYNC_KEY = "narrative_last_sync"

export default function NarrativeDashboard() {
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState(null)
  const [syncError, setSyncError] = useState(null)
  const [lastSync, setLastSync] = useState(() => localStorage.getItem(LAST_SYNC_KEY) || null)
  const [weeks, setWeeks] = useState([])
  const [selectedWeek, setSelectedWeek] = useState(null)
  const [synthesizing, setSynthesizing] = useState(false)
  const [synthResult, setSynthResult] = useState(null)
  const [threads, setThreads] = useState([])

  useEffect(() => {
    fetchWeeklyIndex(50).then(data => setWeeks(data.items || [])).catch(() => {})
    fetchThreads(null, 50).then(data => setThreads(data.items || [])).catch(() => {})
  }, [])

  const handleSyncAll = async () => {
    setSyncing(true)
    setSyncError(null)
    setSyncResult(null)
    try {
      const extractResult = await triggerExtract()
      const synthResult = await triggerSynthesize()
      const now = new Date().toLocaleString()
      localStorage.setItem(LAST_SYNC_KEY, now)
      setLastSync(now)
      setSyncResult({ extract: extractResult, synthesize: synthResult })
    } catch (e) {
      setSyncError(e.message)
    } finally {
      setSyncing(false)
    }
  }

  const handleSynthesize = async () => {
    if (!selectedWeek) return
    setSynthesizing(true)
    setSynthResult(null)
    try {
      const result = await triggerSynthesize(selectedWeek)
      setSynthResult(result)
      const data = await fetchWeeklyIndex(50)
      setWeeks(data.items || [])
    } catch (e) {
      setSyncError(e.message)
    } finally {
      setSynthesizing(false)
    }
  }

  const openThreads = threads.filter(t => t.current_status !== "Closed").length

  const stats = [
    { label: "Active Threads", value: openThreads, icon: "swap_horiz" },
    { label: "Weeks Synthesized", value: weeks.length, icon: "calendar_month" },
  ]

  return (
    <div className="flex flex-col gap-6 pb-10">
      <div className="flex items-center justify-between">
        <span className="font-label-caps text-label-caps text-on-surface-variant">NARRATIVE WAREHOUSE</span>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-4">
        {stats.map((s, i) => (
          <motion.div key={s.label} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}>
            <GlassPanel className="rounded-xl p-card_padding">
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-h1 text-h1 text-primary leading-none">{s.value}</div>
                  <div className="font-label-caps text-label-caps text-on-surface-variant mt-2">{s.label.toUpperCase()}</div>
                </div>
                <div className="bg-primary/5 border border-primary/10 p-2 rounded-lg">
                  <Icon name={s.icon} size={20} className="text-primary" />
                </div>
              </div>
            </GlassPanel>
          </motion.div>
        ))}
      </div>

      {/* Sync All */}
      <GlassPanel className="rounded-xl p-card_padding">
        <h3 className="font-label-caps text-label-caps text-on-surface-variant mb-4">SYNC ALL</h3>
        <div className="flex items-center gap-4 flex-wrap">
          <PrimaryButton onClick={handleSyncAll} disabled={syncing} icon={syncing ? "sync" : "cloud_sync"}>
            {syncing ? "Syncing..." : "Sync All"}
          </PrimaryButton>
          {lastSync && (
            <span className="font-label-caps text-label-caps text-outline">Last sync: {lastSync}</span>
          )}
        </div>

        {syncError && (
          <div className="mt-3 flex items-center gap-2 text-error font-label-caps text-label-caps">
            <Icon name="error" size={14} /> {syncError}
          </div>
        )}

        {syncResult && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            className="mt-4 p-4 bg-surface-container-low rounded-lg"
          >
            <div className="flex items-center gap-2 text-primary font-label-caps text-label-caps mb-1">
              <Icon name="check_circle" size={14} fill /> Extract complete
            </div>
            <div className="font-mono-script text-mono-script text-on-surface-variant mb-3">
              {syncResult.extract.pages_processed} pages · {syncResult.extract.story_nodes_created} nodes · {syncResult.extract.low_potential_count} low-potential
            </div>
            <div className="flex items-center gap-2 text-secondary font-label-caps text-label-caps mb-1">
              <Icon name="check_circle" size={14} fill /> Synthesize complete
            </div>
            <div className="font-mono-script text-mono-script text-on-surface-variant">
              Week {syncResult.synthesize.week_index_id} · {syncResult.synthesize.thread_count} threads · {syncResult.synthesize.open_loops} open · δ {syncResult.synthesize.sentiment_delta?.toFixed(3)}
            </div>
          </motion.div>
        )}
      </GlassPanel>

      {/* Synthesize specific week */}
      <GlassPanel className="rounded-xl p-card_padding">
        <h3 className="font-label-caps text-label-caps text-on-surface-variant mb-4">SYNTHESIZE SPECIFIC WEEK</h3>
        <div className="flex gap-3 flex-wrap items-center">
          <select
            value={selectedWeek || ""}
            onChange={e => setSelectedWeek(e.target.value || null)}
            className="glass-panel rounded-lg px-4 py-3 font-body text-body text-on-surface appearance-none focus:border-primary outline-none border-black/5 min-w-[260px]"
          >
            <option value="">— Select a week —</option>
            {weeks.map(w => (
              <option key={w.id} value={w.week_start}>
                {w.week_start} → {w.week_end} ({w.total_entries} entries, {w.thread_count} threads)
              </option>
            ))}
          </select>
          <motion.button
            onClick={handleSynthesize}
            disabled={!selectedWeek || synthesizing}
            whileTap={{ scale: 0.98 }}
            className="px-5 py-3 rounded-xl font-label-caps text-label-caps bg-secondary text-on-secondary hover:bg-secondary/90 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {synthesizing ? "Running..." : "Synthesize"}
          </motion.button>
        </div>

        {synthResult && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-3 font-mono-script text-mono-script text-secondary"
          >
            Done: {synthResult.thread_count} threads · {synthResult.open_loops} open · {synthResult.closed_loops} closed · δ={synthResult.sentiment_delta?.toFixed(3)}
          </motion.div>
        )}
      </GlassPanel>
    </div>
  )
}
