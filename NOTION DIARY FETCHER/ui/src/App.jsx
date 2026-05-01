import { useState } from 'react'
import PageList from './components/PageList.jsx'
import PageDetail from './components/PageDetail.jsx'

export default function App() {
  const [selectedPageId, setSelectedPageId] = useState(null)

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '2rem' }}>
      <h1 style={{ marginBottom: '1.5rem' }}>Notion Diary</h1>
      {selectedPageId == null ? (
        <PageList onSelect={setSelectedPageId} />
      ) : (
        <PageDetail pageId={selectedPageId} onBack={() => setSelectedPageId(null)} />
      )}
    </div>
  )
}