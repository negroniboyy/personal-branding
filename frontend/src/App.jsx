import { useState } from "react"
import PageList from "./components/PageList.jsx"
import PageDetail from "./components/PageDetail.jsx"
import NarrativeDashboard from "./components/NarrativeDashboard.jsx"
import StoryNodeList from "./components/StoryNodeList.jsx"
import ContentWriter from "./components/ContentWriter.jsx"
import ReelWriter from "./components/ReelWriter.jsx"

export default function App() {
  const [tab, setTab] = useState("diary")
  const [selectedPageId, setSelectedPageId] = useState(null)

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "2rem" }}>
      <h1 style={{ marginBottom: "1.5rem" }}>Personal Brand</h1>

      <div style={{ display: "flex", gap: 4, marginBottom: 24, borderBottom: "1px solid #e0e0e0" }}>
        <TabButton active={tab === "diary"} onClick={() => { setTab("diary"); setSelectedPageId(null) }}>
          Diary
        </TabButton>
        <TabButton active={tab === "narrative"} onClick={() => setTab("narrative")}>
          Narrative Warehouse
        </TabButton>
        <TabButton active={tab === "writer"} onClick={() => setTab("writer")}>
          Content Writer
        </TabButton>
        <TabButton active={tab === "reels"} onClick={() => setTab("reels")}>
          Reels
        </TabButton>
      </div>

      {tab === "diary" && (
        selectedPageId == null ? (
          <PageList onSelect={setSelectedPageId} />
        ) : (
          <PageDetail pageId={selectedPageId} onBack={() => setSelectedPageId(null)} />
        )
      )}

      {tab === "writer" && <ContentWriter />}

      {tab === "reels" && <ReelWriter />}

      {tab === "narrative" && (
        <div>
          <NarrativeDashboard />
          <h2 style={{ fontSize: 18, fontWeight: 700, marginTop: 32, marginBottom: 16 }}>Story Ideas</h2>
          <StoryNodeList />
        </div>
      )}
    </div>
  )
}

function TabButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "8px 20px",
        border: "none",
        borderBottom: active ? "2px solid #1565c0" : "2px solid transparent",
        background: "none",
        cursor: "pointer",
        fontSize: 14,
        fontWeight: active ? 700 : 500,
        color: active ? "#1565c0" : "#888",
      }}
    >
      {children}
    </button>
  )
}