import { useApi } from '../../hooks/useApi';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { TrendingUp, BarChart3, Activity, Users } from 'lucide-react';

interface TrendPoint {
    week: string;
    weekNumber: number;
    year: number;
    avgPScore: number;
    totalRevenue: number;
    avgAttendance: number;
    storeRank: number;
    rank?: number; // Added for flexible access
}

interface StoreTrend {
    storeId: string;
    storeName: string;
    trend: TrendPoint[];
    rankHistory: Array<{
        week: string;
        rank: number;
        avgPScore: number;
        totalRevenue: number;
    }>;
}

interface WarehouseTrendsData {
    weeks: string[];
    stores: StoreTrend[];
}

const STORE_COLORS: Record<string, string> = {
    'S001': '#F97316', // orange
    'S002': '#185FA5', // blue
    'S003': '#3B6D11', // green
};

export default function WarehouseTrends() {
    const { data: trendData, loading } = useApi<WarehouseTrendsData>('/api/headoffice/warehouse/trends?weeks=8');
    const { data: rankHistoryData, loading: loadingRanks } = useApi<WarehouseTrendsData>('/api/headoffice/warehouse/store-ranking-history?weeks=8');

    if (loading || loadingRanks) return <div className="p-8 text-center">Loading Trend Data...</div>;

    // Transform trendData for charts
    const pScoreData = trendData?.weeks.map(w => {
        const point: any = { week: w.split(' ')[0] };
        trendData.stores.forEach(s => {
            const trend = s.trend.find(t => t.week === w);
            if (trend) point[s.storeName] = trend.avgPScore;
        });
        return point;
    });

    const revenueData = trendData?.weeks.map(w => {
        const point: any = { week: w.split(' ')[0] };
        trendData.stores.forEach(s => {
            const trend = s.trend.find(t => t.week === w);
            if (trend) point[s.storeName] = trend.totalRevenue;
        });
        return point;
    });

    const attendanceData = trendData?.weeks.map(w => {
        const point: any = { week: w.split(' ')[0] };
        trendData.stores.forEach(s => {
            const trend = s.trend.find(t => t.week === w);
            if (trend) point[s.storeName] = trend.avgAttendance;
        });
        return point;
    });

    // Ranking Data
    const rankingData = rankHistoryData?.weeks.map(w => {
        const point: any = { week: w };
        rankHistoryData.stores.forEach(s => {
            const history = s.rankHistory.find(h => h.week === w);
            if (history) point[s.storeName] = history.rank;
        });
        return point;
    });

    return (
        <div className="dashboard-container p-6">
            <header className="mb-8">
                <h1 className="text-2xl font-bold flex items-center gap-3">
                    <Activity className="text-navy" size={24} />
                    Network Performance Trends
                </h1>
                <p className="text-muted-foreground">Historical analysis over last 8 weeks</p>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                {/* Chart 1: Avg P Score Trend */}
                <div className="card p-6">
                    <div className="flex items-center gap-3 mb-6">
                        <TrendingUp size={18} className="text-navy" />
                        <h3 className="font-bold">Avg Productivity Score Trend</h3>
                    </div>
                    <div className="h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={pScoreData}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                                <XAxis dataKey="week" style={{ fontSize: '0.75rem' }} />
                                <YAxis domain={[0, 100]} style={{ fontSize: '0.75rem' }} />
                                <Tooltip contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }} />
                                <Legend wrapperStyle={{ fontSize: '0.8rem', paddingTop: '1rem' }} />
                                {trendData?.stores.map(s => (
                                    <Line 
                                        key={s.storeId}
                                        type="monotone"
                                        dataKey={s.storeName}
                                        stroke={STORE_COLORS[s.storeId]}
                                        strokeWidth={3}
                                        dot={{ r: 4 }}
                                        activeDot={{ r: 6 }}
                                    />
                                ))}
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Chart 2: Total Revenue Trend */}
                <div className="card p-6">
                    <div className="flex items-center gap-3 mb-6">
                        <BarChart3 size={18} className="text-secondary" />
                        <h3 className="font-bold">Total Revenue Trend (₹)</h3>
                    </div>
                    <div className="h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={revenueData}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                                <XAxis dataKey="week" style={{ fontSize: '0.75rem' }} />
                                <YAxis style={{ fontSize: '0.75rem' }} tickFormatter={(v) => `₹${v/100000}L`} />
                                <Tooltip contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }} formatter={(v: any) => `₹${v.toLocaleString('en-IN')}`} />
                                <Legend wrapperStyle={{ fontSize: '0.8rem', paddingTop: '1rem' }} />
                                {trendData?.stores.map(s => (
                                    <Area 
                                        key={s.storeId}
                                        type="monotone"
                                        dataKey={s.storeName}
                                        stroke={STORE_COLORS[s.storeId]}
                                        fill={STORE_COLORS[s.storeId]}
                                        fillOpacity={0.1}
                                        strokeWidth={3}
                                    />
                                ))}
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Chart 3: Position/Rank Over Time (Slope Chart) */}
                <div className="card p-6 bg-slate-900 text-white">
                    <div className="flex items-center gap-3 mb-6">
                        <TrendingUp size={18} className="text-yellow-400" />
                        <h3 className="font-bold">Store Ranking Position</h3>
                    </div>
                    <div className="h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={rankingData}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" />
                                <XAxis dataKey="week" style={{ fontSize: '0.75rem' }} tick={{ fill: '#94a3b8' }} />
                                <YAxis domain={[1, 3]} reversed style={{ fontSize: '0.75rem' }} tick={{ fill: '#94a3b8' }} ticks={[1, 2, 3]} />
                                <Tooltip 
                                    contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: 8 }}
                                    itemStyle={{ color: '#fff' }}
                                />
                                <Legend wrapperStyle={{ fontSize: '0.8rem', paddingTop: '1rem' }} />
                                {rankHistoryData?.stores.map(s => (
                                    <Line 
                                        key={s.storeId}
                                        type="monotone"
                                        dataKey={s.storeName}
                                        stroke={STORE_COLORS[s.storeId]}
                                        strokeWidth={4}
                                        dot={{ r: 6, fill: STORE_COLORS[s.storeId] }}
                                        activeDot={{ r: 8 }}
                                    />
                                ))}
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                    <div className="mt-4 text-[10px] text-slate-400 text-center uppercase tracking-widest">
                        Rank 1 at top (Best) — Line going up indicates improvement
                    </div>
                </div>

                {/* Chart 4: Attendance Trend */}
                <div className="card p-6">
                    <div className="flex items-center gap-3 mb-6">
                        <Users size={18} className="text-green-600" />
                        <h3 className="font-bold">Avg Attendance Rate (%)</h3>
                    </div>
                    <div className="h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={attendanceData}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                                <XAxis dataKey="week" style={{ fontSize: '0.75rem' }} />
                                <YAxis domain={[0, 100]} style={{ fontSize: '0.75rem' }} />
                                <Tooltip contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }} />
                                <Legend wrapperStyle={{ fontSize: '0.8rem', paddingTop: '1rem' }} />
                                {trendData?.stores.map(s => (
                                    <Line 
                                        key={s.storeId}
                                        type="monotone"
                                        dataKey={s.storeName}
                                        stroke={STORE_COLORS[s.storeId]}
                                        strokeWidth={3}
                                        dot={{ r: 2 }}
                                    />
                                ))}
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>
        </div>
    );
}
