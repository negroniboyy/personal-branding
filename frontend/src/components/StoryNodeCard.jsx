import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { updateStoryNode } from "../narrativeApi"
import GlassPanel from "./ui/GlassPanel.jsx"
import Icon from "./ui/Icon.jsx"

export default function StoryNodeCard({ node, onUpdate }) {
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({
    user_state: node.user_state,
    conflict_node: node.conflict_node,
    desired_outcome: node.desired_outcome,
    the_bridge: node.the_bridge,
    thematic_tags: typeof node.thematic_tags === "string" ? JSON.parse(node.thematic_tags || "[]") : (node.thematic_tags || []),
    worth_score: node.worth_score,
    narrative_flag: node.narrative_flag,
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const isLowPotential = node.narrative_flag === "Low Narrative Potential"
  const tags = Array.isArray(form.thematic_tags) ? form.thematic_tags : []

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
      thematic_tags: typeof node.thematic_tags === "string" ? JSON.parse(node.thematic_tags || "[]") : (node.thematic_tags || []),
      worth_score: node.worth_score,
      narrative_flag: node.narrative_flag,
    })
    setEditing(false)
    setError(null)
  }

  return (
    <GlassPanel className={`rounded-xl p-card_padding transition-all ${editing ? "border-primary/30" : "hover:border-primary/20 hover:bg-white"}`}>
      {/* Header row */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className={`font-label-caps text-label-caps px-2 py-0.5 rounded ${
            isLowPotential
              ? "bg-surface-container text-on-surface-variant"
              : "bg-primary/5 text-primary border border-primary/10"
          }`}>
            {node.narrative_flag}
          </span>
          <span className="font-label-caps text-[10px] text-on-surface-variant">
            {node.created_time?.slice(0, 10)}
          </span>
        </div>
        {!editing && (
          <motion.button
            onClick={() => setEditing(true)}
            whileTap={{ scale: 0.95 }}
            className="flex items-center gap-1.5 glass-panel px-3 py-1.5 rounded-lg font-label-caps text-label-caps text-on-surface-variant hover:text-primary transition-colors"
          >
            <Icon name="edit" size={14} />
            Edit
          </motion.button>
        )}
      </div>

      {error && (
        <div className="flex items-center gap-2 text-error font-label-caps text-label-caps mb-3">
          <Icon name="error" size={14} /> {error}
        </div>
      )}

      {/* Fields */}
      <div className="grid grid-cols-1 gap-4">
        <Field label="User State" value={form.user_state} editing={editing} onChange={v => setForm(f => ({ ...f, user_state: v }))} />
        <Field label="Conflict Node" value={form.conflict_node} editing={editing} onChange={v => setForm(f => ({ ...f, conflict_node: v }))} />
        <Field label="Desired Outcome" value={form.desired_outcome} editing={editing} onChange={v => setForm(f => ({ ...f, desired_outcome: v }))} />
        <Field label="The Bridge" value={form.the_bridge} editing={editing} onChange={v => setForm(f => ({ ...f, the_bridge: v }))} />
      </div>

      {/* Worth score */}
      <div className="mt-4">
        <label className="font-label-caps text-label-caps text-on-surface-variant block mb-2">WORTH SCORE</label>
        <div className="flex items-center gap-3">
          <input
            type="range" min="0" max="1" step="0.01"
            value={form.worth_score}
            onChange={e => setForm(f => ({ ...f, worth_score: parseFloat(e.target.value) }))}
            disabled={!editing}
            className="flex-1 accent-primary"
          />
          <span className="font-label-caps text-label-caps text-primary min-w-[40px] text-right">
            {form.worth_score?.toFixed(2)}
          </span>
        </div>
      </div>

      {/* Tags */}
      <div className="mt-4">
        <label className="font-label-caps text-label-caps text-on-surface-variant block mb-2">TAGS</label>
        <div className="flex flex-wrap gap-2">
          {tags.map(tag => (
            <span key={tag} className="bg-primary/5 border border-primary/10 text-primary font-label-caps text-label-caps px-2 py-0.5 rounded">
              {tag}
            </span>
          ))}
        </div>
        {editing && (
          <input
            type="text"
            value={tags.join(", ")}
            onChange={e => setForm(f => ({ ...f, thematic_tags: e.target.value.split(",").map(t => t.trim()).filter(Boolean) }))}
            placeholder="tag1, tag2, tag3"
            className="mt-2 w-full glass-panel rounded-lg px-4 py-2 font-mono-script text-mono-script text-on-surface focus:ring-1 focus:ring-primary outline-none border-black/5"
          />
        )}
      </div>

      {/* Edit actions */}
      <AnimatePresence>
        {editing && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="flex gap-3 mt-5"
          >
            <motion.button
              onClick={handleSave}
              disabled={saving}
              whileTap={{ scale: 0.98 }}
              className="px-5 py-2 rounded-xl font-label-caps text-label-caps bg-primary text-on-primary hover:bg-primary/90 transition-all disabled:opacity-40"
            >
              {saving ? "Saving..." : "Save"}
            </motion.button>
            <motion.button
              onClick={handleCancel}
              whileTap={{ scale: 0.98 }}
              className="px-5 py-2 rounded-xl font-label-caps text-label-caps glass-panel text-on-surface-variant hover:text-on-surface transition-colors"
            >
              Cancel
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>
    </GlassPanel>
  )
}

function Field({ label, value, editing, onChange }) {
  return (
    <div>
      <label className="font-label-caps text-label-caps text-on-surface-variant block mb-1">{label.toUpperCase()}</label>
      {editing ? (
        <input
          type="text"
          value={value || ""}
          onChange={e => onChange(e.target.value)}
          className="w-full glass-panel rounded-lg px-4 py-2 font-body text-body text-on-surface focus:ring-1 focus:ring-primary outline-none border-black/5"
        />
      ) : (
        <p className="font-body text-body text-on-surface">{value || <span className="text-on-surface-variant italic">—</span>}</p>
      )}
    </div>
  )
}
