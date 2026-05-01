import { useState, useEffect } from 'react'
import { fetchPage } from '../api.js'

export default function PageDetail({ pageId, onBack }) {
  const [page, setPage] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    fetchPage(pageId)
      .then(data => {
        setPage(data)
        setLoading(false)
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
      })
  }, [pageId])

  if (loading) return <p>Loading page...</p>
  if (error) return <p style={{ color: 'red' }}>Error: {error}</p>
  if (!page) return null

  return (
    <div>
      <button
        onClick={onBack}
        style={{ marginBottom: '1rem', cursor: 'pointer' }}
      >
        &larr; Back
      </button>
      <h2>{page.title || 'Untitled'}</h2>
      <p style={{ fontSize: '0.85rem', color: '#888', marginBottom: '1.5rem' }}>
        {new Date(page.created_time).toLocaleDateString()}
      </p>
      <div>
        {page.blocks
          .filter(b => b.plain_text != null)
          .map((block, i) => (
            <div key={i} style={{ marginBottom: '1rem' }}>
              <span style={{
                display: 'inline-block',
                fontSize: '0.75rem',
                background: '#eee',
                padding: '0.1rem 0.4rem',
                borderRadius: '3px',
                color: '#666',
                marginRight: '0.5rem'
              }}>
                {block.block_type}
              </span>
              <span>{block.plain_text}</span>
            </div>
          ))}
      </div>
    </div>
  )
}