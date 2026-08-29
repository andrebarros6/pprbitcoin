import { Routes, Route, Navigate } from 'react-router-dom';
import Calculator from './pages/Calculator';
import Privacy from './pages/Privacy';
import Terms from './pages/Terms';

/**
 * Application routes.
 *
 * The legal pages are served at both the Portuguese paths (shown in the UI)
 * and the conventional English ones, since /privacy and /terms are what
 * external reviewers and app stores tend to look for.
 */
function App() {
  return (
    <Routes>
      <Route path="/" element={<Calculator />} />
      <Route path="/privacidade" element={<Privacy />} />
      <Route path="/termos" element={<Terms />} />
      <Route path="/privacy" element={<Navigate to="/privacidade" replace />} />
      <Route path="/terms" element={<Navigate to="/termos" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
