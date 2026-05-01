import { useState } from "react"
import { updateStoryNode } from "../narrativeApi"

export default function StoryNodeCard({ node, onUpdate }) {
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({
    user_state: node.user_state,
    conflict_node: node.conflict_node,
    desired_outcome: node.desired_outcome,
    the_bridge: node.the_bridge,
    thematic_tags: typeof node.thematic_tags === "string" ? node.thematic_tags : JSON.parse(node.thematic_tags || "[]"),
    worth_score: node.worth_score,
    narrative_flag: node.narrative_flag,
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      const updated = await updateStoryNode(node.id, {
        user_state: form.user_state,
        conflict_node: form.conflict_node,
        desired_outcome: form.desired_outcome,
        the_bridge: form.the_bridge,
        thematic_tags: form.thematic_tags,
        worth_score: form.worth_score,
        narrative_flag: form.narrative_flag,
      })
      onUpdate(updated)
      setEditing(false)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    setForm({
      user_state: node.user_state,
      conflict_node: node.conflict_node,
      desired_outcome: node.desired_outcome,
      the_bridge: node.the_bridge,
      thematic_tags: typeof node.thematic_tags === "string" ? JSON.parse(node.thematic_tags || "[]") : node.thematic_tags,
      worth_score: node.worth_score,
      narrative_flag: node.narrative_flag,
    })
    setEditing(false)
    setError(null)
  }

  const tags = Array.isArray(form.thematic_tags) ? form.thematic_tags : []

  return (
    <div style={{
      border: "1px solid #e0e0e0",
      borderRadius: 8,
      padding: 16,
      marginBottom: 12,
      background: editing ? "#fafafa" : "#fff",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
        <div>
          <span style={{
            background: node.narrative_flag === "Low Narrative Potential" ? "#f5f5f5" : "#e8f5e9",
            color: node.narrative_flag === "Low Narrative Potential" ? "#666" : "#2e7d32",
            padding: "2px 8px",
            borderRadius: 4,
            fontSize: 11,
            fontWeight: 600,
          }}>{node.narrative_flag}</span>
          <span style={{ marginLeft: 8, fontSize: 12, color: "#888" }}>{node.created_time?.slice(0, 10)}</span>
        </div>
        {!editing && (
          <button onClick={() => setEditing(true)} style={editBtnStyle}>Edit</button>
        )}
      </div>

      {error && <div style={{ color: "red", marginBottom: 8, fontSize: 13 }}>{error}</div>}

      <Field label="User State" value={form.user_state} editing={editing}
        onChange={v => setForm(f => ({ ...f, user_state: v }))} />

      <Field label="Conflict Node" value={form.conflict_node} editing={editing}
        onChange={v => setForm(f => ({ ...f, conflict_node: v }))} />

      <Field label="Desired Outcome" value={form.desired_outcome} editing={editing}
        onChange={v => setForm(f => ({ ...f, desired_outcome: v }))} />

      <Field label="The Bridge" value={form.the_bridge} editing={editing}
        onChange={v => setForm(f => ({ ...f, the_bridge: v }))} />

      <div style={{ marginBottom: 10 }}>
        <label style={labelStyle}>Worth Score</label>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <input
            type="range" min="0" max="1" step="0.01"
            value={form.worth_score}
            onChange={e => setForm(f => ({ ...f, worth_score: parseFloat(e.target.value) }))}
            disabled={!editing}
            style={{ flex: 1 }}
          />
          <span style={{ fontWeight: 700, minWidth: 40 }}>{form.worth_score?.toFixed(2)}</span>
        </div>
      </div>

      <div style={{ marginBottom: 10 }}>
        <label style={labelStyle}>Tags</label>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {tags.map(tag => (
            <span key={tag} style={tagStyle}>{tag}</span>
          ))}
        </div>
        {editing && (
          <input
            type="text"
            value={tags.join(", ")}
            onChange={e => setForm(f => ({
              ...f,
              thematic_tags: e.target.value.split(",").map(t => t.trim()).filter(Boolean)
            }))}
            placeholder="tag1, tag2, tag3"
            style={inputStyle}
          />
        )}
      </div>

      {editing && (
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <button onClick={handleSave} disabled={saving} style={saveBtnStyle}>
            {saving ? "Saving..." : "Save"}
          </button>
          <button onClick={handleCancel} style={cancelBtnStyle}>Cancel</button>
        </div>
      )}
    </div>
  )
}

function Field({ label, value, editing, onChange }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <label style={labelStyle}>{label}</label>
      {editing ? (
        <input type="text" value={value} onChange={e => onChange(e.target.value)} style={inputStyle} />
      ) : (
        <div style={{ color: "#222", fontSize: 14 }}>{value}</div>
      )}
    </div>
  )
}

const labelStyle = { display: "block", fontSize: 11, fontWeight: 600, color: "#888", marginBottom: 4, textTransform: "uppercase", letterSpacing: 0.5 }
const inputStyle = { width: "100%", padding: "6px 10px", border: "1px solid #ccc", borderRadius: 4, fontSize: 14, boxSizing: "border-box" }
const tagStyle = { background: "#e3f2fd", color: "#1565c0", padding: "2px 8px", borderRadius: 4, fontSize: 12 }
const editBtnStyle = { background: "#fff", border: "1px solid #ccc", borderRadius: 4, padding: "4px 12px", cursor: "pointer", fontSize: 12 }
const saveBtnStyle = { background: "#2e7d32", color: "#fff", border: "none", borderRadius: 4, padding: "6px 16px", cursor: "pointer", fontSize: 13 }
const cancelBtnStyle = { background: "#fff", color: "#666", border: "1px solid #ccc", borderRadius: 4, padding: "6px 16px", cursor: "pointer", fontSize: 13 }