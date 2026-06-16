# Blueprint v1.6 — Frontend Redesign
**State:** v1.5 committed. All API wiring preserved. Replacing visual layer only.

## Affected Files
```
frontend/package.json           — add deps
frontend/vite.config.js         — unchanged (PostCSS auto-detected)
frontend/tailwind.config.js     — NEW
frontend/postcss.config.js      — NEW
frontend/index.html             — add Google Fonts
frontend/src/index.css          — NEW (Tailwind + glass utils)
frontend/src/main.jsx           — import index.css
frontend/src/App.jsx            — layout shell (Sidebar + MobileNav)
frontend/src/components/layout/Sidebar.jsx    — NEW
frontend/src/components/layout/MobileNav.jsx  — NEW
frontend/src/components/ui/GlassPanel.jsx     — NEW
frontend/src/components/ui/PrimaryButton.jsx  — NEW
frontend/src/components/ui/Icon.jsx           — NEW
frontend/src/components/PageList.jsx          — restyle
frontend/src/components/PageDetail.jsx        — restyle
frontend/src/components/NarrativeDashboard.jsx — restyle
frontend/src/components/StoryNodeList.jsx     — restyle
frontend/src/components/StoryNodeCard.jsx     — restyle
frontend/src/components/ContentWriter.jsx     — restyle
frontend/src/components/ReelWriter.jsx        — restyle
```

## Design Tokens (tailwind.config.js)
```
primary: #4648d4, secondary: #8127cf
surface: #f7f9fb, background: #f7f9fb
on-surface: #191c1e, on-surface-variant: #464554
outline: #767586, outline-variant: #c7c4d7
glass: rgba(255,255,255,0.7) + backdrop-blur-[16px]
```

## Module Specs

### layout/Sidebar.jsx — full-height desktop nav
```
Props: activeTab: string, onTabChange: (tab: string) => void
State: hoveredItem: string | null
Renders: fixed left 0, h-screen, w-[300px], flex-col, hidden md:flex
  - Logo: motion.div fadeIn + slideDown on mount
  - NavItem × 4: relative div; framer layoutId="activeNavPill" on active bg
  - Icon: font-variation-settings FILL toggle on hover/active
  - Bottom: Settings + Support links
Key rules: LayoutGroup wraps nav; no router, calls onTabChange
```

### layout/MobileNav.jsx — bottom nav (mobile)
```
Props: activeTab: string, onTabChange: (tab: string) => void
Renders: fixed bottom-0, flex md:hidden, glass-panel
  - 4 items; active gets motion.div scale + colored pill (layoutId="mobileActivePill")
Key rules: pb-safe for notch; z-50
```

### ui/GlassPanel.jsx
```
Props: children, className?: string, as?: string
Renders: applies .glass-panel class + any className
```

### ui/PrimaryButton.jsx
```
Props: children, onClick, disabled, className, icon?: string
Renders: motion.button whileTap scale-[0.98] + hover:brightness
```

### ui/Icon.jsx
```
Props: name: string, fill?: boolean, size?: number, className?: string
Renders: <span class="material-symbols-outlined"> with font-variation-settings FILL toggle
```

## M1 DoD
install deps → tailwind.config + postcss.config → index.css → index.html fonts → main.jsx import → ui primitives → App.jsx glass placeholder → `npm run dev` clean

## M2 DoD
Sidebar + MobileNav → App.jsx shell → framer indicator glides → mobile nav visible on resize

## M3 DoD
Diary (list→detail→back) + Narrative (dashboard + story nodes) styled with glass cards, all API calls untouched

## M4 DoD
ContentWriter canvas (idea hint → recommendations → draft canvas → copy → recent drafts) + ReelWriter (picker → generate → MP4 ingest panel) — all endpoints preserved

## M5 DoD
AnimatePresence tab transitions + loading/error/empty states + polish + `npm run build` clean + checkpoint update
