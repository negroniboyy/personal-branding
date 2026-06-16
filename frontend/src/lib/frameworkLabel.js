export function frameworkLabel(fw, channel) {
  const title = (channel === "reel" ? fw.source_file : fw.name) || fw.id
  const tag = fw.id
  const tail = channel === "reel"
    ? [fw.hook_type, fw.pacing, fw.cta_type]
    : [fw.hook_type, fw.tone, fw.cta]
  const meta = tail
    .filter(Boolean)
    .map(s => s.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()))
    .join(" · ")
  const base = tag && tag !== title ? `${title} (${tag})` : title
  return meta ? `${base} — ${meta}` : base
}
