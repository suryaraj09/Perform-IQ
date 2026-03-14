import { BrowserRouter, Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { Sun, Moon, LayoutDashboard, Receipt, ShoppingBag, Trophy, Clock, ClipboardCheck, Users, Grid3X3, LogOut } from 'lucide-react';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './pages/auth/Login';
import EmployeeDashboard from './pages/employee/Dashboard';
import RecordSale from './pages/employee/RecordSale';
import MySales from './pages/employee/MySales';
import Leaderboard from './pages/employee/Leaderboard';
import Attendance from './pages/employee/Attendance';
import ManagerDashboard from './pages/manager/Dashboard';
import ReviewQueue from './pages/manager/ReviewQueue';
import Clustering from './pages/manager/Clustering';
import Heatmap from './pages/manager/Heatmap';
import PendingApproval from './pages/auth/PendingApproval';
import './index.css';

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}

function AppRoutes() {
  const { profile, loading, handleSignOut } = useAuth();

  const [theme, setTheme] = useState<'dark' | 'light'>(() =>
    (localStorage.getItem('theme') as 'dark' | 'light') || 'light'
  );

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark');

  // Show loading spinner while auth state is resolving
  if (loading) {
    return (
      <div className="auth-page" style={{ justifyContent: 'center' }}>
        <div className="auth-logo">
          <div className="auth-logo-icon" style={{ animation: 'pulse 1.5s ease infinite' }}>
            <span style={{ fontSize: 28, fontWeight: 800 }}>PQ</span>
          </div>
          <p style={{ marginTop: 16, color: 'var(--text-muted)' }}>Loading...</p>
        </div>
      </div>
    );
  }

  // Not authenticated → show login
  if (!profile) {
    return (
      <Routes>
        <Route path="*" element={<Login />} />
      </Routes>
    );
  }

  // Pending approval → show pending screen
  if (profile.status === 'pending') {
    return <PendingApproval />;
  }

  const role = profile.role;
  const employeeId = profile.id;

  const employeeLinks = [
    { to: '/employee/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/employee/record-sale', icon: Receipt, label: 'Record Sale' },
    { to: '/employee/my-sales', icon: ShoppingBag, label: 'My Sales' },
    { to: '/employee/leaderboard', icon: Trophy, label: 'Leaderboard' },
    { to: '/employee/attendance', icon: Clock, label: 'Attendance' },
  ];

  const managerLinks = [
    { to: '/manager/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/manager/review-queue', icon: ClipboardCheck, label: 'Review Queue' },
    { to: '/manager/clustering', icon: Users, label: 'Clustering' },
    { to: '/manager/heatmap', icon: Grid3X3, label: 'Heatmap' },
  ];

  const links = role === 'employee' ? employeeLinks : managerLinks;
  const defaultRoute = role === 'employee' ? '/employee/dashboard' : '/manager/dashboard';

  return (
    <div className="app-layout">
      {/* Sidebar */}
      <aside className={`sidebar ${role === 'manager' ? 'sidebar-manager' : 'sidebar-employee'}`}>
        <div className="sidebar-logo">
          <div className="logo-icon">PQ</div>
          <h1>PerformIQ</h1>
        </div>

        {/* User info */}
        <div className="sidebar-user-info">
          <div className="sidebar-user-avatar">
            {profile.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)}
          </div>
          <div className="sidebar-user-details">
            <div className="sidebar-user-name">{profile.name}</div>
            <div className="sidebar-user-role">{role === 'manager' ? '👔 Manager' : `⚡ Lv${profile.level} ${profile.level_title}`}</div>
          </div>
        </div>

        <nav className="sidebar-nav">
          {links.map(link => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
            >
              <link.icon />
              <span>{link.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Sign Out */}
        <div style={{ padding: '12px', marginTop: 'auto' }}>
          <button className="sidebar-link" onClick={handleSignOut} style={{ width: '100%', border: 'none', background: 'none' }}>
            <LogOut size={20} />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <div className="top-bar">
          <PageTitle />
          <div className="top-bar-actions">
            <button className="theme-toggle" onClick={toggleTheme} title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}>
              {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
            </button>
          </div>
        </div>

        <Routes>
          {/* Employee Routes */}
          {role === 'employee' && (
            <>
              <Route path="/employee/dashboard" element={<EmployeeDashboard employeeId={employeeId} />} />
              <Route path="/employee/record-sale" element={<RecordSale employeeId={employeeId} />} />
              <Route path="/employee/my-sales" element={<MySales employeeId={employeeId} />} />
              <Route path="/employee/leaderboard" element={<Leaderboard />} />
              <Route path="/employee/attendance" element={<Attendance employeeId={employeeId} />} />
            </>
          )}

          {/* Manager Routes */}
          {role === 'manager' && (
            <>
              <Route path="/manager/dashboard" element={<ManagerDashboard />} />
              <Route path="/manager/review-queue" element={<ReviewQueue />} />
              <Route path="/manager/clustering" element={<Clustering />} />
              <Route path="/manager/heatmap" element={<Heatmap />} />
            </>
          )}

          {/* Default redirect based on role */}
          <Route path="*" element={<Navigate to={defaultRoute} replace />} />
        </Routes>
      </main>
    </div>
  );
}

function PageTitle() {
  const location = useLocation();
  const titles: Record<string, string> = {
    '/employee/dashboard': 'Dashboard',
    '/employee/record-sale': 'Record Sale',
    '/employee/my-sales': 'My Sales',
    '/employee/leaderboard': 'Leaderboard',
    '/employee/attendance': 'Attendance',
    '/manager/dashboard': 'Command Center',
    '/manager/review-queue': 'Review Queue',
    '/manager/clustering': 'Employee Clustering',
    '/manager/heatmap': 'Correlation Heatmap',
  };
  return <h2>{titles[location.pathname] || 'PerformIQ'}</h2>;
}

export default App;
