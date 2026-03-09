import { useApi } from '../../hooks/useApi';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis } from 'recharts';
import { TrendingUp, IndianRupee, ShoppingCart, Download, Zap } from 'lucide-react';

interface DashboardData {
    employee: { name: string; department_name: string; store_name: string; total_xp: number; level: number; level_title: string };
    score: { productivity_index: number; metrics: Record<string, number>; weights: Record<string, number> };
    gamification: { level: number; title: string; total_xp: number; next_threshold: number; current_threshold: number; progress: number; xp_to_next: number; badges: Array<{ badge_name: string; badge_emoji: string; description: string }>; streak: number };
    trends: { weeks: Array<{ week: string; week_start: string; revenue: number; num_sales: number; avg_basket: number }>; trend_line: number[]; direction: string };
    weekly_stats: { revenue: number; bills: number; avg_basket: number; app_downloads: number };
}

export default function EmployeeDashboard({ employeeId }: { employeeId: number }) {
    const { data, loading } = useApi<DashboardData>(`/api/dashboard/employee/${employeeId}`);

    if (loading || !data) return <div className="animate-in" style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Loading dashboard...</div>;

    const { employee, score, gamification, trends, weekly_stats } = data;
    const circumference = 2 * Math.PI * 58;
    const offset = circumference - (score.productivity_index / 100) * circumference;
    const xpCircumference = 2 * Math.PI * 58;
    const xpOffset = xpCircumference - gamification.progress * xpCircumference;

    const radarData = Object.entries(score.metrics).map(([key, value]) => ({ metric: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()), value: Math.round(value), fullMark: 100 }));

    return (
        <div className="animate-in">
            <p style={{ color: 'var(--text-secondary)', marginTop: -20, marginBottom: 24 }}>Welcome back, <strong>{employee.name}</strong>! · {employee.department_name} · {employee.store_name}</p>

            {/* Score + XP Row */}
            <div className="dashboard-grid" style={{ marginBottom: 24 }}>
                {/* Productivity Score */}
                <div className="score-ring-container">
                    <div className="score-ring">
                        <svg viewBox="0 0 128 128">
                            <circle className="ring-bg" cx="64" cy="64" r="58" />
                            <circle className="ring-progress" cx="64" cy="64" r="58" strokeDasharray={circumference} strokeDashoffset={offset} />
                        </svg>
                        <div className="ring-label">
                            <div className="ring-value">{score.productivity_index}</div>
                            <div className="ring-subtitle">/ 100</div>
                        </div>
                    </div>
                    <div className="score-details">
                        <div className="score-title">Productivity Score</div>
                        <div className="score-subtitle">Updated in real-time from approved data</div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <TrendingUp size={16} color={trends.direction === 'growing' ? 'var(--success)' : 'var(--danger)'} />
                            <span style={{ fontSize: '0.85rem', color: trends.direction === 'growing' ? 'var(--success)' : 'var(--danger)', fontWeight: 600 }}>
                                {trends.direction === 'growing' ? '↑ Growing' : trends.direction === 'declining' ? '↓ Declining' : '→ Stable'}
                            </span>
                        </div>
                    </div>
                </div>

                {/* XP Ring */}
                <div className="score-ring-container">
                    <div className="score-ring">
                        <svg viewBox="0 0 128 128">
                            <circle className="ring-bg" cx="64" cy="64" r="58" />
                            <circle className="ring-progress" cx="64" cy="64" r="58" strokeDasharray={xpCircumference} strokeDashoffset={xpOffset} style={{ stroke: '#8B5CF6' }} />
                        </svg>
                        <div className="ring-label">
                            <div className="ring-value" style={{ fontSize: '1.2rem', color: '#8B5CF6' }}>Lv {gamification.level}</div>
                            <div className="ring-subtitle">{gamification.title}</div>
                        </div>
                    </div>
                    <div className="score-details">
                        <div className="score-title">{gamification.total_xp.toLocaleString()} XP</div>
                        <div className="score-subtitle">{gamification.xp_to_next.toLocaleString()} XP to next level</div>
                        <div className="xp-bar-container">
                            <div className="xp-bar">
                                <div className="xp-bar-fill" style={{ width: `${gamification.progress * 100}%`, background: 'linear-gradient(90deg, #8B5CF6, #A78BFA)' }} />
                            </div>
                        </div>
                        <div style={{ marginTop: 8, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                            🔥 {gamification.streak}-day streak
                        </div>
                    </div>
                </div>
            </div>

            {/* Stat Cards */}
            <div className="stats-grid">
                <div className="stat-card">
                    <div className="stat-icon"><IndianRupee size={20} /></div>
                    <div className="stat-value">₹{(weekly_stats.revenue / 1000).toFixed(1)}K</div>
                    <div className="stat-label">Weekly Revenue</div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon"><ShoppingCart size={20} /></div>
                    <div className="stat-value">{weekly_stats.bills}</div>
                    <div className="stat-label">Bills Generated</div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon"><Zap size={20} /></div>
                    <div className="stat-value">₹{weekly_stats.avg_basket.toLocaleString()}</div>
                    <div className="stat-label">Avg Basket Size</div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon"><Download size={20} /></div>
                    <div className="stat-value">{weekly_stats.app_downloads}</div>
                    <div className="stat-label">App Downloads</div>
                </div>
            </div>

            {/* Charts Row */}
            <div className="dashboard-grid">
                {/* Performance Trend */}
                <div className="card">
                    <div className="card-header">
                        <span className="card-title">Weekly Performance Trend</span>
                    </div>
                    <div className="chart-container">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={trends.weeks.map((w, i) => ({ ...w, trend: trends.trend_line[i] }))}>
                                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                                <XAxis dataKey="week_start" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} tickFormatter={(v) => new Date(v).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })} />
                                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 12 }} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}K`} />
                                <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, color: 'var(--text-primary)' }} formatter={(v: any) => [`₹${Number(v).toLocaleString()}`, '']} />
                                <Line type="monotone" dataKey="revenue" stroke="#F97316" strokeWidth={3} dot={{ fill: '#F97316', r: 5 }} activeDot={{ r: 7 }} name="Revenue" />
                                <Line type="monotone" dataKey="trend" stroke="#F97316" strokeWidth={1} strokeDasharray="5 5" dot={false} name="Trend" />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Radar Chart */}
                <div className="card">
                    <div className="card-header">
                        <span className="card-title">Metric Breakdown</span>
                    </div>
                    <div className="chart-container">
                        <ResponsiveContainer width="100%" height="100%">
                            <RadarChart data={radarData}>
                                <PolarGrid stroke="var(--border)" />
                                <PolarAngleAxis dataKey="metric" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                                <Radar dataKey="value" stroke="#F97316" fill="#F97316" fillOpacity={0.2} strokeWidth={2} />
                            </RadarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            {/* Badges */}
            <div className="card">
                <div className="card-header">
                    <span className="card-title">Earned Badges</span>
                </div>
                <div className="badges-container">
                    {gamification.badges.length > 0 ? gamification.badges.map((badge, i) => (
                        <div className="badge-item" key={i}>
                            <span className="badge-emoji">{badge.badge_emoji}</span>
                            <div>
                                <div className="badge-name">{badge.badge_name}</div>
                                <div className="badge-desc">{badge.description}</div>
                            </div>
                        </div>
                    )) : (
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>No badges earned yet. Keep performing to unlock badges!</p>
                    )}
                </div>
            </div>
        </div>
    );
}
