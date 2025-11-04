import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import '@/App.css';
import Landing from './pages/Landing';
import Auth from './pages/Auth';
import CitizenDashboard from './pages/CitizenDashboard';
import AuthorityDashboard from './pages/AuthorityDashboard';
import { Toaster } from '@/components/ui/sonner';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for stored auth
    const token = localStorage.getItem('token');
    const userData = localStorage.getItem('user');
    if (token && userData) {
      setUser(JSON.parse(userData));
    }
    setLoading(false);
  }, []);

  const handleLogin = (userData, token) => {
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(userData));
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  }

  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={!user ? <Landing /> : <Navigate to={user.role === 'authority' ? '/authority' : '/dashboard'} />} />
          <Route path="/auth" element={!user ? <Auth onLogin={handleLogin} /> : <Navigate to={user.role === 'authority' ? '/authority' : '/dashboard'} />} />
          <Route 
            path="/dashboard" 
            element={user && user.role === 'citizen' ? <CitizenDashboard user={user} onLogout={handleLogout} /> : <Navigate to="/auth" />} 
          />
          <Route 
            path="/authority" 
            element={user && user.role === 'authority' ? <AuthorityDashboard user={user} onLogout={handleLogout} /> : <Navigate to="/auth" />} 
          />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" />
    </div>
  );
}

export default App;
