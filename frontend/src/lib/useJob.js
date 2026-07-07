import { useEffect, useRef, useState } from "react"
import { API_BASE as BASE } from "../apiBase"

async function fetchJob(jobId) {
  const res = await fetch(`${BASE}/jobs/${jobId}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

// Polls a background job (queued -> running -> done|failed) until it reaches
// a terminal state. Leaving the page and coming back loses nothing — the job
// keeps running server-side; a new useJob(jobId) call just resumes polling.
export function useJob(jobId, { intervalMs = 2000, onDone, onError } = {}) {
  const [job, setJob] = useState(null)
  const [error, setError] = useState(null)
  const onDoneRef = useRef(onDone)
  const onErrorRef = useRef(onError)
  onDoneRef.current = onDone
  onErrorRef.current = onError

  useEffect(() => {
    if (!jobId) {
      setJob(null)
      setError(null)
      return
    }
    let cancelled = false
    let timer = null

    async function poll() {
      try {
        const j = await fetchJob(jobId)
        if (cancelled) return
        setJob(j)
        if (j.status === "done") {
          onDoneRef.current?.(j.result)
          return
        }
        if (j.status === "failed") {
          onErrorRef.current?.(j.error || "job failed")
          return
        }
        timer = setTimeout(poll, intervalMs)
      } catch (e) {
        if (cancelled) return
        setError(e.message)
      }
    }
    poll()

    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [jobId, intervalMs])

  return { job, error }
}
