import { useApi } from '../../hooks/useApi';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Target, Users, AlertTriangle, TrendingUp, ArrowRight } from 'lucide-react';

interface StoreWarehouseSummary {
    store_id: string;
    store_name: string;
    store_location: string;
    avg_p_score: number;
    total_revenue: number;
    avg_attendance_rate: number;
    avg_punctuality_score: number;
    total_flagged_sales: number;
    total_geofence_alerts: number;
    employees_above_target: number;
    total_employees_active: number;
    top_performer_name: string;
    top_performer_score: number;
    store_rank: number;
    revenue_rank: number;
    attendance_rank: number;
}

interface WarehouseOverviewData {
    weekNumber: number;
    year: number;
    stores: StoreWarehouseSummary[];
}

// ISO Week helpers (same as manager dashboard)
function getISOWeek(date: Date) {
    const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
    const dayNum = d.getUTCDay() || 7;
    d.setUTCDate(d.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
    return Math.ceil((((d.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
}

function getWeekOptions(count = 8) {
    const options = [];
    const now = new Date();
    for (let i = 0; i < count; i++) {
        const d = new Date(now.getTime() - i * 7 * 24 * 60 * 60 * 1000);
        const w = getISOWeek(d);
        const y = d.getFullYear();
        options.push({ label: i === 0 ? `Current Week (W${w})` : `W${w}, ${y}`, week: w, year: y });
    }
    return options;
}

export default function WarehouseOverview() {
    const nav = useNavigate();
    const weekOptions = getWeekOptions(8);
    const [selectedWeek, setSelectedWeek] = useState(weekOptions[0]);
    
    const { data, loading } = useApi<WarehouseOverviewData>(
        `/api/headoffice/warehouse/overview?week=${selectedWeek.week}&year=${selectedWeek.year}`, 
        [selectedWeek]
    );

    const fmtRev = (v: number) => `₹${(v / 100000).toFixed(1)}L`;
    const getScoreColor = (s: number) => s >= 75 ? '#3B6D11' : s >= 50 ? '#BA7517' : '#A32D2D';

    if (loading) return <div className="p-8 text-center">Loading Warehouse Data...</div>;

    const sortedStores = data?.stores.sort((a, b) => a.store_rank - b.store_rank) || [];

    return (
        <div className="dashboard-container p-6">
            <header className="mb-8 flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold">Network Warehouse Overview</h1>
                    <p className="text-muted-foreground">Week {data?.weekNumber}, {data?.year}</p>
                </div>
                <div className="flex items-center gap-3">
                    <span className="text-sm text-muted-foreground font-medium">Reporting Period:</span>
                    <select 
                        className="bg-card border p-2 rounded-lg text-sm"
                        value={`${selectedWeek.week}-${selectedWeek.year}`}
                        onChange={(e) => {
                            const [w, y] = e.target.value.split('-').map(Number);
                            setSelectedWeek({ week: w, year: y, label: e.target.options[e.target.selectedIndex].text });
                        }}
                    >
                        {weekOptions.map(opt => (
                            <option key={`${opt.week}-${opt.year}`} value={`${opt.week}-${opt.year}`}>{opt.label}</option>
                        ))}
                    </select>
                </div>
            </header>

            {/* Store Ranking Strip */}
            <div className="bg-navy text-white rounded-xl p-4 mb-8 flex gap-8 items-center overflow-x-auto">
                <span className="text-xs font-bold uppercase tracking-widest opacity-60">Performance Leaderboard</span>
                {sortedStores.map(s => (
                    <div key={s.store_id} className="flex items-center gap-3 whitespace-nowrap border-l border-white/10 pl-8 first:border-l-0 first:pl-0">
                        <span className="text-xl font-black text-white/50">#{s.store_rank}</span>
                        <div>
                            <div className="text-sm font-bold">{s.store_name}</div>
                            <div className="text-xs opacity-80 flex items-center gap-1">
                                Avg P: {s.avg_p_score.toFixed(1)}
                                <TrendingUp size={12} className="text-green-400" />
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Store Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                {data?.stores.map(s => (
                    <div key={s.store_id} className="card p-6 border-t-4" style={{ borderColor: getScoreColor(s.avg_p_score) }}>
                        <div className="flex justify-between items-start mb-4">
                            <div>
                                <h3 className="font-bold text-lg">{s.store_name}</h3>
                                <p className="text-xs text-muted-foreground">{s.store_location}</p>
                            </div>
                            <span className="bg-muted px-2 py-1 rounded text-xs font-mono font-bold">#{s.store_rank}</span>
                        </div>

                        <div className="grid grid-cols-2 gap-4 mb-6">
                            <div className="bg-muted/50 p-3 rounded-lg">
                                <div className="text-[10px] uppercase font-bold text-muted-foreground mb-1">Avg P Score</div>
                                <div className="text-xl font-black" style={{ color: getScoreColor(s.avg_p_score) }}>
                                    {s.avg_p_score.toFixed(1)}
                                </div>
                            </div>
                            <div className="bg-secondary/10 p-3 rounded-lg">
                                <div className="text-[10px] uppercase font-bold text-secondary mb-1">Total Revenue</div>
                                <div className="text-xl font-black">{fmtRev(s.total_revenue)}</div>
                            </div>
                        </div>

                        <ul className="space-y-3 mb-6">
                            <li className="flex justify-between text-sm">
                                <span className="text-muted-foreground flex items-center gap-2"><Users size={14} /> Attendance</span>
                                <span className="font-bold">{s.avg_attendance_rate.toFixed(0)}%</span>
                            </li>
                            <li className="flex justify-between text-sm">
                                <span className="text-muted-foreground flex items-center gap-2"><Target size={14} /> Above Target</span>
                                <span className="font-bold">{s.employees_above_target} / {s.total_employees_active}</span>
                            </li>
                            <li className="flex justify-between text-sm">
                                <span className="text-muted-foreground flex items-center gap-2"><AlertTriangle size={14} /> Flagged Sales</span>
                                <span className={`font-bold ${s.total_flagged_sales > 0 ? 'text-orange-500' : ''}`}>{s.total_flagged_sales}</span>
                            </li>
                        </ul>

                        <div className="bg-slate-50 p-3 rounded-lg mb-6 border border-slate-100">
                            <div className="text-[10px] uppercase font-bold text-slate-400 mb-1">Top Performer</div>
                            <div className="flex justify-between items-center text-sm">
                                <span className="font-semibold">{s.top_performer_name || 'N/A'}</span>
                                <span className="text-xs font-bold text-orange-600 px-1.5 py-0.5 bg-orange-50 rounded italic">Score: {s.top_performer_score.toFixed(1)}</span>
                            </div>
                        </div>

                        <button 
                            onClick={() => nav(`/headoffice/store/${s.store_id}`)}
                            className="w-full py-2.5 bg-navy text-white rounded-lg text-sm font-bold flex items-center justify-center gap-2 hover:bg-navy-light transition-colors"
                        >
                            Drill into store <ArrowRight size={16} />
                        </button>
                    </div>
                ))}
            </div>

            {/* Summary Row */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-white p-5 rounded-xl border border-slate-200">
                    <div className="text-xs font-bold text-slate-400 uppercase mb-2">Network Best P-Score</div>
                    <div className="text-lg font-bold">{(data?.stores || []).find(s => s.store_rank === 1)?.store_name || '---'}</div>
                </div>
                <div className="bg-white p-5 rounded-xl border border-slate-200">
                    <div className="text-xs font-bold text-slate-400 uppercase mb-2">Top Revenue Hub</div>
                    <div className="text-lg font-bold">{(data?.stores || []).find(s => s.revenue_rank === 1)?.store_name || '---'}</div>
                </div>
                <div className="bg-white p-5 rounded-xl border border-slate-200">
                    <div className="text-xs font-bold text-slate-400 uppercase mb-2">Attendance Leader</div>
                    <div className="text-lg font-bold">{(data?.stores || []).find(s => s.attendance_rank === 1)?.store_name || '---'}</div>
                </div>
                <div className="bg-white p-5 rounded-xl border border-slate-200">
                    <div className="text-xs font-bold text-slate-400 uppercase mb-2">Total Flagged Sales</div>
                    <div className="text-lg font-bold text-orange-600">
                        {data?.stores.reduce((acc, s) => acc + s.total_flagged_sales, 0)}
                    </div>
                </div>
            </div>
        </div>
    );
}
