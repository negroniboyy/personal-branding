export default function GlassPanel({ children, className = "", as: Tag = "div", ...props }) {
  return (
    <Tag className={`glass-panel ${className}`} {...props}>
      {children}
    </Tag>
  )
}
