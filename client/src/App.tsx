import { BrowserRouter, Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom';
import { useState, useEffect, useCallback } from 'react';
import { Sun, Moon, LayoutDashboard, Receipt, ShoppingBag, Trophy, Clock, ClipboardCheck, Users, Grid3X3, LogOut, Flag, TrendingUp } from 'lucide-react';
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
import FlaggedSales from './pages/manager/FlaggedSales';
import GlobalLeaderboard from './pages/HeadOfficeAnalytics/WarehouseLeaderboard';
import DepartmentAnalysis from './pages/HeadOfficeAnalytics/WarehouseDepartments';
import WarehouseOverview from './pages/HeadOfficeAnalytics/WarehouseOverview';
import WarehouseTrends from './pages/HeadOfficeAnalytics/WarehouseTrends';
import HeadOfficeAlerts from './pages/HeadOfficeAnalytics/HeadOfficeAlerts';
import StoreDrillDown from './pages/HeadOfficeAnalytics/StoreDrillDown';
import { Store, BarChart3, Globe, AlertCircle } from 'lucide-react';
import PendingApproval from './pages/auth/PendingApproval';
import AdminLayout from './layouts/AdminLayout';
import AdminDashboard from './pages/admin/Dashboard';
import StoreManagement from './pages/admin/StoreManagement';
import EmployeeManagement from './pages/admin/EmployeeManagement';
import WeeklyTargets from './pages/admin/WeeklyTargets';
import SystemConfig from './pages/admin/SystemConfig';
import DataExports from './pages/admin/DataExports';
import RatingManagement from './pages/admin/RatingManagement';
import WarehouseLayout from './layouts/WarehouseLayout';
import WHStoreSummary from './pages/warehouse/WHStoreSummary';
import WHEmployeeFacts from './pages/warehouse/WHEmployeeFacts';
import WHDeptBenchmark from './pages/warehouse/WHDeptBenchmark';
import WHFlagSummary from './pages/warehouse/WHFlagSummary';
import WHEtlRuns from './pages/warehouse/WHEtlRuns';
import AccessDenied from './pages/warehouse/AccessDenied';
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
  const { profile, role, loading, activeStoreId, setActiveStoreId, storeName, handleSignOut } = useAuth();

  const [theme, setTheme] = useState<'dark' | 'light'>(() =>
    (localStorage.getItem('theme') as 'dark' | 'light') || 'light'
  );

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark');

  // Flagged sales badge count for manager nav
  const [flaggedCount, setFlaggedCount] = useState(0);
  const fetchFlaggedCount = useCallback(async () => {
    if (!profile) return;
    try {
      if (profile.role === 'manager') {
        const res = await fetch('http://localhost:8000/api/admin/flagged-sales');
        const data = await res.json();
        setFlaggedCount(Array.isArray(data) ? data.length : 0);
      } else if (profile.role === 'HEAD_OFFICE') {
        const res = await fetch('http://localhost:8000/api/headoffice/alerts');
        const data = await res.json();
        setFlaggedCount(data.total_unresolved || 0);
      }
    } catch { /* silent */ }
  }, [profile]);

  useEffect(() => {
    fetchFlaggedCount();
    const interval = setInterval(fetchFlaggedCount, 60000);
    return () => clearInterval(interval);
  }, [fetchFlaggedCount]);

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
    { to: '/manager/flagged-sales', icon: Flag, label: 'Flagged Sales', badge: flaggedCount },
    { to: '/manager/clustering', icon: Users, label: 'Clustering' },
    { to: '/manager/heatmap', icon: Grid3X3, label: 'Heatmap' },
  ];

  const headOfficeLinks = [
    { to: '/headoffice/dashboard', icon: LayoutDashboard, label: 'Warehouse Overview' },
    { to: '/headoffice/trends', icon: TrendingUp, label: 'Network Trends' },
    { to: '/headoffice/departments', icon: BarChart3, label: 'Department Analysis' },
    { to: '/headoffice/leaderboard', icon: Globe, label: 'Global Rankings' },
    { to: '/headoffice/alerts', icon: AlertCircle, label: 'Network Alerts', badge: flaggedCount },
  ];

  const links = role === 'employee' ? employeeLinks : (role === 'HEAD_OFFICE' ? headOfficeLinks : managerLinks);
  const defaultRoute = role === 'employee' ? '/employee/dashboard' : (role === 'HEAD_OFFICE' ? '/headoffice/dashboard' : '/manager/dashboard');

  const location = useLocation();
  const isAdminPortalPath = location.pathname.startsWith('/admin-portal');
  const isAdminPath = location.pathname.startsWith('/admin') && !isAdminPortalPath;

  // Access denied route — always accessible
  if (location.pathname === '/access-denied') {
    return (
      <Routes>
        <Route path="/access-denied" element={<AccessDenied />} />
      </Routes>
    );
  }

  // Branch for Data Warehouse Portal (/admin-portal)
  if (isAdminPortalPath) {
    if (role !== 'HEAD_OFFICE') {
      return (
        <Routes>
          <Route path="*" element={<Navigate to="/access-denied" replace />} />
        </Routes>
      );
    }
    return (
      <Routes>
        <Route path="/admin-portal" element={<WarehouseLayout />}>
          <Route index element={<WHStoreSummary />} />
          <Route path="employees" element={<WHEmployeeFacts />} />
          <Route path="benchmarks" element={<WHDeptBenchmark />} />
          <Route path="flags" element={<WHFlagSummary />} />
          <Route path="etl" element={<WHEtlRuns />} />
        </Route>
        <Route path="*" element={<Navigate to="/admin-portal" replace />} />
      </Routes>
    );
  }

  // Branch for Admin Panel
  if (isAdminPath && role === 'HEAD_OFFICE') {
    return (
      <Routes>
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<AdminDashboard />} />
          <Route path="stores" element={<StoreManagement />} />
          <Route path="employees" element={<EmployeeManagement />} />
          <Route path="targets" element={<WeeklyTargets />} />
          <Route path="config" element={<SystemConfig />} />
          <Route path="data" element={<DataExports />} />
          <Route path="ratings" element={<RatingManagement />} />
        </Route>
        <Route path="*" element={<Navigate to="/admin" replace />} />
      </Routes>
    );
  }

  return (
    <div className="app-layout">
      {/* Sidebar */}
      <aside className={`sidebar ${role !== 'employee' ? 'sidebar-manager' : 'sidebar-employee'}`}>
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
            <div className="sidebar-user-role">
                {role === 'HEAD_OFFICE' ? '🏢 Head Office' : role === 'manager' ? '👔 Store Manager' : `⚡ Lv${profile.level} ${profile.level_title}`}
            </div>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: 2, display: 'flex', alignItems: 'center', gap: 4 }}>
                <Store size={10} /> Blue Buddha {storeName || '...'}
            </div>
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
              {'badge' in link && (link as any).badge > 0 && (
                <span style={{
                  marginLeft: 'auto', background: '#ef4444', color: '#fff',
                  borderRadius: 10, padding: '1px 7px', fontSize: '0.7rem', fontWeight: 700,
                  minWidth: 18, textAlign: 'center',
                }}>{(link as any).badge}</span>
              )}
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
          <div className="top-bar-actions" style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            {role === 'HEAD_OFFICE' && (
              <div className="store-selector-container" style={{ position: 'relative' }}>
                <select 
                  className="theme-toggle" 
                  style={{ width: 'auto', padding: '0 12px', fontSize: '0.85rem' }}
                  value={activeStoreId || ''}
                  onChange={(e) => setActiveStoreId(e.target.value)}
                >
                  <option value="S001">Navrangpura (S001)</option>
                  <option value="S002">Satellite (S002)</option>
                  <option value="S003">Bopal (S003)</option>
                </select>
              </div>
            )}
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
              <Route path="/employee/attendance" element={<Attendance employeeId={employeeId} employeeName={profile.name} />} />
            </>
          )}

          {/* Manager & HO Routes */}
          {(role === 'manager' || role === 'HEAD_OFFICE') && (
            <>
              <Route path="/manager/dashboard" element={<ManagerDashboard />} />
              <Route path="/manager/review-queue" element={<ReviewQueue />} />
              <Route path="/manager/flagged-sales" element={<FlaggedSales />} />
              <Route path="/manager/clustering" element={<Clustering />} />
              <Route path="/manager/heatmap" element={<Heatmap />} />
            </>
          )}

          {/* Head Office Specific Pages */}
          {role === 'HEAD_OFFICE' && (
            <>
              <Route path="/headoffice/dashboard" element={<WarehouseOverview />} />
              <Route path="/headoffice/trends" element={<WarehouseTrends />} />
              <Route path="/headoffice/leaderboard" element={<GlobalLeaderboard />} />
              <Route path="/headoffice/departments" element={<DepartmentAnalysis />} />
              <Route path="/headoffice/alerts" element={<HeadOfficeAlerts />} />
              <Route path="/headoffice/store/:storeId" element={<StoreDrillDown />} />
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
    '/manager/flagged-sales': 'Flagged Sales',
    '/manager/clustering': 'Employee Clustering',
    '/manager/heatmap': 'Correlation Heatmap',
  };
  return <h2>{titles[location.pathname] || 'PerformIQ'}</h2>;
}

export default App;
