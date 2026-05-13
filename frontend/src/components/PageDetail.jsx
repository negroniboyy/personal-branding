import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { fetchPage } from "../api.js"
import GlassPanel from "./ui/GlassPanel.jsx"
import Icon from "./ui/Icon.jsx"

const BLOCK_TYPE_COLORS = {
  heading_1: "text-primary",
  heading_2: "text-primary/80",
  heading_3: "text-primary/60",
  paragraph: "text-on-surface-variant",
  bulleted_list_item: "text-secondary",
  numbered_list_item: "text-secondary",
}

export default function PageDetail({ pageId, onBack }) {
  const [page, setPage] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    fetchPage(pageId)
      .then(data => { setPage(data); setLoading(false) })
      .catch(err => { setError(err.message); setLoading(false) })
  }, [pageId])

  if (loading) return (
    <div className="flex flex-col gap-4">
      <div className="h-8 bg-surface-container rounded w-1/2 animate-pulse" />
      {[...Array(5)].map((_, i) => (
        <div key={i} className="h-4 bg-surface-container rounded animate-pulse" style={{ width: `${70 + Math.random() * 30}%` }} />
      ))}
    </div>
  )

  if (error) return (
    <GlassPanel className="rounded-xl p-card_padding border-error/20">
      <div className="flex items-center gap-2 text-error font-label-caps text-label-caps">
        <Icon name="error" size={16} /> {error}
      </div>
    </GlassPanel>
  )

  if (!page) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="flex flex-col gap-6"
    >
      <button
        onClick={onBack}
        className="flex items-center gap-2 text-on-surface-variant hover:text-primary font-label-caps text-label-caps transition-colors w-fit"
      >
        <Icon name="arrow_back" size={16} />
        Back to Diary
      </button>

      <GlassPanel className="rounded-xl p-card_padding">
        <h1 className="font-h1 text-h1 text-on-surface mb-2">{page.title || "Untitled"}</h1>
        <p className="font-label-caps text-label-caps text-on-surface-variant">
          {new Date(page.created_time).toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" }).toUpperCase()}
        </p>
      </GlassPanel>

      <GlassPanel className="rounded-xl p-card_padding">
        <div className="flex flex-col gap-4">
          {page.blocks
            .filter(b => b.plain_text != null)
            .map((block, i) => (
              <div key={i} className="flex items-start gap-3">
                <span className={`font-label-caps text-[10px] mt-1 px-2 py-0.5 rounded glass-panel flex-shrink-0 ${BLOCK_TYPE_COLORS[block.block_type] || "text-outline"}`}>
                  {block.block_type?.replace(/_/g, " ").toUpperCase()}
                </span>
                <span className="font-body text-body text-on-surface leading-relaxed">{block.plain_text}</span>
              </div>
            ))}
        </div>
      </GlassPanel>
    </motion.div>
  )
}
