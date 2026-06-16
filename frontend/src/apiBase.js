// Single source of truth for the backend API origin.
// Override per-environment via Vite env var VITE_API_BASE (see frontend/.env).
export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:9000"
