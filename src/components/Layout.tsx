import { Outlet } from 'react-router-dom'
import { AppHeader } from './AppHeader'
import { MobileBottomNav } from './MobileBottomNav'

export function Layout() {
  return (
    <div className="flex flex-col min-h-screen">
      <AppHeader />
      <div className="flex-1 pb-[calc(56px+env(safe-area-inset-bottom))] md:pb-0">
        <Outlet />
      </div>
      <footer className="hidden md:block w-full bg-surface-container-low py-10">
        <div className="max-w-[1440px] mx-auto px-margin-mobile md:px-margin-tablet lg:px-margin flex flex-col md:flex-row items-center justify-between gap-4">
          <span className="font-serif text-headline-sm text-on-surface uppercase">Dispatch</span>
          <span className="font-sans text-label-sm text-on-surface-variant">
            Stories curated around what you follow.
          </span>
        </div>
      </footer>
      <MobileBottomNav />
    </div>
  )
}
