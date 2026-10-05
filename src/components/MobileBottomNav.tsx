import { Link, useLocation } from 'react-router-dom'

type BottomNavItem = {
  label: string
  to: string
  icon: string
}

const BOTTOM_NAV_ITEMS: BottomNavItem[] = [
  { label: 'Brief', to: '/brief', icon: 'article' },
  { label: 'Watching', to: '/watching', icon: 'visibility' },
  { label: 'Setup', to: '/setup', icon: 'tune' },
]

export function MobileBottomNav() {
  const location = useLocation()

  return (
    <nav
      aria-label="Primary"
      className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-surface/95 backdrop-blur-md border-t border-surface-container pb-[env(safe-area-inset-bottom)]"
    >
      <div className="flex items-stretch justify-around">
        {BOTTOM_NAV_ITEMS.map((item) => {
          const isActive =
            location.pathname === item.to || location.pathname.startsWith(`${item.to}/`)

          return (
            <Link
              key={item.to}
              to={item.to}
              aria-current={isActive ? 'page' : undefined}
              className={`flex flex-col items-center justify-center gap-0.5 flex-1 min-h-[56px] py-2 transition-colors ${
                isActive
                  ? 'text-secondary bg-secondary-fixed/50'
                  : 'text-on-surface-variant'
              }`}
            >
              <span className="material-symbols-outlined text-[22px]" aria-hidden="true">
                {item.icon}
              </span>
              <span className="font-sans text-label-sm">{item.label}</span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
