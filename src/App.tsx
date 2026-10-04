import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { BriefScreen } from './screens/BriefScreen'
import { SetupScreen } from './screens/SetupScreen'
import { WatchDetailScreen } from './screens/WatchDetailScreen'
import { WatchingScreen } from './screens/WatchingScreen'

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/setup" replace />} />
        <Route path="/setup" element={<SetupScreen />} />
        <Route path="/brief" element={<BriefScreen />} />
        <Route path="/watching" element={<WatchingScreen />} />
        <Route path="/watching/:id" element={<WatchDetailScreen />} />
        <Route path="*" element={<Navigate to="/setup" replace />} />
      </Route>
    </Routes>
  )
}

export default App
