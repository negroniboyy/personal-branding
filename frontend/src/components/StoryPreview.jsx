import GlassPanel from "./ui/GlassPanel.jsx"

function parseTags(value) {
  if (Array.isArray(value)) return value
  try { return JSON.parse(value || "[]") } catch { return [] }
}

const ROWS = [
  ["User state", "user_state"],
  ["Conflict", "conflict_node"],
  ["Desired outcome", "desired_outcome"],
  ["The bridge", "the_bridge"],
]

export default function StoryPreview({ story }) {
  if (!story) return null
  const tags = parseTags(story.thematic_tags)
  const score = story.worth_score != null ? Number(story.worth_score).toFixed(2) : null

  return (
    <GlassPanel className="rounded-xl p-card_padding bg-white/40">
      <div className="flex items-center justify-between mb-3">
        <span className="font-label-caps text-label-caps text-on-surface-variant">STORY PREVIEW</span>
        {score && (
          <span className="font-label-caps text-label-caps text-primary bg-primary/5 border border-primary/10 px-2 py-0.5 rounded">
            {score}
          </span>
        )}
      </div>
      <div className="flex flex-col gap-2">
        {ROWS.map(([label, key]) => story[key] ? (
          <div key={key} className="grid grid-cols-[110px_1fr] gap-3">
            <span className="font-label-caps text-[10px] text-on-surface-variant pt-0.5">{label.toUpperCase()}</span>
            <span className="font-body text-body text-on-surface leading-snug">{story[key]}</span>
          </div>
        ) : null)}
      </div>
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {tags.map(tag => (
            <span key={tag} className="bg-primary/5 border border-primary/10 text-primary font-label-caps text-[10px] px-2 py-0.5 rounded">
              {tag}
            </span>
          ))}
        </div>
      )}
    </GlassPanel>
  )
}
