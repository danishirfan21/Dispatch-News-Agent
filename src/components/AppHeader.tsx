import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useAutoHideHeader } from '../hooks/useAutoHideHeader'

type NavItem = {
  label: string
  to: string
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Your Brief', to: '/brief' },
  { label: 'Watching', to: '/watching' },
  { label: 'Setup', to: '/setup' },
]

export function AppHeader() {
  const { visible, headerInteractionProps } = useAutoHideHeader()
  const location = useLocation()
  const navigate = useNavigate()
  const { logout } = useAuth()

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <header
      {...headerInteractionProps}
      className={`fixed top-0 w-full z-50 bg-surface/90 backdrop-blur-md shadow-[0_1px_8px_rgba(0,0,0,0.04)] transition-transform duration-200 ease-in-out will-change-transform ${
        visible ? 'translate-y-0' : '-translate-y-full'
      }`}
    >
      <div className="h-20 max-w-[1440px] mx-auto px-margin-mobile md:px-margin-tablet lg:px-margin flex items-center justify-between gap-6">
        <span className="font-serif text-headline-sm text-on-surface tracking-tight uppercase leading-none">
          DISPATCH
        </span>

        <nav className="flex items-center gap-1 bg-surface-container-low p-1 rounded-xl overflow-x-auto max-w-[70vw] sm:max-w-none">
          {NAV_ITEMS.map((item) => {
            const isActive =
              location.pathname === item.to || location.pathname.startsWith(`${item.to}/`)

            return (
              <Link
                key={item.to}
                to={item.to}
                aria-current={isActive ? 'page' : undefined}
                className={
                  isActive
                    ? 'px-4 py-1 rounded-lg transition-all text-on-surface bg-surface-container font-semibold font-sans text-label-md'
                    : 'px-4 py-1 rounded-lg transition-all text-on-surface-variant hover:text-on-surface hover:bg-surface-container font-sans text-label-md'
                }
              >
                {item.label}
              </Link>
            )
          })}
        </nav>

        <button
          type="button"
          onClick={handleLogout}
          className="px-4 py-1 rounded-lg font-sans text-label-md text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low transition-colors cursor-pointer"
        >
          Log out
        </button>
      </div>
    </header>
  )
}
