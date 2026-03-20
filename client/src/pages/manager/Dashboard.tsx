import { useApi } from '../../hooks/useApi';
import { useSSE } from '../../hooks/useSSE';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { IndianRupee, Users, Target, ClipboardCheck, Bell, UserPlus, CheckCircle2, XCircle } from 'lucide-react';
import { useState } from 'react';

interface ManagerDashboardData {
    summary: { total_revenue: number; active_employees: number; avg_target_achievement: number; pending_reviews: number };
    departments: Array<{ id: number; name: string; weekly_revenue: number; weekly_revenue_target: number; employee_count: number; target_achievement: number }>;
    review_queue: { total: number; sales: Array<{ id: number; employee_name: string; revenue: number; submitted_at: string }>; downloads: unknown[] };
    attendance: Array<{ id: number; name: string; department_name: string; punch_in_time: string | null; punch_out_time: string | null; hours_worked: number | null }>;
}

interface PendingEmployee {
    id: number;
    name: string;
    email: string;
    role: string;
    department_name: string;
    store_name: string;
    created_at: string;
}

export default function ManagerDashboard() {
    const { data, loading, refetch } = useApi<ManagerDashboardData>('/api/dashboard/manager');
    const { data: pendingEmployees, refetch: refetchPending } = useApi<PendingEmployee[]>('/api/manager/pending-employees');
    const { alerts } = useSSE();
    const [actionLoading, setActionLoading] = useState<number | null>(null);

    const handleReview = async (employeeId: number, status: 'approved' | 'rejected') => {
        setActionLoading(employeeId);
        try {
            await fetch(`http://localhost:8000/api/manager/employees/${employeeId}/review`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status, reviewer_id: 1 })
            });
            await refetchPending();
            await refetch();
        } catch (err) {
            console.error('Failed to review employee', err);
        } finally {
            setActionLoading(null);
        }
    };

    if (loading || !data) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Loading manager dashboard...</div>;

    const { summary, departments, attendance } = data;
    const presentCount = attendance.filter(a => a.punch_in_time).length;

    const COLORS = ['#3B82F6', '#60A5FA', '#93C5FD', '#BFDBFE'];

    return (
        <div className="animate-in">
            {/* Command Center Banner */}
            <div style={{
                background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(96, 165, 250, 0.08))',
                border: '1px solid rgba(59, 130, 246, 0.2)',
                borderRadius: 16, padding: '20px 24px', marginBottom: 24,
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
                <div>
                    <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: 4 }}>
                        🏢 Store Command Center
                    </h3>
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        Real-time overview · {new Date().toLocaleDateString('en-IN', { weekday: 'long', month: 'long', day: 'numeric' })}
                    </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--success)' }}>{presentCount}</div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>On Floor</div>
                    </div>
                    <div style={{ width: 1, height: 32, background: 'var(--border)' }} />
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--danger)' }}>{attendance.length - presentCount}</div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Absent</div>
                    </div>
                </div>
            </div>

            {/* KPI Cards */}
            <div className="stats-grid">
                <div className="stat-card">
                    <div className="stat-icon" style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#3B82F6' }}><IndianRupee size={20} /></div>
                    <div className="stat-value">₹{(summary.total_revenue / 100000).toFixed(1)}L</div>
                    <div className="stat-label">Weekly Revenue</div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon" style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#3B82F6' }}><Users size={20} /></div>
                    <div className="stat-value">{summary.active_employees}</div>
                    <div className="stat-label">Active Employees</div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon" style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#3B82F6' }}><Target size={20} /></div>
                    <div className="stat-value">{summary.avg_target_achievement}%</div>
                    <div className="stat-label">Avg Target Achievement</div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon" style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#3B82F6' }}><ClipboardCheck size={20} /></div>
                    <div className="stat-value">{summary.pending_reviews}</div>
                    <div className="stat-label">Pending Reviews</div>
                </div>
            </div>

            <div className="dashboard-grid">
                {/* Department Revenue Chart */}
                <div className="card">
                    <div className="card-header">
                        <span className="card-title">Department Revenue vs Target</span>
                    </div>
                    <div className="chart-container">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={departments} layout="vertical">
                                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                                <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}K`} />
                                <YAxis type="category" dataKey="name" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} width={100} />
                                <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, color: 'var(--text-primary)' }} formatter={(v: any) => [`₹${Number(v).toLocaleString()}`, '']} />
                                <Bar dataKey="weekly_revenue" fill="#F97316" radius={[0, 6, 6, 0]} name="Revenue" />
                                <Bar dataKey="weekly_revenue_target" fill="var(--border)" radius={[0, 6, 6, 0]} name="Target" opacity={0.5} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Target Achievement Donut */}
                <div className="card">
                    <div className="card-header">
                        <span className="card-title">Target Achievement by the Store</span>
                    </div>
                    <div className="chart-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie data={departments} cx="50%" cy="50%" innerRadius={60} outerRadius={100} dataKey="target_achievement" nameKey="name" label={({ name, value }) => `${name}: ${value}%`}>
                                    {departments.map((_entry, i) => (
                                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, color: 'var(--text-primary)' }} />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            <div className="dashboard-grid">
                {/* Attendance Overview */}
                <div className="card">
                    <div className="card-header">
                        <span className="card-title">Today's Attendance ({presentCount}/{attendance.length} present)</span>
                    </div>
                    <div style={{ maxHeight: 300, overflowY: 'auto' }}>
                        {attendance.map(emp => (
                            <div key={emp.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
                                <div>
                                    <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{emp.name}</span>
                                    <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginLeft: 8 }}>{emp.department_name}</span>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                    {emp.punch_in_time ? (
                                        <>
                                            <span style={{ width: 8, height: 8, borderRadius: '50%', background: emp.punch_out_time ? 'var(--text-muted)' : 'var(--success)', display: 'inline-block' }} />
                                            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                                {emp.punch_out_time ? `${emp.hours_worked?.toFixed(1)}h` : 'On Floor'}
                                            </span>
                                        </>
                                    ) : (
                                        <span style={{ fontSize: '0.8rem', color: 'var(--danger)' }}>Absent</span>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Pending Approvals */}
                <div className="card">
                    <div className="card-header">
                        <span className="card-title">
                            <UserPlus size={14} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 6 }} />
                            Pending Approvals ({pendingEmployees?.length || 0})
                        </span>
                    </div>
                    <div style={{ maxHeight: 300, overflowY: 'auto' }}>
                        {pendingEmployees && pendingEmployees.length > 0 ? pendingEmployees.map(emp => (
                            <div key={emp.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px', borderBottom: '1px solid var(--border)' }}>
                                <div>
                                    <div style={{ fontWeight: 600, fontSize: '0.9rem', marginBottom: 2 }}>{emp.name}</div>
                                    <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', display: 'flex', gap: 8 }}>
                                        <span>{emp.email}</span>
                                        <span>•</span>
                                        <span>{emp.department_name}</span>
                                    </div>
                                </div>
                                <div style={{ display: 'flex', gap: 8 }}>
                                    <button 
                                        onClick={() => handleReview(emp.id, 'approved')}
                                        disabled={actionLoading === emp.id}
                                        style={{ background: 'rgba(16, 185, 129, 0.1)', color: 'var(--success)', border: 'none', padding: '6px 12px', borderRadius: 6, display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer', fontSize: '0.8rem', fontWeight: 600 }}
                                    >
                                        <CheckCircle2 size={14} /> Approve
                                    </button>
                                    <button 
                                        onClick={() => handleReview(emp.id, 'rejected')}
                                        disabled={actionLoading === emp.id}
                                        style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', border: 'none', padding: '6px 12px', borderRadius: 6, display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer', fontSize: '0.8rem', fontWeight: 600 }}
                                    >
                                        <XCircle size={14} /> Reject
                                    </button>
                                </div>
                            </div>
                        )) : (
                            <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)' }}>
                                <UserPlus size={32} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
                                <p>No pending employee registrations.</p>
                            </div>
                        )}
                    </div>
                </div>

                {/* Live Alerts */}
                <div className="card">
                    <div className="card-header">
                        <span className="card-title"><Bell size={14} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 6 }} />Live Alerts</span>
                    </div>
                    <div style={{ maxHeight: 300, overflowY: 'auto' }}>
                        {alerts.length > 0 ? alerts.map((alert, i) => (
                            <div key={i} className={`alert-item ${alert.type === 'new_sale' ? 'alert-warning' : 'alert-success'}`}>
                                {alert.message}
                                <span style={{ marginLeft: 'auto', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                                    {new Date(alert.timestamp).toLocaleTimeString()}
                                </span>
                            </div>
                        )) : (
                            <p style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>No recent alerts. Live events will appear here.</p>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
