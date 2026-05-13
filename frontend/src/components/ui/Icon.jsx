export default function Icon({ name, fill = false, size = 24, className = "" }) {
  return (
    <span
      className={`material-symbols-outlined ${className}`}
      style={{
        fontSize: size,
        fontVariationSettings: `'FILL' ${fill ? 1 : 0}, 'wght' 400, 'GRAD' 0, 'opsz' ${size}`,
        transition: "font-variation-settings 150ms ease",
      }}
    >
      {name}
    </span>
  )
}
