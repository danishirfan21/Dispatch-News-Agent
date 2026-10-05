import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { hasSeenOnboarding } from '../utils/onboarding'

export function ProtectedRoute() {
  const { user, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) return null

  if (!user) {
    const destination = hasSeenOnboarding() ? '/login' : '/welcome'
    return <Navigate to={destination} replace state={{ from: location.pathname }} />
  }

  return <Outlet />
}
