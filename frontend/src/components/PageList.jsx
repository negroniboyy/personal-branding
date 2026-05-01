import { useState, useEffect } from 'react'
import { fetchPages } from '../api.js'

export default function PageList({ onSelect }) {
  const [pages, setPages] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchPages()
      .then(data => {
        setPages(data)
        setLoading(false)
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  if (loading) return <p>Loading pages...</p>
  if (error) return <p style={{ color: 'red' }}>Error: {error}</p>

  return (
    <div>
      <p style={{ marginBottom: '1rem', color: '#666' }}>{pages.length} pages</p>
      <ul style={{ listStyle: 'none', padding: 0 }}>
        {pages.map(page => (
          <li key={page.id} style={{ marginBottom: '0.75rem' }}>
            <button
              onClick={() => onSelect(page.id)}
              style={{
                background: 'none',
                border: 'none',
                padding: 0,
                textAlign: 'left',
                cursor: 'pointer',
                color: '#0066cc',
                textDecoration: 'underline',
                fontSize: '1rem'
              }}
            >
              {page.title || 'Untitled'}
            </button>
            <br />
            <span style={{ fontSize: '0.85rem', color: '#888' }}>
              {new Date(page.created_time).toLocaleDateString()}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}