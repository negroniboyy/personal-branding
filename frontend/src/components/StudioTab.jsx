import { useEffect, useMemo, useState } from "react"
import { motion } from "framer-motion"
import { fetchReelScripts, patchReelScript, patchReelScriptMeta, postReelPackage, fetchReelScriptVersions } from "../reelApi"
import { fetchDrafts, patchDraft, patchDraftMeta, postDraftPackage } from "../contentWriterApi"
import GlassPanel from "./ui/GlassPanel.jsx"
import Icon from "./ui/Icon.jsx"

const BACKLOG_TARGET = 30

function toItem(row, channel) {
  return { ...row, channel, key: `${channel}-${row.id}` }
}

export default function StudioTab() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const [scripts, drafts] = await Promise.all([fetchReelScripts(), fetchDrafts()])
      setItems([
        ...scripts.map(s => toItem(s, "reel")),
        ...drafts.map(d => toItem(d, "linkedin")),
      ])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  function replaceItem(updated, channel) {
    setItems(prev => prev.map(it => (it.channel === channel && it.id === updated.id ? { ...it, ...updated } : it)))
  }

  const groups = useMemo(() => {
    const status = it => it.status || "queued"
    const byDate = (a, b) => (b.created_at || "").localeCompare(a.created_at || "")
    return {
      queued:   items.filter(it => status(it) === "queued").sort(byDate),
      workshop: items.filter(it => ["approved", "recorded"].includes(status(it))).sort(byDate),
      posted:   items.filter(it => status(it) === "posted").sort((a, b) => (b.posted_at || "").localeCompare(a.posted_at || "")),
      rejected: items.filter(it => status(it) === "killed").sort(byDate),
    }
  }, [items])

  const postedLast30 = useMemo(() => {
    const cutoff = new Date(Date.now() - 30 * 86400_000).toISOString().slice(0, 10)
    return groups.posted.filter(it => (it.posted_at || "") >= cutoff).length
  }, [groups.posted])

  return (
    <div className="flex flex-col gap-8">
      <GlassPanel className="rounded-xl p-card_padding">
        <div className="flex flex-wrap items-center gap-6">
          <Meter label="READY AHEAD" value={groups.workshop.length} target={BACKLOG_TARGET} />
          <Stat label="IN QUEUE" value={groups.queued.length} />
          <Stat label="POSTED · 30 DAYS" value={postedLast30} />
          <button
            onClick={load}
            className="ml-auto p-2 rounded-lg text-on-surface-variant hover:text-primary transition-colors"
            title="Refresh"
          >
            <Icon name="refresh" size={18} />
          </button>
        </div>
        <div className="mt-3 h-2 rounded-full bg-primary/10 overflow-hidden">
          <motion.div
            className="h-full rounded-full bg-primary"
            initial={{ width: 0 }}
            animate={{ width: `${Math.min(100, (groups.workshop.length / BACKLOG_TARGET) * 100)}%` }}
            transition={{ duration: 0.6, ease: "easeOut" }}
          />
        </div>
        <p className="mt-2 font-label-caps text-[10px] text-on-surface-variant">
          MORNING DIGEST UNLOCKS AT {BACKLOG_TARGET} APPROVED POSTS
        </p>
      </GlassPanel>

      {error && (
        <div className="flex items-center gap-2 text-error font-label-caps text-label-caps">
          <Icon name="error" size={14} /> {error}
        </div>
      )}
      {loading && <p className="font-label-caps text-label-caps text-on-surface-variant">LOADING PIPELINE…</p>}

      <Section title="QUEUE — REVIEW" empty="Nothing queued. Generate drafts in Reels / Writer, or let the nightly routine top this up."
        items={groups.queued} onChanged={replaceItem} />
      <Section title="WORKSHOP — EDIT & SHIP" empty="Approve a queued draft to bring it here, then refine the text before posting."
        items={groups.workshop} onChanged={replaceItem} />
      <Section title="SHIPPED" empty="Nothing posted yet — first one is the hardest."
        items={groups.posted.slice(0, 10)} onChanged={replaceItem} />
      {groups.rejected.length > 0 && (
        <Section title="REJECTED" empty="" items={groups.rejected} onChanged={replaceItem} />
      )}
    </div>
  )
}

function Meter({ label, value, target }) {
  return (
    <div>
      <p className="font-label-caps text-[10px] text-on-surface-variant">{label}</p>
      <p className="font-h2 text-h2 text-primary">
        {value}<span className="text-on-surface-variant text-body font-body"> / {target}</span>
      </p>
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div>
      <p className="font-label-caps text-[10px] text-on-surface-variant">{label}</p>
      <p className="font-h2 text-h2 text-on-surface">{value}</p>
    </div>
  )
}

function Section({ title, empty, items, onChanged }) {
  return (
    <section>
      <h2 className="font-label-caps text-label-caps text-on-surface-variant mb-3">
        {title} <span className="text-primary">({items.length})</span>
      </h2>
      {items.length === 0 ? (
        <p className="font-body text-body text-on-surface-variant italic">{empty}</p>
      ) : (
        <div className="flex flex-col gap-3">
          {items.map(it => <PipelineCard key={it.key} item={it} onChanged={onChanged} />)}
        </div>
      )}
    </section>
  )
}

function PipelineCard({ item, onChanged }) {
  const [expanded, setExpanded] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const [text, setText] = useState(item.generated_text || "")
  const [rejecting, setRejecting] = useState(false)
  const [reason, setReason] = useState("")
  const [history, setHistory] = useState(null)
  const [loadingHistory, setLoadingHistory] = useState(false)

  const isReel = item.channel === "reel"
  const status = item.status || "queued"
  const patchMeta = isReel ? patchReelScriptMeta : patchDraftMeta
  const patchText = isReel ? patchReelScript : patchDraft
  const pkg = isReel ? postReelPackage : postDraftPackage

  const editable = status === "queued" || status === "approved" || status === "recorded"
  const dirty = text !== (item.generated_text || "")

  async function run(fn) {
    setBusy(true); setErr(null)
    try { await fn() } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  const meta = (fields) => run(async () => {
    const updated = await patchMeta(item.id, fields)
    onChanged(updated, item.channel)
  })

  const saveText = () => run(async () => {
    const updated = await patchText(item.id, text)
    onChanged(updated, item.channel)
  })

  const confirmReject = () => {
    run(async () => {
      const fields = { status: "killed", verdict: -1 }
      if (reason.trim()) fields.verdict_note = reason.trim()
      const updated = await patchMeta(item.id, fields)
      onChanged(updated, item.channel)
      setRejecting(false)
    })
  }

  const makePackage = () => run(async () => {
    const res = await pkg(item.id)
    onChanged({ id: item.id, caption: res.caption, cta: res.cta }, item.channel)
  })

  const toggleHistory = () => run(async () => {
    if (history) { setHistory(null); return }
    setLoadingHistory(true)
    try {
      const versions = await fetchReelScriptVersions(item.id)
      setHistory(versions.filter(v => v.id !== item.id))
    } finally {
      setLoadingHistory(false)
    }
  })

  function copyPost() {
    const parts = [item.generated_text]
    if (item.caption) parts.push("", item.caption)
    if (item.cta) parts.push("", item.cta)
    navigator.clipboard.writeText(parts.join("\n"))
  }

  return (
    <GlassPanel className="rounded-xl hover:border-primary/20 transition-all">
      <div className="p-card_padding">
        {/* Header row */}
        <div className="flex items-center gap-3">
          <span className={`font-label-caps text-[10px] px-2 py-1 rounded border shrink-0 ${
            isReel ? "text-secondary bg-secondary/5 border-secondary/20" : "text-primary bg-primary/5 border-primary/20"
          }`}>
            {isReel ? "REEL" : "LINKEDIN"} #{item.id}
          </span>
          {isReel && item.version > 1 && (
            <span className="font-label-caps text-[10px] px-2 py-1 rounded border shrink-0 text-on-surface-variant bg-black/5 border-black/10">
              v{item.version}
            </span>
          )}
          {isReel && item.tier && (
            <span className="font-label-caps text-[10px] px-2 py-1 rounded border shrink-0 text-secondary bg-secondary/5 border-secondary/20">
              {item.tier}
            </span>
          )}
          <button onClick={() => setExpanded(e => !e)} className="flex-1 min-w-0 text-left">
            <p className="font-body text-body text-on-surface line-clamp-1">
              {(item.generated_text || "").slice(0, 120) || "—"}
            </p>
            <p className="font-label-caps text-[10px] text-on-surface-variant mt-1">
              {item.framework_id} · {item.model_used} · {(item.created_at || "").slice(0, 10)}
            </p>
          </button>
          <StatusBadge status={status} />
          <button
            onClick={() => setExpanded(e => !e)}
            className="p-1.5 rounded-lg text-on-surface-variant hover:text-primary transition-colors shrink-0"
          >
            <Icon name={expanded ? "expand_less" : "expand_more"} size={18} />
          </button>
        </div>

        {expanded && (
          <div className="mt-4 border-t border-black/5 pt-4">
            {/* Script: editable in queue/workshop, read-only once posted/rejected */}
            {editable ? (
              <>
                <textarea
                  value={text}
                  onChange={e => setText(e.target.value)}
                  rows={Math.min(20, Math.max(6, text.split("\n").length + 1))}
                  className="w-full glass-panel rounded-lg px-4 py-3 font-body text-body text-on-surface focus:ring-1 focus:ring-primary outline-none border-black/5 resize-y"
                />
                {dirty && (
                  <div className="flex gap-2 mt-2 mb-4">
                    <Action primary disabled={busy} icon="save" label={busy ? "Saving…" : "Save text"} onClick={saveText} />
                    <Action disabled={busy} icon="undo" label="Revert" onClick={() => setText(item.generated_text || "")} />
                  </div>
                )}
                {!dirty && <div className="mb-4" />}
              </>
            ) : (
              <pre className="font-body text-body text-on-surface whitespace-pre-wrap mb-4">{item.generated_text}</pre>
            )}

            {/* Rejection reason shown on rejected cards */}
            {status === "killed" && item.verdict_note && (
              <div className="mb-4 rounded-lg bg-error/5 border border-error/15 p-3">
                <p className="font-label-caps text-[10px] text-error mb-1">REJECTED BECAUSE</p>
                <p className="font-body text-body text-on-surface">{item.verdict_note}</p>
              </div>
            )}

            {/* Caption / CTA */}
            {(item.caption || item.cta) && (
              <div className="mb-4 rounded-lg bg-primary/5 border border-primary/10 p-3">
                <p className="font-label-caps text-[10px] text-on-surface-variant mb-1">CAPTION</p>
                <p className="font-body text-body text-on-surface whitespace-pre-wrap">{item.caption}</p>
                {item.cta && (
                  <>
                    <p className="font-label-caps text-[10px] text-on-surface-variant mt-2 mb-1">CTA</p>
                    <p className="font-body text-body text-on-surface">{item.cta}</p>
                  </>
                )}
              </div>
            )}

            {err && (
              <div className="flex items-center gap-2 text-error font-label-caps text-label-caps mb-3">
                <Icon name="error" size={14} /> {err}
              </div>
            )}

            {/* Version history — prior takes for this idea, read-only */}
            {isReel && (
              <div className="mb-4">
                <Action disabled={loadingHistory} icon={history ? "expand_less" : "history"}
                  label={loadingHistory ? "Loading…" : (history ? "Hide history" : "History")}
                  onClick={toggleHistory} />
                {history && (
                  history.length === 0 ? (
                    <p className="mt-2 font-label-caps text-[10px] text-on-surface-variant italic">
                      No prior versions — this is the only take.
                    </p>
                  ) : (
                    <div className="mt-2 flex flex-col gap-2">
                      {history.map(v => (
                        <div key={v.id} className="rounded-lg border border-black/5 bg-black/[0.02] p-3">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-label-caps text-[10px] text-on-surface-variant">v{v.version}</span>
                            <StatusBadge status={v.status || "queued"} />
                            <span className="font-label-caps text-[10px] text-on-surface-variant">
                              {(v.created_at || "").slice(0, 16)}
                            </span>
                          </div>
                          <p className="font-body text-sm text-on-surface whitespace-pre-wrap line-clamp-3">
                            {v.generated_text}
                          </p>
                        </div>
                      ))}
                    </div>
                  )
                )}
              </div>
            )}

            {/* Reject reason field (two-step) */}
            {rejecting && (
              <div className="mb-3 flex gap-2">
                <input
                  autoFocus
                  type="text"
                  value={reason}
                  onChange={e => setReason(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && confirmReject()}
                  placeholder="Why reject? (optional — feeds the next batch as 'avoid this')"
                  className="flex-1 glass-panel rounded-lg px-3 py-2 font-body text-sm text-on-surface focus:ring-1 focus:ring-error outline-none border-black/5"
                />
                <Action disabled={busy} icon="check" label="Confirm" onClick={confirmReject} />
                <Action disabled={busy} icon="close" label="Cancel" onClick={() => { setRejecting(false); setReason("") }} />
              </div>
            )}

            {/* Actions by state */}
            {!rejecting && (
              <div className="flex flex-wrap gap-2">
                {status === "queued" && (
                  <>
                    <Action primary disabled={busy} icon="check_circle" label="Approve" onClick={() => meta({ status: "approved" })} />
                    <Action disabled={busy} icon="thumb_down" label="Reject" onClick={() => setRejecting(true)} />
                  </>
                )}
                {(status === "approved" || status === "recorded") && (
                  <>
                    {!item.caption && (
                      <Action primary disabled={busy} icon="auto_awesome" label={busy ? "Working…" : "Caption + CTA"} onClick={makePackage} />
                    )}
                    {isReel && status === "approved" && (
                      <Action disabled={busy} icon="videocam" label="Mark recorded" onClick={() => meta({ status: "recorded" })} />
                    )}
                    <Action primary={!!item.caption} disabled={busy} icon="rocket_launch" label="Mark posted" onClick={() => meta({ status: "posted" })} />
                    <Action disabled={busy} icon="content_copy" label="Copy post" onClick={copyPost} />
                    <Action disabled={busy} icon="thumb_down" label="Reject" onClick={() => setRejecting(true)} />
                  </>
                )}
                {status === "posted" && (
                  <Action disabled={busy} icon="content_copy" label="Copy post" onClick={copyPost} />
                )}
                {status === "killed" && (
                  <Action disabled={busy} icon="undo" label="Restore to queue" onClick={() => meta({ status: "queued" })} />
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </GlassPanel>
  )
}

function StatusBadge({ status }) {
  const map = {
    queued:   ["QUEUED",   "text-on-surface-variant bg-black/5 border-black/10"],
    approved: ["WORKSHOP", "text-primary bg-primary/5 border-primary/20"],
    recorded: ["RECORDED", "text-secondary bg-secondary/5 border-secondary/20"],
    posted:   ["POSTED",   "text-on-primary bg-primary border-primary"],
    killed:   ["REJECTED", "text-error bg-error/5 border-error/20"],
  }
  const [label, cls] = map[status] || map.queued
  return (
    <span className={`font-label-caps text-[10px] px-2 py-1 rounded border shrink-0 ${cls}`}>
      {label}
    </span>
  )
}

function Action({ icon, label, onClick, disabled, primary }) {
  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-label-caps text-label-caps border transition-colors disabled:opacity-40 ${
        primary
          ? "bg-primary text-on-primary border-primary hover:bg-primary/90"
          : "text-on-surface-variant border-black/10 hover:text-primary hover:border-primary/20"
      }`}
    >
      <Icon name={icon} size={14} /> {label}
    </motion.button>
  )
}
