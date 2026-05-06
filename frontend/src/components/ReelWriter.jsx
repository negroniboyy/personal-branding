import { useState, useEffect, useCallback } from "react"
import {
  postReelRecommendations,
  postReelGenerate,
  fetchReelScripts,
  fetchReelScript,
  postReelScan,
  postReelOpenReferences,
} from "../reelApi.js"

export default function ReelWriter() {
  const [stories, setStories] = useState([])
  const [frameworks, setFrameworks] = useState([])
  const [selectedStoryId, setSelectedStoryId] = useState(null)
  const [selectedFrameworkId, setSelectedFrameworkId] = useState(null)
  const [ideaPrompt, setIdeaPrompt] = useState("")
  const [manualOverride, setManualOverride] = useState(false)
  const [scripts, setScripts] = useState([])
  const [activeScript, setActiveScript] = useState(null)
  const [generating, setGenerating] = useState(false)
  const [loadingRecs, setLoadingRecs] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [scanResult, setScanResult] = useState(null)
  const [error, setError] = useState(null)

  const loadRecommendations = useCallback(async (idea) => {
    setLoadingRecs(true)
    setError(null)
    try {
      const data = await postReelRecommendations({ idea_prompt: idea || null, top_n: 5 })
      setStories(data.stories || [])
      setFrameworks(data.frameworks || [])
      if (!manualOverride) {
        if (data.stories.length > 0) setSelectedStoryId(data.stories[0].id)
        if (data.frameworks.length > 0) setSelectedFrameworkId(data.frameworks[0].id)
      }
      setManualOverride(false)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoadingRecs(false)
    }
  }, [manualOverride])

  const loadScripts = async () => {
    try {
      const data = await fetchReelScripts()
      setScripts(data)
    } catch { /* non-blocking */ }
  }

  useEffect(() => {
    loadRecommendations("")
    loadScripts()
  }, [])

  const handleGenerate = async () => {
    if (!selectedStoryId || !selectedFrameworkId) return
    setGenerating(true)
    setError(null)
    setActiveScript(null)
    try {
      const result = await postReelGenerate({
        story_node_id: selectedStoryId,
        framework_id: selectedFrameworkId,
        idea_prompt: ideaPrompt || null,
      })
      setActiveScript(result)
      await loadScripts()
    } catch (e) {
      setError(e.message)
    } finally {
      setGenerating(false)
    }
  }

  const handleSelectScript = async (id) => {
    try {
      const s = await fetchReelScript(id)
      setActiveScript({
        script_id: s.id,
        generated_text: s.generated_text,
        story_node_id: s.story_node_id,
        framework_id: s.framework_id,
        model_used: s.model_used,
        created_at: s.created_at,
      })
    } catch (e) {
      setError(e.message)
    }
  }

  const handleOpenReferences = async () => {
    setError(null)
    try {
      await postReelOpenReferences()
    } catch (e) {
      setError(e.message)
    }
  }

  const handleScan = async () => {
    setScanning(true)
    setError(null)
    setScanResult(null)
    try {
      const r = await postReelScan()
      setScanResult(r)
      if (r.succeeded.length > 0) await loadRecommendations(ideaPrompt)
    } catch (e) {
      setError(e.message)
    } finally {
      setScanning(false)
    }
  }

  const selectedStory = stories.find(s => s.id === selectedStoryId)
  const selectedFramework = frameworks.find(f => f.id === selectedFrameworkId)

  return (
    <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: 24 }}>

      {/* LEFT PANEL */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

        {/* Idea prompt */}
        <div>
          <label style={labelStyle}>Idea / framing hint (optional)</label>
          <textarea
            value={ideaPrompt}
            onChange={e => setIdeaPrompt(e.target.value)}
            placeholder="e.g. the moment you stopped chasing approval"
            rows={3}
            style={{ ...inputStyle, resize: "vertical" }}
          />
          <button
            onClick={() => loadRecommendations(ideaPrompt)}
            disabled={loadingRecs}
            style={secondaryBtnStyle}
          >
            {loadingRecs ? "Loading…" : "Get Recommendations"}
          </button>
        </div>

        {/* Story picker */}
        <div>
          <label style={labelStyle}>Story</label>
          <select
            value={selectedStoryId ?? ""}
            onChange={e => { setSelectedStoryId(e.target.value); setManualOverride(true) }}
            style={inputStyle}
          >
            {stories.length === 0 && <option value="">No stories loaded</option>}
            {stories.map(s => (
              <option key={s.id} value={s.id}>
                [{s.worth_score?.toFixed(1)}] #{s.id} {(s.user_state || s.conflict_node || "").slice(0, 40)}
              </option>
            ))}
          </select>
          {selectedStory && (
            <p style={metaStyle}>{selectedStory.conflict_node}</p>
          )}
        </div>

        {/* Framework picker */}
        <div>
          <label style={labelStyle}>Framework</label>
          <select
            value={selectedFrameworkId ?? ""}
            onChange={e => { setSelectedFrameworkId(e.target.value); setManualOverride(true) }}
            style={inputStyle}
          >
            {frameworks.length === 0 && <option value="">No frameworks loaded</option>}
            {frameworks.map(f => (
              <option key={f.id} value={f.id}>{f.id}</option>
            ))}
          </select>
          {selectedFramework && (
            <p style={metaStyle}>
              {selectedFramework.hook_type} · {selectedFramework.pacing} · {selectedFramework.cta_type}
              {selectedFramework.duration_sec ? ` · ${selectedFramework.duration_sec.toFixed(1)}s` : ""}
            </p>
          )}
        </div>

        {/* Generate */}
        <button
          onClick={handleGenerate}
          disabled={generating || !selectedStoryId || !selectedFrameworkId}
          style={primaryBtnStyle}
        >
          {generating ? "Generating…" : "Generate Reel Script"}
        </button>

        {error && <p style={{ color: "#c62828", fontSize: 13 }}>{error}</p>}

        {/* Recent scripts */}
        {scripts.length > 0 && (
          <div>
            <p style={{ ...labelStyle, marginBottom: 6 }}>Recent scripts</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {scripts.map(s => (
                <button
                  key={s.id}
                  onClick={() => handleSelectScript(s.id)}
                  style={{
                    textAlign: "left",
                    background: activeScript?.script_id === s.id ? "#e3f2fd" : "#f5f5f5",
                    border: "none",
                    borderRadius: 6,
                    padding: "6px 10px",
                    cursor: "pointer",
                    fontSize: 12,
                    color: "#333",
                  }}
                >
                  #{s.id} · {s.model_used} · {s.created_at?.slice(0, 16)}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* MP4 ingest */}
        <div style={{ borderTop: "1px solid #e0e0e0", paddingTop: 12 }}>
          <p style={labelStyle}>MP4 ingest</p>
          <button onClick={handleOpenReferences} style={secondaryBtnStyle}>
            Open references folder
          </button>
          <button
            onClick={handleScan}
            disabled={scanning}
            style={{ ...secondaryBtnStyle, marginTop: 6 }}
          >
            {scanning ? "Scanning…" : "Scan references folder"}
          </button>
          <p style={{ fontSize: 11, color: "#888", marginTop: 6, lineHeight: 1.4 }}>
            Drop .mp4 files into the references folder, then scan to extract frameworks.
            Successful extractions delete the source file; failures stay for inspection.
            May take several minutes per file.
          </p>
          {scanResult && (
            <div style={{ fontSize: 12, color: "#333", marginTop: 6 }}>
              Processed {scanResult.processed} ·{" "}
              OK {scanResult.succeeded.length} ·{" "}
              Failed {scanResult.failed.length}
              {scanResult.failed.length > 0 && (
                <ul style={{ margin: "4px 0 0 16px", padding: 0, color: "#c62828" }}>
                  {scanResult.failed.map(f => (
                    <li key={f.file}>{f.file}: {f.status}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </div>

      {/* RIGHT PANEL */}
      <div>
        {activeScript ? (
          <div>
            <div style={{ display: "flex", gap: 12, marginBottom: 12, flexWrap: "wrap" }}>
              <Chip label="Script" value={`#${activeScript.script_id}`} />
              <Chip label="Model" value={activeScript.model_used} />
              <Chip label="Story" value={`#${activeScript.story_node_id}`} />
              <Chip label="Framework" value={activeScript.framework_id} />
            </div>
            <pre style={draftStyle}>{activeScript.generated_text}</pre>
            <button
              onClick={() => navigator.clipboard.writeText(activeScript.generated_text)}
              style={{ ...secondaryBtnStyle, marginTop: 8 }}
            >
              Copy
            </button>
          </div>
        ) : (
          <div style={{ color: "#aaa", marginTop: 48, textAlign: "center" }}>
            {generating ? "Generating your reel script…" : "Select a story + framework and click Generate Reel Script"}
          </div>
        )}
      </div>

    </div>
  )
}

function Chip({ label, value }) {
  return (
    <span style={{ fontSize: 12, background: "#f0f4ff", borderRadius: 4, padding: "3px 8px", color: "#555" }}>
      <strong>{label}:</strong> {value}
    </span>
  )
}

const labelStyle = { display: "block", fontSize: 12, fontWeight: 600, color: "#555", marginBottom: 4 }
const metaStyle = { fontSize: 11, color: "#888", marginTop: 4, lineHeight: 1.4 }
const inputStyle = { width: "100%", padding: "7px 10px", borderRadius: 6, border: "1px solid #ddd", fontSize: 13, boxSizing: "border-box" }
const primaryBtnStyle = { width: "100%", padding: "10px", background: "#1565c0", color: "#fff", border: "none", borderRadius: 6, fontSize: 14, fontWeight: 600, cursor: "pointer" }
const secondaryBtnStyle = { width: "100%", marginTop: 6, padding: "8px", background: "#f5f5f5", color: "#333", border: "1px solid #ddd", borderRadius: 6, fontSize: 13, cursor: "pointer" }
const draftStyle = { whiteSpace: "pre-wrap", wordBreak: "break-word", background: "#fafafa", border: "1px solid #e0e0e0", borderRadius: 8, padding: 20, fontSize: 14, lineHeight: 1.7, minHeight: 300 }
