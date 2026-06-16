/**
 * DomainChips — controlled pill row for filtering stories by domain.
 * Props:
 *   domains  : string[]          — ordered list of domain values
 *   selected : string | null     — currently active domain (null = All)
 *   onChange : (d: string|null) => void
 */
export default function DomainChips({ domains, selected, onChange }) {
  const all = [null, ...domains]

  return (
    <div className="flex flex-wrap gap-2">
      {all.map((d) => {
        const label = d === null ? "All" : d.charAt(0).toUpperCase() + d.slice(1)
        const active = d === selected
        return (
          <button
            key={d ?? "__all__"}
            onClick={() => onChange(active ? null : d)}
            className={[
              "px-3 py-1 rounded-full font-label-caps text-[10px] transition-colors border",
              active
                ? "bg-primary text-white border-primary"
                : "glass-panel text-on-surface-variant hover:text-primary hover:border-primary/30 border-black/5",
            ].join(" ")}
          >
            {label}
          </button>
        )
      })}
    </div>
  )
}
