import { useState, useEffect, useCallback } from "react"
import {
  fetchFrameworks,
  postRecommendations,
  postGenerate,
  fetchDrafts,
  fetchDraft,
} from "../contentWriterApi.js"

export default function ContentWriter() {
  const [stories, setStories] = useState([])
  const [frameworks, setFrameworks] = useState([])
  const [selectedStoryId, setSelectedStoryId] = useState(null)
  const [selectedFrameworkId, setSelectedFrameworkId] = useState(null)
  const [ideaPrompt, setIdeaPrompt] = useState("")
  const [manualOverride, setManualOverride] = useState(false)
  const [drafts, setDrafts] = useState([])
  const [activeDraft, setActiveDraft] = useState(null)
  const [generating, setGenerating] = useState(false)
  const [loadingRecs, setLoadingRecs] = useState(false)
  const [error, setError] = useState(null)

  const loadRecommendations = useCallback(async (idea) => {
    setLoadingRecs(true)
    setError(null)
    try {
      const data = await postRecommendations({ idea_prompt: idea || null, top_n: 5 })
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

  const loadDrafts = async () => {
    try {
      const data = await fetchDrafts()
      setDrafts(data)
    } catch { /* non-blocking */ }
  }

  useEffect(() => {
    loadRecommendations("")
    loadDrafts()
  }, [])

  const handleGenerate = async () => {
    if (!selectedStoryId || !selectedFrameworkId) return
    setGenerating(true)
    setError(null)
    setActiveDraft(null)
    try {
      const result = await postGenerate({
        story_node_id: selectedStoryId,
        framework_id: selectedFrameworkId,
        idea_prompt: ideaPrompt || null,
      })
      setActiveDraft(result)
      await loadDrafts()
    } catch (e) {
      setError(e.message)
    } finally {
      setGenerating(false)
    }
  }

  const handleSelectDraft = async (id) => {
    try {
      const d = await fetchDraft(id)
      setActiveDraft(d)
    } catch (e) {
      setError(e.message)
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
            placeholder="e.g. overcoming imposter syndrome in your 30s"
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
            onChange={e => { setSelectedStoryId(Number(e.target.value)); setManualOverride(true) }}
            style={inputStyle}
          >
            {stories.length === 0 && <option value="">No stories loaded</option>}
            {stories.map(s => (
              <option key={s.id} value={s.id}>
                [{s.worth_score?.toFixed(1)}] {s.title || `#${s.id}`}
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
            onChange={e => { setSelectedFrameworkId(Number(e.target.value)); setManualOverride(true) }}
            style={inputStyle}
          >
            {frameworks.length === 0 && <option value="">No frameworks loaded</option>}
            {frameworks.map(f => (
              <option key={f.id} value={f.id}>{f.name}</option>
            ))}
          </select>
          {selectedFramework && (
            <p style={metaStyle}>{selectedFramework.hook_type} · {selectedFramework.tone}</p>
          )}
        </div>

        {/* Generate */}
        <button
          onClick={handleGenerate}
          disabled={generating || !selectedStoryId || !selectedFrameworkId}
          style={primaryBtnStyle}
        >
          {generating ? "Generating…" : "Generate Draft"}
        </button>

        {error && <p style={{ color: "#c62828", fontSize: 13 }}>{error}</p>}

        {/* Recent drafts */}
        {drafts.length > 0 && (
          <div>
            <p style={{ ...labelStyle, marginBottom: 6 }}>Recent drafts</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {drafts.map(d => (
                <button
                  key={d.id}
                  onClick={() => handleSelectDraft(d.id)}
                  style={{
                    textAlign: "left",
                    background: activeDraft?.id === d.id ? "#e3f2fd" : "#f5f5f5",
                    border: "none",
                    borderRadius: 6,
                    padding: "6px 10px",
                    cursor: "pointer",
                    fontSize: 12,
                    color: "#333",
                  }}
                >
                  #{d.id} · {d.model_used} · {d.created_at?.slice(0, 16)}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* RIGHT PANEL */}
      <div>
        {activeDraft ? (
          <div>
            <div style={{ display: "flex", gap: 12, marginBottom: 12, flexWrap: "wrap" }}>
              <Chip label="Draft" value={`#${activeDraft.draft_id ?? activeDraft.id}`} />
              <Chip label="Model" value={activeDraft.model_used} />
              <Chip label="Story" value={`#${activeDraft.story_node_id}`} />
              <Chip label="Framework" value={`#${activeDraft.framework_id}`} />
            </div>
            <pre style={draftStyle}>{activeDraft.generated_text}</pre>
            <button
              onClick={() => navigator.clipboard.writeText(activeDraft.generated_text)}
              style={{ ...secondaryBtnStyle, marginTop: 8 }}
            >
              Copy
            </button>
          </div>
        ) : (
          <div style={{ color: "#aaa", marginTop: 48, textAlign: "center" }}>
            {generating ? "Generating your draft…" : "Select a story + framework and click Generate Draft"}
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
