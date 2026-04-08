import React from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Store, 
  Users, 
  Target, 
  Settings, 
  Database, 
  Star,
  LogOut,
  ShieldCheck,
  ChevronRight
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const AdminLayout: React.FC = () => {
  const { profile: user, handleSignOut: logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const navItems = [
    { to: '/admin', icon: LayoutDashboard, label: 'Dashboard', end: true },
    { to: '/admin/stores', icon: Store, label: 'Store Management' },
    { to: '/admin/employees', icon: Users, label: 'Employee Management' },
    { to: '/admin/targets', icon: Target, label: 'Weekly Targets' },
    { to: '/admin/config', icon: Settings, label: 'System Configuration' },
    { to: '/admin/data', icon: Database, label: 'Raw Data & Exports' },
    { to: '/admin/ratings', icon: Star, label: 'Rating Management' },
  ];

  return (
    <div className="flex h-screen bg-[#f0f2f5] font-sans">
      {/* Sidebar */}
      <aside className="w-64 bg-[#1a2332] text-white flex flex-col shadow-xl z-20">
        <div className="p-6 border-b border-slate-700 flex items-center gap-3">
          <div className="bg-orange-500 p-2 rounded-lg">
            <ShieldCheck className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-xl tracking-tight">PerformIQ</h1>
            <span className="text-[10px] uppercase tracking-[0.2em] text-orange-400 font-semibold">Admin Panel</span>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto py-6 px-4 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `
                flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group
                ${isActive 
                  ? 'bg-orange-500 text-white shadow-lg shadow-orange-500/20' 
                  : 'text-slate-400 hover:bg-slate-800 hover:text-white'}
              `}
            >
              <item.icon className="w-5 h-5" />
              <span className="font-medium">{item.label}</span>
              <ChevronRight className={`ml-auto w-4 h-4 transition-transform ${item.to === window.location.pathname ? 'rotate-90' : 'opacity-0 group-hover:opacity-100'}`} />
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-slate-700">
          <div className="bg-slate-800/50 rounded-2xl p-4 mb-4">
            <div className="flex items-center gap-3 mb-1">
              <div className="w-8 h-8 rounded-full bg-orange-500 flex items-center justify-center text-xs font-bold uppercase">
                {user?.name?.[0] || 'A'}
              </div>
              <div className="overflow-hidden">
                <p className="text-sm font-semibold truncate">{user?.name || 'Administrator'}</p>
                <p className="text-[10px] text-slate-400 truncate">{user?.email}</p>
              </div>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-4 py-3 text-slate-400 hover:text-red-400 hover:bg-red-400/10 rounded-xl transition-all duration-200"
          >
            <LogOut className="w-5 h-5" />
            <span className="font-medium">Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto relative bg-[#f0f2f5]">
        <header className="sticky top-0 z-10 bg-white/80 backdrop-blur-md border-b border-slate-200 px-8 py-4 flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-800 uppercase tracking-wide">
            {navItems.find(item => window.location.pathname === item.to || (item.to !== '/admin' && window.location.pathname.startsWith(item.to)))?.label || 'Dashboard'}
          </h2>
          <div className="flex items-center gap-4">
            <div className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-bold border border-green-200 flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
              SYSTEM ACTIVE
            </div>
          </div>
        </header>

        <div className="p-8 max-w-[1600px] mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default AdminLayout;
