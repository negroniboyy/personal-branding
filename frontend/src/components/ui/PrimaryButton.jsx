import { motion } from "framer-motion"
import Icon from "./Icon.jsx"

export default function PrimaryButton({ children, onClick, disabled = false, className = "", icon = null }) {
  return (
    <motion.button
      onClick={onClick}
      disabled={disabled}
      whileTap={{ scale: 0.98 }}
      whileHover={{ brightness: 0.95 }}
      className={`
        relative overflow-hidden bg-primary text-on-primary
        py-4 px-6 rounded-xl
        font-label-caps text-label-caps
        flex items-center justify-center gap-2
        transition-all hover:bg-primary/90 hover:shadow-lg
        disabled:opacity-50 disabled:cursor-not-allowed
        ${className}
      `}
    >
      {icon && <Icon name={icon} size={18} />}
      {children}
    </motion.button>
  )
}
