import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { ProtectedRoute } from './components/ProtectedRoute'
import { BriefRoute } from './screens/BriefRoute'
import { LoginScreen } from './screens/LoginScreen'
import { OnboardingScreen } from './screens/OnboardingScreen'
import { RegisterScreen } from './screens/RegisterScreen'
import { SetupScreen } from './screens/SetupScreen'
import { WatchDetailScreen } from './screens/WatchDetailScreen'
import { WatchingScreen } from './screens/WatchingScreen'

function App() {
  return (
    <Routes>
      <Route path="/welcome" element={<OnboardingScreen />} />
      <Route path="/login" element={<LoginScreen />} />
      <Route path="/register" element={<RegisterScreen />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/setup" replace />} />
          <Route path="/setup" element={<SetupScreen />} />
          <Route path="/brief" element={<BriefRoute />} />
          <Route path="/watching" element={<WatchingScreen />} />
          <Route path="/watching/:id" element={<WatchDetailScreen />} />
          <Route path="*" element={<Navigate to="/setup" replace />} />
        </Route>
      </Route>
    </Routes>
  )
}

export default App
