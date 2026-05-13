import { useState } from "react"
import { AnimatePresence, motion } from "framer-motion"
import PageList from "./components/PageList.jsx"
import PageDetail from "./components/PageDetail.jsx"
import NarrativeDashboard from "./components/NarrativeDashboard.jsx"
import StoryNodeList from "./components/StoryNodeList.jsx"
import ContentWriter from "./components/ContentWriter.jsx"
import ReelWriter from "./components/ReelWriter.jsx"
import IdeasTab from "./components/IdeasTab.jsx"
import Sidebar from "./components/layout/Sidebar.jsx"
import MobileNav from "./components/layout/MobileNav.jsx"

const PAGE_TITLES = {
  diary: "Diary",
  narrative: "Narrative Warehouse",
  writer: "Content Writer",
  reels: "Reels",
  ideas: "Ideas",
}

export default function App() {
  const [tab, setTab] = useState("diary")
  const [selectedPageId, setSelectedPageId] = useState(null)

  function handleTabChange(newTab) {
    setTab(newTab)
    if (newTab !== "diary") setSelectedPageId(null)
  }

  return (
    <div className="relative min-h-screen bg-background text-on-background font-body text-body selection:bg-primary-container selection:text-on-primary-container">
      <div className="gradient-bg" />

      <Sidebar activeTab={tab} onTabChange={handleTabChange} />
      <MobileNav activeTab={tab} onTabChange={handleTabChange} />

      <main className="md:pl-[300px] min-h-screen pb-20 md:pb-0">
        <div className="max-w-[900px] mx-auto px-gutter py-section_padding">

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
              key={tab + (selectedPageId ?? "")}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.22, ease: "easeOut" }}
            >
              {tab === "diary" && (
                selectedPageId == null
                  ? <PageList onSelect={setSelectedPageId} />
                  : <PageDetail pageId={selectedPageId} onBack={() => setSelectedPageId(null)} />
              )}
              {tab === "writer" && <ContentWriter />}
              {tab === "reels" && <ReelWriter />}
              {tab === "ideas" && <IdeasTab />}
              {tab === "narrative" && (
                <div className="flex flex-col gap-0">
                  <NarrativeDashboard />
                  <h2 className="font-label-caps text-label-caps text-on-surface-variant mt-2 mb-4">STORY IDEAS</h2>
                  <StoryNodeList />
                </div>
              )}
            </motion.div>
          </AnimatePresence>

        </div>
      </main>
    </div>
  )
}
