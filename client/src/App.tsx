import { BrowserRouter, Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { Sun, Moon, LayoutDashboard, Receipt, ShoppingBag, Trophy, Clock, ClipboardCheck, Users, Grid3X3 } from 'lucide-react';
import EmployeeDashboard from './pages/employee/Dashboard';
import RecordSale from './pages/employee/RecordSale';
import MySales from './pages/employee/MySales';
import Leaderboard from './pages/employee/Leaderboard';
import Attendance from './pages/employee/Attendance';
import ManagerDashboard from './pages/manager/Dashboard';
import ReviewQueue from './pages/manager/ReviewQueue';
import Clustering from './pages/manager/Clustering';
import Heatmap from './pages/manager/Heatmap';
import './index.css';

function App() {
  const [theme, setTheme] = useState<'dark' | 'light'>(() =>
    (localStorage.getItem('theme') as 'dark' | 'light') || 'dark'
  );
  const [role, setRole] = useState<'employee' | 'manager'>(() =>
    (localStorage.getItem('role') as 'employee' | 'manager') || 'employee'
  );
  const [employeeId] = useState(1); // Default employee for demo

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem('role', role);
  }, [role]);

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark');

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
    <BrowserRouter>
      <div className="app-layout">
        {/* Sidebar */}
        <aside className="sidebar">
          <div className="sidebar-logo">
            <div className="logo-icon">PQ</div>
            <h1>PerformIQ</h1>
          </div>

          <div className="sidebar-role">
            {role === 'employee' ? '👤 Employee' : '👔 Manager'}
          </div>

          {/* Role Switcher (dev/demo) */}
          <div className="role-switcher">
            <button className={role === 'employee' ? 'active' : ''} onClick={() => setRole('employee')}>
              Employee
            </button>
            <button className={role === 'manager' ? 'active' : ''} onClick={() => setRole('manager')}>
              Manager
            </button>
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
            <Route path="/employee/dashboard" element={<EmployeeDashboard employeeId={employeeId} />} />
            <Route path="/employee/record-sale" element={<RecordSale employeeId={employeeId} />} />
            <Route path="/employee/my-sales" element={<MySales employeeId={employeeId} />} />
            <Route path="/employee/leaderboard" element={<Leaderboard />} />
            <Route path="/employee/attendance" element={<Attendance employeeId={employeeId} />} />

            {/* Manager Routes */}
            <Route path="/manager/dashboard" element={<ManagerDashboard />} />
            <Route path="/manager/review-queue" element={<ReviewQueue />} />
            <Route path="/manager/clustering" element={<Clustering />} />
            <Route path="/manager/heatmap" element={<Heatmap />} />

            {/* Default redirect */}
            <Route path="*" element={<Navigate to={defaultRoute} replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
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
    '/manager/dashboard': 'Manager Dashboard',
    '/manager/review-queue': 'Review Queue',
    '/manager/clustering': 'Employee Clustering',
    '/manager/heatmap': 'Correlation Heatmap',
  };
  return <h2>{titles[location.pathname] || 'PerformIQ'}</h2>;
}

export default App;
