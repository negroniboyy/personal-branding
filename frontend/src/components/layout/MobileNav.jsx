import { motion, LayoutGroup } from "framer-motion"
import Icon from "../ui/Icon.jsx"

const NAV_ITEMS = [
  { id: "diary",     label: "Diary",     icon: "auto_stories" },
  { id: "narrative", label: "Narrative", icon: "account_tree" },
  { id: "writer",    label: "Writer",    icon: "edit_note"    },
  { id: "reels",     label: "Reels",     icon: "movie_edit"   },
]

export default function MobileNav({ activeTab, onTabChange }) {
  return (
    <nav className="fixed bottom-0 left-0 w-full z-50 flex md:hidden justify-around items-center px-4 py-2 glass-panel border-t border-black/5 shadow-lg bg-white/80">
      <LayoutGroup>
        {NAV_ITEMS.map((item) => {
          const isActive = activeTab === item.id
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className="relative flex flex-col items-center justify-center p-2 font-label-caps text-label-caps"
            >
              {isActive && (
                <motion.div
                  layoutId="mobileActivePill"
                  className="absolute inset-0 rounded-xl bg-primary/10"
                  transition={{ type: "spring", stiffness: 400, damping: 35 }}
                />
              )}
              <Icon
                name={item.icon}
                fill={isActive}
                size={22}
                className={`relative z-10 transition-colors ${isActive ? "text-primary" : "text-on-surface-variant"}`}
              />
              <span className={`relative z-10 mt-0.5 transition-colors ${isActive ? "text-primary" : "text-on-surface-variant"}`}>
                {item.label}
              </span>
            </button>
          )
        })}
      </LayoutGroup>
    </nav>
  )
}
