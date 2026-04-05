import { useApi } from '../../hooks/useApi';
import { useSSE } from '../../hooks/useSSE';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line, ScatterChart, Scatter, ZAxis, ReferenceLine } from 'recharts';
import { IndianRupee, Users, Target, ClipboardCheck, Bell, UserPlus, CheckCircle2, XCircle, TrendingUp, TrendingDown, AlertTriangle, Shield } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

// ==================== INTERFACES ====================

interface ManagerDashboardData {
    summary: { total_revenue: number; active_employees: number; avg_target_achievement: number; pending_reviews: number };
    departments: Array<{ id: number; name: string; weekly_revenue: number; weekly_revenue_target: number; employee_count: number; target_achievement: number }>;
    review_queue: { total: number; sales: Array<{ id: number; employee_name: string; revenue: number; submitted_at: string }>; downloads: unknown[] };
    attendance: Array<{ id: number; name: string; department_name: string; punch_in_time: string | null; punch_out_time: string | null; hours_worked: number | null }>;
}

interface PendingEmployee {
    id: number; name: string; email: string; role: string; department_name: string; store_name: string; created_at: string;
}

interface StoreOverview {
    storeId: string; storeName: string;
    currentWeek: {
        weekNumber: number;
        employees: Array<{
            employeeId: string; name: string; department: string;
            pScore: number; M1: number; M2: number; M3: number; M4: number; M5: number; M7: number; M8: number;
            weeklyRevenue: number; weeklyTarget: number; totalBills: number; avgBasketSize: number;
            attendanceRate: number; punctualityScore: number;
        }>;
        storeSummary: {
            avgPScore: number; totalRevenue: number; avgAttendance: number;
            flaggedSalesPending: number; geofenceAlertsPending: number;
            employeesAboveTarget: number; employeesBelowTarget: number;
        };
    };
    weeklyTrend: Array<{ week: string; avgPScore: number; totalRevenue: number; avgAttendance: number }>;
    basketTrend: Array<{ week: string; employees: Array<{ employeeId: string; name: string; avgBasketSize: number }> }>;
    attendanceMatrix: Array<{ employeeId: string; name: string; days: Array<{ date: string; status: string }> }>;
}

interface DeptSummary {
    departments: Array<{
        department: string; avgPScore: number; avgRevenue: number; avgBasketSize: number;
        avgAttendance: number; headcount: number; employeesAboveTarget: number;
    }>;
}

// ==================== HELPERS ====================
const DEPT_COLORS: Record<string, string> = { Apparel: '#185FA5', Electronics: '#3B6D11', Food: '#BA7517' };
const EMP_PALETTE = ['#F97316', '#3B82F6', '#22C55E', '#EAB308', '#8B5CF6', '#EC4899', '#14B8A6', '#F43F5E', '#6366F1', '#06B6D4'];

function getScoreColor(s: number) { return s >= 75 ? '#3B6D11' : s >= 50 ? '#BA7517' : '#A32D2D'; }
function fmtRev(v: number) { return v >= 100000 ? `₹${(v / 100000).toFixed(1)}L` : `₹${(v / 1000).toFixed(1)}K`; }

function ChartLoading() {
    return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200, color: 'var(--text-muted)', fontSize: '0.85rem' }}>Loading chart data...</div>;
}

// ==================== CHART 8: Store Summary Cards ====================
function StoreSummaryCards({ overview }: { overview: StoreOverview }) {
    const nav = useNavigate();
    const s = overview.currentWeek.storeSummary;
    const trend = overview.weeklyTrend;
    const lastWeek = trend.length >= 2 ? trend[trend.length - 2] : null;

    const delta = (curr: number, prev: number | null | undefined) => {
        if (prev == null || prev === 0) return null;
        return +((curr - prev) / prev * 100).toFixed(1);
    };

    const cards = [
        {
            label: 'Avg P Score', value: s.avgPScore.toFixed(1), color: getScoreColor(s.avgPScore),
            delta: lastWeek ? delta(s.avgPScore, lastWeek.avgPScore) : null,
            icon: <Target size={20} />,
        },
        {
            label: 'Store Revenue', value: fmtRev(s.totalRevenue), color: '#F97316',
            delta: lastWeek ? delta(s.totalRevenue, lastWeek.totalRevenue) : null,
            icon: <IndianRupee size={20} />,
        },
        {
            label: 'Avg Attendance', value: `${s.avgAttendance.toFixed(0)}%`, color: s.avgAttendance >= 80 ? '#3B6D11' : '#BA7517',
            delta: lastWeek ? delta(s.avgAttendance, lastWeek.avgAttendance) : null,
            icon: <Users size={20} />,
        },
        {
            label: 'Pending Actions', value: `${s.flaggedSalesPending + s.geofenceAlertsPending}`,
            color: (s.flaggedSalesPending + s.geofenceAlertsPending) > 0 ? '#A32D2D' : '#3B6D11',
            delta: null, icon: <AlertTriangle size={20} />,
            onClick: () => nav('/flagged-sales'),
        },
    ];

    return (
        <div className="stats-grid" style={{ marginBottom: 24 }}>
            {cards.map((c, i) => (
                <div className="stat-card" key={i} style={{ cursor: c.onClick ? 'pointer' : undefined }} onClick={c.onClick}>
                    <div className="stat-icon" style={{ background: `${c.color}18`, color: c.color }}>{c.icon}</div>
                    <div className="stat-value" style={{ color: c.color }}>{c.value}</div>
                    <div className="stat-label">{c.label}</div>
                    {c.delta !== null && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.75rem', fontWeight: 700, color: c.delta >= 0 ? '#3B6D11' : '#A32D2D', marginTop: 4 }}>
                            {c.delta >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                            {c.delta >= 0 ? '+' : ''}{c.delta}% vs last week
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}

// ==================== CHART 1: P Score Ranking ====================
function PScoreRanking({ employees }: { employees: StoreOverview['currentWeek']['employees'] }) {
    const sorted = [...employees].sort((a, b) => b.pScore - a.pScore);

    return (
        <div className="card">
            <div className="card-header"><span className="card-title">Employee P Score Ranking</span></div>
            <div className="chart-container" style={{ height: Math.max(250, sorted.length * 40 + 40) }}>
                {sorted.length === 0 ? <ChartLoading /> : (
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={sorted} layout="vertical" margin={{ left: 10, right: 30 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                            <XAxis type="number" domain={[0, 100]} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                            <YAxis type="category" dataKey="name" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} width={90} />
                            <Tooltip
                                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, color: 'var(--text-primary)' }}
                                formatter={(v: any) => [v, 'P Score']}
                            />
                            <Bar dataKey="pScore" radius={[0, 6, 6, 0]} label={{ position: 'right', fill: 'var(--text-secondary)', fontSize: 11, fontWeight: 700 }}>
                                {sorted.map((e, i) => (
                                    <Cell key={i} fill={getScoreColor(e.pScore)} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                )}
            </div>
        </div>
    );
}

// ==================== CHART 2: Revenue vs Target ====================
function RevenueVsTarget({ employees }: { employees: StoreOverview['currentWeek']['employees'] }) {
    const data = employees.map(e => ({
        name: e.name.split(' ')[0],
        revenue: e.weeklyRevenue,
        target: e.weeklyTarget,
        pctTarget: e.weeklyTarget > 0 ? Math.round((e.weeklyRevenue / e.weeklyTarget) * 100) : 0,
    }));
    const avgRevenue = data.length > 0 ? data.reduce((s, d) => s + d.revenue, 0) / data.length : 0;

    return (
        <div className="card">
            <div className="card-header"><span className="card-title">Revenue vs Target</span></div>
            <div className="chart-container">
                {data.length === 0 ? <ChartLoading /> : (
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={data}>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                            <XAxis dataKey="name" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                            <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}K`} />
                            <Tooltip
                                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, color: 'var(--text-primary)' }}
                                formatter={(v: any, name: string) => [`₹${Number(v).toLocaleString('en-IN')}`, name === 'revenue' ? 'Revenue' : 'Target']}
                                labelFormatter={(name) => { const d = data.find(x => x.name === name); return d ? `${name} — ${d.pctTarget}% of target` : name; }}
                            />
                            <ReferenceLine y={avgRevenue} stroke="#F97316" strokeDasharray="4 4" strokeOpacity={0.6} />
                            <Bar dataKey="revenue" fill="#F97316" radius={[6, 6, 0, 0]} name="revenue" />
                            <Bar dataKey="target" fill="#888" opacity={0.35} radius={[6, 6, 0, 0]} name="target" />
                        </BarChart>
                    </ResponsiveContainer>
                )}
            </div>
        </div>
    );
}

// ==================== CHART 3: Score Distribution ====================
function ScoreDistribution({ employees }: { employees: StoreOverview['currentWeek']['employees'] }) {
    const low = employees.filter(e => e.pScore < 50).length;
    const mid = employees.filter(e => e.pScore >= 50 && e.pScore < 75).length;
    const high = employees.filter(e => e.pScore >= 75).length;
    const total = employees.length;

    const data = [
        { band: 'Low (0–49)', count: low, fill: '#A32D2D', pct: total > 0 ? Math.round((low / total) * 100) : 0 },
        { band: 'Mid (50–74)', count: mid, fill: '#BA7517', pct: total > 0 ? Math.round((mid / total) * 100) : 0 },
        { band: 'High (75–100)', count: high, fill: '#3B6D11', pct: total > 0 ? Math.round((high / total) * 100) : 0 },
    ];

    return (
        <div className="card">
            <div className="card-header">
                <span className="card-title">Score Distribution</span>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{high} of {total} above 75</span>
            </div>
            <div className="chart-container" style={{ height: 220 }}>
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                        <XAxis dataKey="band" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                        <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} allowDecimals={false} />
                        <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, color: 'var(--text-primary)' }} />
                        <Bar dataKey="count" radius={[6, 6, 0, 0]} label={{ position: 'top', fill: 'var(--text-secondary)', fontSize: 11, formatter: (v: number) => `${data.find(d => d.count === v)?.pct || 0}%` }}>
                            {data.map((d, i) => <Cell key={i} fill={d.fill} />)}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}

// ==================== CHART 4: Attendance Heatmap ====================
function AttendanceHeatmap({ matrix }: { matrix: StoreOverview['attendanceMatrix'] }) {
    const statusColors: Record<string, string> = {
        ON_TIME: '#3B6D11', LATE: '#BA7517', VERY_LATE: '#A32D2D', ABSENT: '#A32D2D', DAY_OFF: 'var(--bg-input)',
    };

    if (!matrix.length) return null;
    const days = matrix[0]?.days || [];

    return (
        <div className="card">
            <div className="card-header"><span className="card-title">Attendance Heatmap — 28 Days</span></div>
            <div style={{ overflowX: 'auto', padding: '0 20px 20px' }}>
                <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: 2, minWidth: 600 }}>
                    <thead>
                        <tr>
                            <th style={{ width: 100, textAlign: 'left', fontSize: '0.7rem', color: 'var(--text-muted)' }}>Employee</th>
                            {days.map((d, i) => (
                                <th key={i} style={{ fontSize: '0.6rem', color: 'var(--text-muted)', padding: 0, fontWeight: 500 }}>
                                    {new Date(d.date).toLocaleDateString('en-IN', { day: 'numeric' })}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {matrix.map(emp => (
                            <tr key={emp.employeeId}>
                                <td style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', whiteSpace: 'nowrap', paddingRight: 8 }}>{emp.name.split(' ')[0]}</td>
                                {emp.days.map((d, i) => (
                                    <td key={i} title={`${new Date(d.date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })} — ${d.status.replace(/_/g, ' ')}`}>
                                        <div style={{
                                            width: 14, height: 14, borderRadius: 3, margin: '0 auto',
                                            background: statusColors[d.status] || 'var(--bg-input)',
                                            opacity: d.status === 'DAY_OFF' ? 0.3 : d.status === 'ABSENT' ? 0.7 : 1,
                                        }} />
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
                <div style={{ display: 'flex', gap: 16, marginTop: 12, fontSize: '0.7rem', color: 'var(--text-muted)', flexWrap: 'wrap' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 10, height: 10, borderRadius: 2, background: '#3B6D11' }} /> On Time</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 10, height: 10, borderRadius: 2, background: '#BA7517' }} /> Late</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 10, height: 10, borderRadius: 2, background: '#A32D2D' }} /> Absent / Very Late</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 10, height: 10, borderRadius: 2, background: 'var(--bg-input)' }} /> Day Off</span>
                </div>
            </div>
        </div>
    );
}

// ==================== CHART 5: Basket Size Trend ====================
function BasketTrend({ basketTrend }: { basketTrend: StoreOverview['basketTrend'] }) {
    if (!basketTrend.length || !basketTrend[0].employees.length) return null;

    const empNames = basketTrend[0].employees.map(e => e.name);
    const chartData = basketTrend.map(wk => {
        const row: Record<string, any> = { week: wk.week };
        wk.employees.forEach(e => { row[e.name] = e.avgBasketSize; });
        return row;
    });

    // Dept avg for reference line
    const allBaskets = basketTrend.flatMap(wk => wk.employees.map(e => e.avgBasketSize)).filter(v => v > 0);
    const deptAvg = allBaskets.length > 0 ? allBaskets.reduce((s, v) => s + v, 0) / allBaskets.length : 0;

    return (
        <div className="card">
            <div className="card-header"><span className="card-title">Basket Size Trend — Last 8 Weeks</span></div>
            <div className="chart-container">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                        <XAxis dataKey="week" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                        <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickFormatter={(v) => `₹${v}`} />
                        <Tooltip
                            contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, color: 'var(--text-primary)' }}
                            formatter={(v: any, name: string) => [`₹${Number(v).toLocaleString('en-IN')}`, name]}
                        />
                        <ReferenceLine y={deptAvg} stroke="var(--text-muted)" strokeDasharray="4 4" label={{ value: `Avg ₹${deptAvg.toFixed(0)}`, fill: 'var(--text-muted)', fontSize: 10, position: 'right' }} />
                        {empNames.slice(0, 10).map((name, i) => (
                            <Line key={name} type="monotone" dataKey={name} stroke={EMP_PALETTE[i % EMP_PALETTE.length]} strokeWidth={2} dot={{ r: 3 }} name={name} />
                        ))}
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}

// ==================== CHART 6: Stability vs P Score Scatter ====================
function StabilityScatter({ employees }: { employees: StoreOverview['currentWeek']['employees'] }) {
    const data = employees.map(e => ({
        x: e.M5, y: e.pScore, name: e.name, department: e.department,
        fill: DEPT_COLORS[e.department] || '#888',
    }));

    return (
        <div className="card">
            <div className="card-header"><span className="card-title">Stability vs P Score</span></div>
            <div className="chart-container" style={{ position: 'relative' }}>
                {/* Quadrant labels */}
                <div style={{ position: 'absolute', top: 12, right: 24, fontSize: '0.65rem', color: 'var(--text-muted)', opacity: 0.6 }}>Reliable stars</div>
                <div style={{ position: 'absolute', top: 12, left: 24, fontSize: '0.65rem', color: 'var(--text-muted)', opacity: 0.6 }}>Streaky performers</div>
                <div style={{ position: 'absolute', bottom: 32, right: 24, fontSize: '0.65rem', color: 'var(--text-muted)', opacity: 0.6 }}>Consistent underperformers</div>
                <div style={{ position: 'absolute', bottom: 32, left: 24, fontSize: '0.65rem', color: 'var(--text-muted)', opacity: 0.6 }}>At risk</div>
                <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart margin={{ left: 10, right: 10, bottom: 10 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                        <XAxis type="number" dataKey="x" domain={[0, 100]} name="Stability" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} label={{ value: 'Stability Index (M5)', position: 'bottom', fill: 'var(--text-muted)', fontSize: 11, offset: -5 }} />
                        <YAxis type="number" dataKey="y" domain={[0, 100]} name="P Score" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} label={{ value: 'P Score', angle: -90, position: 'insideLeft', fill: 'var(--text-muted)', fontSize: 11 }} />
                        <ZAxis range={[150, 150]} />
                        <ReferenceLine x={50} stroke="var(--border)" strokeDasharray="4 4" />
                        <ReferenceLine y={50} stroke="var(--border)" strokeDasharray="4 4" />
                        <Tooltip
                            contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, color: 'var(--text-primary)' }}
                            content={({ payload }) => {
                                if (!payload?.[0]) return null;
                                const d = payload[0].payload;
                                return (
                                    <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, padding: 12 }}>
                                        <div style={{ fontWeight: 700 }}>{d.name}</div>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{d.department}</div>
                                        <div style={{ fontSize: '0.8rem', marginTop: 4 }}>Stability: {d.x}</div>
                                        <div style={{ fontSize: '0.8rem' }}>P Score: {d.y}</div>
                                    </div>
                                );
                            }}
                        />
                        <Scatter data={data}>
                            {data.map((d, i) => <Cell key={i} fill={d.fill} />)}
                        </Scatter>
                    </ScatterChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}

// ==================== CHART 7: Department Comparison ====================
function DeptComparison({ departments }: { departments: DeptSummary['departments'] }) {
    if (!departments.length) return null;

    // Scale revenue to 0-100 range for comparability
    const maxRev = Math.max(...departments.map(d => d.avgRevenue), 1);
    const data = departments.map(d => ({
        department: d.department,
        'Avg P Score': d.avgPScore,
        'Revenue (scaled)': Math.round((d.avgRevenue / maxRev) * 100),
        'Avg Attendance': d.avgAttendance,
        avgRevenue: d.avgRevenue,
    }));

    return (
        <div className="card">
            <div className="card-header"><span className="card-title">Department Comparison</span></div>
            <div className="chart-container">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                        <XAxis dataKey="department" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                        <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} domain={[0, 100]} />
                        <Tooltip
                            contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, color: 'var(--text-primary)' }}
                            formatter={(v: any, name: string, props: any) => {
                                if (name === 'Revenue (scaled)') return [`₹${props.payload.avgRevenue.toLocaleString('en-IN')}`, 'Avg Revenue'];
                                return [v, name];
                            }}
                        />
                        <Bar dataKey="Avg P Score" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                        <Bar dataKey="Revenue (scaled)" fill="#F97316" radius={[4, 4, 0, 0]} />
                        <Bar dataKey="Avg Attendance" fill="#22C55E" radius={[4, 4, 0, 0]} />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}


// ==================== MAIN COMPONENT ====================
export default function ManagerDashboard() {
    const { data, loading, refetch } = useApi<ManagerDashboardData>('/api/dashboard/manager');
    const { data: pendingEmployees, refetch: refetchPending } = useApi<PendingEmployee[]>('/api/manager/pending-employees');
    const { data: storeData, loading: storeLoading } = useApi<StoreOverview>('/api/manager/store-overview');
    const { data: deptData } = useApi<DeptSummary>('/api/manager/department-summary');
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
            {/* ===== PHASE 2: Store Summary Cards ===== */}
            {storeData && <StoreSummaryCards overview={storeData} />}

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

            {/* Original KPI Cards */}
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

            {/* ===== PHASE 2 CHARTS ===== */}
            {storeData && (
                <>
                    {/* P Score Ranking + Score Distribution */}
                    <div className="dashboard-grid" style={{ marginTop: 24 }}>
                        <PScoreRanking employees={storeData.currentWeek.employees} />
                        <ScoreDistribution employees={storeData.currentWeek.employees} />
                    </div>

                    {/* Revenue vs Target + Stability Scatter */}
                    <div className="dashboard-grid">
                        <RevenueVsTarget employees={storeData.currentWeek.employees} />
                        <StabilityScatter employees={storeData.currentWeek.employees} />
                    </div>

                    {/* Basket Trend */}
                    <BasketTrend basketTrend={storeData.basketTrend} />

                    {/* Attendance Heatmap */}
                    <AttendanceHeatmap matrix={storeData.attendanceMatrix} />
                </>
            )}

            {/* Department Comparison */}
            {deptData && <DeptComparison departments={deptData.departments} />}

            {/* ===== ORIGINAL CONTENT ===== */}
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
