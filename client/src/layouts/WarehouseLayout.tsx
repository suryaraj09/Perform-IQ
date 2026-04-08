import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  Database,
  Users,
  BarChart3,
  Flag,
  Activity,
  LogOut,
  ShieldCheck,
  LayoutDashboard,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const WarehouseLayout: React.FC = () => {
  const { profile, handleSignOut } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await handleSignOut();
    navigate('/');
  };

  const navItems = [
    { to: '/admin-portal', icon: LayoutDashboard, label: 'Store Summary', end: true },
    { to: '/admin-portal/employees', icon: Users, label: 'Employee Facts' },
    { to: '/admin-portal/benchmarks', icon: BarChart3, label: 'Dept Benchmarks' },
    { to: '/admin-portal/flags', icon: Flag, label: 'Flag Summary' },
    { to: '/admin-portal/etl', icon: Activity, label: 'ETL Runs' },
  ];

  return (
    <div className="wh-layout">
      {/* Sidebar */}
      <aside className="wh-sidebar">
        <div className="wh-sidebar-header">
          <div className="wh-sidebar-logo-icon">
            <Database size={20} />
          </div>
          <div>
            <h1 className="wh-sidebar-title">PerformIQ</h1>
            <span className="wh-sidebar-subtitle">Data Warehouse</span>
          </div>
        </div>

        <nav className="wh-sidebar-nav">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `wh-sidebar-link ${isActive ? 'active' : ''}`
              }
            >
              <item.icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="wh-sidebar-footer">
          <div className="wh-sidebar-user">
            <div className="wh-sidebar-avatar">
              <ShieldCheck size={16} />
            </div>
            <div className="wh-sidebar-user-info">
              <div className="wh-sidebar-user-name">{profile?.name || 'Admin'}</div>
              <div className="wh-sidebar-user-email">{profile?.email || ''}</div>
            </div>
          </div>
          <button className="wh-sidebar-link wh-logout-btn" onClick={handleLogout}>
            <LogOut size={18} />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="wh-main">
        <Outlet />
      </main>
    </div>
  );
};

export default WarehouseLayout;
