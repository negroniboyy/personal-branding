import { useState } from "react"
import { motion, LayoutGroup } from "framer-motion"
import Icon from "../ui/Icon.jsx"

const NAV_ITEMS = [
  { id: "studio",      label: "Studio",      icon: "rocket_launch" },
  { id: "reels",       label: "Reels",       icon: "movie_edit"   },
  { id: "writer",      label: "Writer",      icon: "edit_note"    },
  { id: "narrative",   label: "Narrative",   icon: "account_tree" },
  { id: "ideas",       label: "Ideas",       icon: "lightbulb"    },
  { id: "diary",       label: "Diary",       icon: "auto_stories" },
  { id: "frameworks",  label: "Frameworks",  icon: "schema"       },
]


export default function Sidebar({ activeTab, onTabChange }) {
  const [hovered, setHovered] = useState(null)

  return (
    <aside className="fixed left-0 top-0 h-screen w-[300px] hidden md:flex flex-col py-6 px-4 z-40 bg-white/40 backdrop-blur-xl border-r border-black/5">

      {/* Logo */}
      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="mb-8 px-2"
      >
        <div className="flex flex-col gap-4 mb-6">
          <span className="font-h2 text-h2 text-primary">StudioBrand</span>
        </div>
        <button
          onClick={() => {
            onTabChange("ideas")
            window.dispatchEvent(new CustomEvent("create-idea"))
          }}
          className="w-full glass-panel text-primary py-3 rounded-lg font-label-caps text-label-caps flex items-center justify-center gap-2 hover:bg-white transition-colors border-primary/20"
        >
          <Icon name="add" size={18} />
          New Idea
        </button>
      </motion.div>

      {/* Nav items */}
      <nav className="flex-1 space-y-1">
        <LayoutGroup>
          {NAV_ITEMS.map((item) => {
            const isActive = activeTab === item.id
            const isHovered = hovered === item.id
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                onMouseEnter={() => setHovered(item.id)}
                onMouseLeave={() => setHovered(null)}
                className="relative w-full flex items-center gap-3 px-4 py-3 rounded-lg font-label-caps text-label-caps transition-colors text-left"
              >
                {isActive && (
                  <motion.div
                    layoutId="activeNavPill"
                    className="absolute inset-0 rounded-lg"
                    style={{
                      background: "linear-gradient(90deg, rgba(70,72,212,0.1) 0%, rgba(129,39,207,0.1) 100%)",
                      border: "1px solid rgba(70,72,212,0.1)",
                    }}
                    transition={{ type: "spring", stiffness: 400, damping: 35 }}
                  />
                )}
                <Icon
                  name={item.icon}
                  fill={isActive || isHovered}
                  size={22}
                  className={`relative z-10 transition-colors ${isActive ? "text-primary" : "text-on-surface-variant"}`}
                />
                <span className={`relative z-10 transition-colors ${isActive ? "text-primary" : "text-on-surface-variant hover:text-on-surface"}`}>
                  {item.label}
                </span>
              </button>
            )
          })}
        </LayoutGroup>
      </nav>

    </aside>
  )
}
