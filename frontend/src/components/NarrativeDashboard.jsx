import { useState, useEffect } from "react"
import { triggerExtract, triggerSynthesize, fetchWeeklyIndex, fetchThreads } from "../narrativeApi"

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
  const [totalNodes, setTotalNodes] = useState(null)

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
      // refresh weeks
      const data = await fetchWeeklyIndex(50)
      setWeeks(data.items || [])
    } catch (e) {
      setSyncError(e.message)
    } finally {
      setSynthesizing(false)
    }
  }

  const openThreads = threads.filter(t => t.current_status !== "Closed").length

  return (
    <div style={{ padding: "0 0 40px" }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginBottom: 24 }}>
        <StatCard label="Story Nodes" value={totalNodes ?? "—"} />
        <StatCard label="Active Threads" value={openThreads} />
        <StatCard label="Weeks Synthesized" value={weeks.length} />
      </div>

      <div style={{ background: "#f8f9fa", borderRadius: 8, padding: 20, marginBottom: 24 }}>
        <h3 style={{ marginTop: 0, marginBottom: 12, fontSize: 15, fontWeight: 700 }}>Sync All</h3>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <button
            onClick={handleSyncAll}
            disabled={syncing}
            style={{
              background: syncing ? "#ccc" : "#1565c0",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              padding: "10px 24px",
              fontSize: 14,
              fontWeight: 600,
              cursor: syncing ? "not-allowed" : "pointer",
            }}>
            {syncing ? "Syncing..." : "Sync All"}
          </button>
          {lastSync && <span style={{ fontSize: 12, color: "#666" }}>Last sync: {lastSync}</span>}
        </div>

        {syncError && <div style={{ color: "red", marginTop: 10, fontSize: 13 }}>{syncError}</div>}

        {syncResult && (
          <div style={{ marginTop: 12, fontSize: 13 }}>
            <div style={{ color: "#2e7d32", fontWeight: 600 }}>Extract complete!</div>
            <div>{syncResult.extract.pages_processed} pages, {syncResult.extract.story_nodes_created} nodes, {syncResult.extract.low_potential_count} low-potential</div>
            <div style={{ marginTop: 4, color: "#2e7d32", fontWeight: 600 }}>Synthesize complete!</div>
            <div>Week: {syncResult.synthesize.week_index_id} — {syncResult.synthesize.thread_count} threads, {syncResult.synthesize.open_loops} open, sentiment {syncResult.synthesize.sentiment_delta?.toFixed(3)}</div>
          </div>
        )}
      </div>

      <div style={{ background: "#f8f9fa", borderRadius: 8, padding: 20 }}>
        <h3 style={{ marginTop: 0, marginBottom: 12, fontSize: 15, fontWeight: 700 }}>Synthesize Specific Week</h3>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <select
            value={selectedWeek || ""}
            onChange={e => setSelectedWeek(e.target.value || null)}
            style={{ padding: "8px 12px", border: "1px solid #ccc", borderRadius: 4, fontSize: 13, minWidth: 260 }}>
            <option value="">— Select a week —</option>
            {weeks.map(w => (
              <option key={w.id} value={w.week_start}>
                {w.week_start} → {w.week_end} ({w.total_entries} entries, {w.thread_count} threads)
              </option>
            ))}
          </select>
          <button
            onClick={handleSynthesize}
            disabled={!selectedWeek || synthesizing}
            style={{
              background: !selectedWeek || synthesizing ? "#ccc" : "#2e7d32",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              padding: "8px 20px",
              fontSize: 13,
              fontWeight: 600,
              cursor: !selectedWeek || synthesizing ? "not-allowed" : "pointer",
            }}>
            {synthesizing ? "Running..." : "Synthesize"}
          </button>
        </div>
        {synthResult && (
          <div style={{ marginTop: 10, fontSize: 13, color: "#2e7d32" }}>
            Done: {synthResult.thread_count} threads, {synthResult.open_loops} open, {synthResult.closed_loops} closed, delta={synthResult.sentiment_delta?.toFixed(3)}
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value }) {
  return (
    <div style={{ background: "#fff", border: "1px solid #e0e0e0", borderRadius: 8, padding: "16px 20px" }}>
      <div style={{ fontSize: 28, fontWeight: 800, color: "#1565c0" }}>{value}</div>
      <div style={{ fontSize: 12, color: "#888", fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5, marginTop: 4 }}>{label}</div>
    </div>
  )
}