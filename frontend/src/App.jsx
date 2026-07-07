import { useState } from "react"
import { AnimatePresence, motion } from "framer-motion"
import ContentWriter from "./components/ContentWriter.jsx"
import ReelWriter from "./components/ReelWriter.jsx"
import IdeasTab from "./components/IdeasTab.jsx"
import FrameworksTab from "./components/FrameworksTab.jsx"
import StudioTab from "./components/StudioTab.jsx"
import Sidebar from "./components/layout/Sidebar.jsx"
import MobileNav from "./components/layout/MobileNav.jsx"

const PAGE_TITLES = {
  studio: "Studio",
  writer: "Content Writer",
  reels: "Reels",
  ideas: "Ideas",
  frameworks: "Frameworks",
}

export default function App() {
  const [tab, setTab] = useState("studio")

  function handleTabChange(newTab) {
    setTab(newTab)
  }

  return (
    <div className="relative min-h-screen bg-background text-on-background font-body text-body selection:bg-primary-container selection:text-on-primary-container">
      <div className="gradient-bg" />

      <Sidebar activeTab={tab} onTabChange={handleTabChange} />
      <MobileNav activeTab={tab} onTabChange={handleTabChange} />

      <main className="md:pl-[300px] min-h-screen pb-20 md:pb-0">
        <div className={`mx-auto px-gutter py-section_padding ${tab === "ideas" ? "max-w-[1400px]" : "max-w-[900px]"}`}>

          {/* Page heading */}
          <motion.h1
            key={tab}
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
            className="font-h1 text-h1 text-on-surface mb-8"
          >
            {PAGE_TITLES[tab]}
          </motion.h1>

          {/* Tab content with crossfade transition */}
          <AnimatePresence mode="wait">
            <motion.div
              key={tab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.22, ease: "easeOut" }}
            >
              {tab === "studio" && <StudioTab />}
              {tab === "writer" && <ContentWriter />}
              {tab === "reels" && <ReelWriter />}
              {tab === "ideas" && <IdeasTab />}
              {tab === "frameworks" && <FrameworksTab />}
            </motion.div>
          </AnimatePresence>

        </div>
      </main>
    </div>
  )
}
