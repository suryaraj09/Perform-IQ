import { useApi } from '../../hooks/useApi';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Area, ComposedChart, ReferenceLine } from 'recharts';
import { TrendingUp, IndianRupee, ShoppingCart, Zap } from 'lucide-react';

interface DashboardData {
    employee: { name: string; department_name: string; store_name: string; total_xp: number; level: number; level_title: string };
    score: { productivity_index: number; metrics: Record<string, number>; weights: Record<string, number> };
    gamification: { level: number; title: string; total_xp: number; next_threshold: number; current_threshold: number; progress: number; xp_to_next: number; badges: Array<{ badge_name: string; badge_emoji: string; description: string }>; streak: number };
    trends: { weeks: Array<{ week: string; week_start: string; revenue: number; num_sales: number; avg_basket: number }>; trend_line: number[]; direction: string };
    weekly_stats: { revenue: number; bills: number; avg_basket: number };
}

interface V2DashboardData {
    employee: { employeeId: string; name: string; department: string; level: number; levelLabel: string; xp: number; xpToNextLevel: number; weeklyTarget: number; shiftStartTime: string };
    currentWeek: { weekNumber: number; year: number; pScore: number; M1: number; M2: number; M3: number; M4: number; M5: number; M7: number; M8: number; weeklyRevenue: number; totalBills: number; avgBasketSize: number; revenueRemaining: number };
    weeklyTrend: Array<{ week: string; revenue: number; target: number; pScore: number }>;
    streakData: Array<{ date: string; hitTarget: boolean; present: boolean; onTime: boolean }>;
    gamification: { currentStreak: number; longestStreak: number; rank: number; totalEmployees: number; weeklyXP: number; bonusXP: { streakBonus: number; leaderboardBonus: number; ratingBonus: number } };
}

const METRIC_CONFIG = [
    { key: 'M1', label: 'Revenue vs Target', weight: 0.30 },
    { key: 'M2', label: 'Basket Performance', weight: 0.25 },
    { key: 'M3', label: 'Manager Rating', weight: 0.15 },
    { key: 'M4', label: 'Growth Trend', weight: 0.10 },
    { key: 'M5', label: 'Stability Index', weight: 0.10 },
    { key: 'M7', label: 'Attendance Rate', weight: 0.05 },
    { key: 'M8', label: 'Punctuality Score', weight: 0.05 },
];

const LEVEL_THRESHOLDS = [
    { level: 1, label: 'Rookie', min: 0, max: 999 },
    { level: 2, label: 'Associate', min: 1000, max: 2999 },
    { level: 3, label: 'Performer', min: 3000, max: 5999 },
    { level: 4, label: 'Expert', min: 6000, max: 9999 },
    { level: 5, label: 'Champion', min: 10000, max: 99999 },
];

function getScoreColor(score: number) {
    if (score >= 75) return '#3B6D11';
    if (score >= 50) return '#BA7517';
    return '#A32D2D';
}

function getBarColor(score: number) {
    if (score >= 67) return '#3B6D11';
    if (score >= 34) return '#BA7517';
    return '#A32D2D';
}

function LoadingSkeleton() {
    return (
        <div className="animate-in" style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
            <div style={{ width: 48, height: 48, borderRadius: '50%', border: '3px solid var(--border)', borderTopColor: '#F97316', margin: '0 auto 16px', animation: 'spin 0.8s linear infinite' }} />
            Loading dashboard...
            <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
        </div>
    );
}

// ===================== COMPONENT 1: P Score Radial Gauge =====================
function PScoreGauge({ pScore, rank, totalEmployees }: { pScore: number; rank: number; totalEmployees: number }) {
    const clampedScore = Math.max(0, Math.min(100, pScore));
    const r = 90;
    const circumference = Math.PI * r;
    const offset = circumference - (clampedScore / 100) * circumference;
    const scoreColor = getScoreColor(clampedScore);

    return (
        <div className="card" style={{ textAlign: 'center', padding: 24 }}>
            <div className="card-header"><span className="card-title">Productivity Score</span></div>
            <svg viewBox="0 0 220 130" style={{ maxWidth: 280, margin: '0 auto', display: 'block' }}>
                {/* Background arc */}
                <path d="M 20 120 A 90 90 0 0 1 200 120" fill="none" stroke="var(--border)" strokeWidth="14" strokeLinecap="round" />
                {/* Color zone arcs */}
                <path d="M 20 120 A 90 90 0 0 1 200 120" fill="none" stroke="#A32D2D" strokeWidth="14" strokeLinecap="round" opacity="0.15" />
                {/* Score arc */}
                <path
                    d="M 20 120 A 90 90 0 0 1 200 120"
                    fill="none" stroke={scoreColor} strokeWidth="14" strokeLinecap="round"
                    strokeDasharray={`${circumference}`}
                    strokeDashoffset={offset}
                    style={{ transition: 'stroke-dashoffset 1s ease-out' }}
                />
                {/* Score text */}
                <text x="110" y="100" textAnchor="middle" fontSize="38" fontWeight="800" fill="var(--text-primary)">{clampedScore}</text>
                <text x="110" y="120" textAnchor="middle" fontSize="11" fill="var(--text-muted)">This week</text>
            </svg>
            <div style={{
                display: 'inline-flex', alignItems: 'center', gap: 6, marginTop: 8,
                padding: '4px 14px', borderRadius: 20,
                background: rank <= 3 ? 'rgba(59, 109, 17, 0.1)' : 'var(--glass)',
                color: rank <= 3 ? '#3B6D11' : 'var(--text-secondary)',
                fontSize: '0.8rem', fontWeight: 700,
            }}>
                🏅 Rank #{rank} of {totalEmployees}
            </div>
        </div>
    );
}

// ===================== COMPONENT 2: Metric Contribution Bars =====================
function MetricBars({ currentWeek }: { currentWeek: V2DashboardData['currentWeek'] }) {
    const total = METRIC_CONFIG.reduce((sum, m) => {
        const raw = (currentWeek as any)[m.key] || 0;
        return sum + raw * m.weight;
    }, 0);

    return (
        <div className="card">
            <div className="card-header"><span className="card-title">Metric Contributions</span></div>
            <div style={{ padding: '0 20px 16px' }}>
                {METRIC_CONFIG.map(m => {
                    const raw = (currentWeek as any)[m.key] || 0;
                    const weighted = +(raw * m.weight).toFixed(1);
                    const color = getBarColor(raw);
                    return (
                        <div key={m.key} style={{ marginBottom: 12 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: 4 }}>
                                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{m.label}</span>
                                <span style={{ color: 'var(--text-muted)' }}>{Math.round(m.weight * 100)}% · {raw.toFixed(0)}/100 · <strong style={{ color }}>{weighted}</strong></span>
                            </div>
                            <div style={{ height: 8, borderRadius: 4, background: 'var(--bg-input)', overflow: 'hidden' }}>
                                <div style={{ height: '100%', width: `${Math.min(100, raw)}%`, borderRadius: 4, background: color, transition: 'width 0.8s ease-out' }} />
                            </div>
                        </div>
                    );
                })}
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16, paddingTop: 12, borderTop: '1px solid var(--border)', fontWeight: 700, fontSize: '0.9rem' }}>
                    <span>Total P Score</span>
                    <span style={{ color: getScoreColor(total) }}>{total.toFixed(1)}</span>
                </div>
            </div>
        </div>
    );
}

// ===================== COMPONENT 3: Revenue vs Target Line Chart =====================
function RevenueTargetChart({ weeklyTrend }: { weeklyTrend: V2DashboardData['weeklyTrend'] }) {
    const chartData = weeklyTrend.map(w => ({
        ...w,
        above: w.revenue >= w.target ? w.revenue - w.target : 0,
        below: w.revenue < w.target ? w.target - w.revenue : 0,
    }));

    return (
        <div className="card">
            <div className="card-header"><span className="card-title">Revenue vs Target — Last 8 Weeks</span></div>
            <div className="chart-container">
                {chartData.length === 0 ? (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>No trend data available</div>
                ) : (
                    <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={chartData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                            <XAxis dataKey="week" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
                            <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 12 }} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}K`} />
                            <Tooltip
                                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, color: 'var(--text-primary)' }}
                                formatter={(v: any, name: string) => [
                                    `₹${Number(v).toLocaleString('en-IN')}`,
                                    name === 'revenue' ? 'My Revenue' : name === 'target' ? 'My Target' : name
                                ]}
                                labelFormatter={(label: string) => {
                                    const w = chartData.find(d => d.week === label);
                                    return w ? `${label} · P Score: ${w.pScore}` : label;
                                }}
                            />
                            <Area type="monotone" dataKey="target" fill="transparent" stroke="none" />
                            <Line type="monotone" dataKey="target" stroke="#888" strokeWidth={2} strokeDasharray="6 4" dot={false} name="target" />
                            <Line type="monotone" dataKey="revenue" stroke="#F97316" strokeWidth={3} dot={{ fill: '#F97316', r: 5 }} activeDot={{ r: 7 }} name="revenue" />
                        </ComposedChart>
                    </ResponsiveContainer>
                )}
            </div>
        </div>
    );
}

// ===================== COMPONENT 4: Progress Ring — This Week's Target =====================
function TargetProgressRing({ weeklyRevenue, weeklyTarget, revenueRemaining }: { weeklyRevenue: number; weeklyTarget: number; revenueRemaining: number }) {
    const pct = weeklyTarget > 0 ? Math.min(100, (weeklyRevenue / weeklyTarget) * 100) : 0;
    const exceeded = weeklyRevenue >= weeklyTarget && weeklyTarget > 0;
    const overAmount = exceeded ? weeklyRevenue - weeklyTarget : 0;
    const ringColor = exceeded ? '#3B6D11' : pct >= 75 ? '#3B6D11' : pct >= 50 ? '#BA7517' : '#A32D2D';
    const r = 58;
    const circumference = 2 * Math.PI * r;
    const offset = circumference - (Math.min(100, pct) / 100) * circumference;

    const fmtK = (v: number) => v >= 1000 ? `₹${(v / 1000).toFixed(1)}K` : `₹${v.toFixed(0)}`;

    return (
        <div className="card" style={{ textAlign: 'center', padding: 24 }}>
            <div className="card-header"><span className="card-title">This Week's Target</span></div>
            <svg viewBox="0 0 128 128" style={{ width: 140, height: 140, margin: '8px auto' }}>
                <circle cx="64" cy="64" r={r} fill="none" stroke="var(--border)" strokeWidth="10" />
                <circle cx="64" cy="64" r={r} fill="none" stroke={ringColor} strokeWidth="10"
                    strokeDasharray={circumference} strokeDashoffset={offset}
                    strokeLinecap="round" transform="rotate(-90 64 64)"
                    style={{ transition: 'stroke-dashoffset 1s ease-out' }}
                />
                <text x="64" y="58" textAnchor="middle" fontSize="13" fontWeight="700" fill="var(--text-primary)">{fmtK(weeklyRevenue)}</text>
                <text x="64" y="74" textAnchor="middle" fontSize="10" fill="var(--text-muted)">of {fmtK(weeklyTarget)}</text>
            </svg>
            <div style={{ fontSize: '0.85rem', fontWeight: 600, color: exceeded ? '#3B6D11' : ringColor, marginTop: 4 }}>
                {exceeded ? `✅ Target hit! ₹${overAmount.toLocaleString('en-IN')} over` : `₹${revenueRemaining.toLocaleString('en-IN')} remaining`}
            </div>
        </div>
    );
}

// ===================== COMPONENT 5: XP Progress Bar =====================
function XPProgressBar({ employee, gamification }: { employee: V2DashboardData['employee']; gamification: V2DashboardData['gamification'] }) {
    const currentLevel = LEVEL_THRESHOLDS.find(l => l.level === employee.level) || LEVEL_THRESHOLDS[0];
    const nextLevel = LEVEL_THRESHOLDS.find(l => l.level === employee.level + 1);
    const rangeMin = currentLevel.min;
    const rangeMax = nextLevel ? nextLevel.min : currentLevel.max;
    const progressPct = rangeMax > rangeMin ? Math.min(100, ((employee.xp - rangeMin) / (rangeMax - rangeMin)) * 100) : 100;
    const bonuses = gamification.bonusXP;
    const hasBonuses = bonuses.streakBonus > 0 || bonuses.leaderboardBonus > 0 || bonuses.ratingBonus > 0;

    return (
        <div className="card">
            <div className="card-header"><span className="card-title">Level Progress</span></div>
            <div style={{ padding: '0 20px 20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <span style={{ padding: '3px 12px', borderRadius: 12, background: 'rgba(139, 92, 246, 0.15)', color: '#8B5CF6', fontWeight: 700, fontSize: '0.8rem' }}>
                        {currentLevel.label}
                    </span>
                    {nextLevel && (
                        <span style={{ padding: '3px 12px', borderRadius: 12, background: 'var(--glass)', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.8rem' }}>
                            {nextLevel.label}
                        </span>
                    )}
                </div>
                <div style={{ height: 12, borderRadius: 6, background: 'var(--bg-input)', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${progressPct}%`, borderRadius: 6, background: 'linear-gradient(90deg, #8B5CF6, #A78BFA)', transition: 'width 1s ease-out' }} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 6 }}>
                    <span>{employee.xp.toLocaleString()} XP</span>
                    <span>{employee.xpToNextLevel.toLocaleString()} XP to next level</span>
                </div>
                <div style={{ marginTop: 12, display: 'flex', gap: 12, flexWrap: 'wrap', fontSize: '0.8rem' }}>
                    <span style={{ color: '#8B5CF6', fontWeight: 700 }}>+{gamification.weeklyXP} XP this week</span>
                    {hasBonuses && (
                        <span style={{ color: 'var(--text-secondary)' }}>
                            {bonuses.streakBonus > 0 && `🔥 Streak +${bonuses.streakBonus} `}
                            {bonuses.leaderboardBonus > 0 && `🏅 Top 3 +${bonuses.leaderboardBonus} `}
                            {bonuses.ratingBonus > 0 && `⭐ Rating +${bonuses.ratingBonus}`}
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
}

// ===================== COMPONENT 6: Streak Calendar =====================
function StreakCalendar({ streakData, currentStreak }: { streakData: V2DashboardData['streakData']; currentStreak: number }) {
    const getDotColor = (d: V2DashboardData['streakData'][0]) => {
        if (!d.present && !d.onTime) return 'var(--text-muted)';  // day off or no data
        if (!d.present) return '#A32D2D';
        if (d.present && !d.onTime) return '#BA7517';
        if (d.present && d.hitTarget) return '#3B6D11';
        return '#6BBF4A';
    };

    const getDotTooltip = (d: V2DashboardData['streakData'][0]) => {
        const dt = new Date(d.date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' });
        if (!d.present) return `${dt}: Absent`;
        if (!d.onTime) return `${dt}: Late`;
        if (d.hitTarget) return `${dt}: Target hit ✓`;
        return `${dt}: Present`;
    };

    return (
        <div className="card">
            <div className="card-header">
                <span className="card-title">Streak Calendar — 28 Days</span>
                <span style={{ fontWeight: 700, fontSize: '0.9rem', color: currentStreak >= 7 ? '#3B6D11' : currentStreak > 0 ? '#BA7517' : 'var(--text-muted)' }}>
                    🔥 {currentStreak} day streak
                </span>
            </div>
            <div style={{ padding: '12px 20px 20px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 6 }}>
                    {['M', 'T', 'W', 'T', 'F', 'S', 'S'].map((d, i) => (
                        <div key={i} style={{ textAlign: 'center', fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 600, marginBottom: 4 }}>{d}</div>
                    ))}
                    {streakData.map((d, i) => (
                        <div key={i} title={getDotTooltip(d)} style={{
                            width: '100%', aspectRatio: '1', borderRadius: '50%',
                            background: getDotColor(d), cursor: 'default',
                            transition: 'transform 0.15s', maxWidth: 28, margin: '0 auto',
                        }}
                        onMouseEnter={e => (e.currentTarget.style.transform = 'scale(1.3)')}
                        onMouseLeave={e => (e.currentTarget.style.transform = 'scale(1)')}
                        />
                    ))}
                </div>
                <div style={{ display: 'flex', gap: 16, marginTop: 12, fontSize: '0.7rem', color: 'var(--text-muted)', justifyContent: 'center', flexWrap: 'wrap' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: '#3B6D11' }} /> Target hit</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: '#6BBF4A' }} /> Present</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: '#BA7517' }} /> Late</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: '#A32D2D' }} /> Absent</span>
                </div>
            </div>
        </div>
    );
}


// ===================== MAIN DASHBOARD COMPONENT =====================
export default function EmployeeDashboard({ employeeId }: { employeeId: number }) {
    const { data, loading } = useApi<DashboardData>(`/api/dashboard/employee/${employeeId}`);
    const { data: v2, loading: v2Loading } = useApi<V2DashboardData>(`/api/employee/${employeeId}/dashboard`);

    if (loading || !data) return <LoadingSkeleton />;

    const { employee, score, gamification, trends, weekly_stats } = data;

    const radarData = Object.entries(score.metrics).map(([key, value]) => ({ metric: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()), value: Math.round(value), fullMark: 100 }));

    return (
        <div className="animate-in">
            <p style={{ color: 'var(--text-secondary)', marginTop: -20, marginBottom: 24 }}>Welcome back, <strong>{employee.name}</strong>! · {employee.department_name} · {employee.store_name}</p>

            {/* ===== PHASE 2 VISUALISATIONS ===== */}
            {v2 && !v2Loading && (
                <>
                    {/* P Score Gauge + Target Ring */}
                    <div className="dashboard-grid" style={{ marginBottom: 24 }}>
                        <PScoreGauge pScore={v2.currentWeek.pScore} rank={v2.gamification.rank} totalEmployees={v2.gamification.totalEmployees} />
                        <TargetProgressRing weeklyRevenue={v2.currentWeek.weeklyRevenue} weeklyTarget={v2.employee.weeklyTarget} revenueRemaining={v2.currentWeek.revenueRemaining} />
                    </div>

                    {/* Metric Bars + XP Progress */}
                    <div className="dashboard-grid" style={{ marginBottom: 24 }}>
                        <MetricBars currentWeek={v2.currentWeek} />
                        <div>
                            <XPProgressBar employee={v2.employee} gamification={v2.gamification} />
                            <div style={{ marginTop: 16 }}>
                                <StreakCalendar streakData={v2.streakData} currentStreak={v2.gamification.currentStreak} />
                            </div>
                        </div>
                    </div>

                    {/* Revenue vs Target Line Chart */}
                    <RevenueTargetChart weeklyTrend={v2.weeklyTrend} />
                    <div style={{ marginBottom: 24 }} />
                </>
            )}

            {/* ===== ORIGINAL CONTENT PRESERVED ===== */}

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
