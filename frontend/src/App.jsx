import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './Login';
import Chat from './Chat';
import Admin from './Admin';
import Help from './Help';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/login" element={<Login />} />
      <Route path="/chat" element={<Chat />} />
      <Route path="/admin" element={<Admin />} />
      <Route path="/help" element={<Help />} />
    </Routes>
  );
}

export default App;
