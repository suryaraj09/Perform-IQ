import { useApi } from '../../hooks/useApi';
import { useState } from 'react';
import { Trophy, Star, User } from 'lucide-react';

interface LeaderboardItem {
    rank: number;
    employeeId: string;
    name: string;
    department: string;
    storeId: string;
    storeName: string;
    pScore: number;
    weeklyRevenue: number;
    level: number;
    levelLabel: string;
    xp: number;
}

interface LeaderboardData {
    weekNumber: number;
    leaderboard: LeaderboardItem[];
}

// ISO Week helpers
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

const STORE_COLORS: Record<string, string> = {
    'S001': 'bg-orange-100 text-orange-700 border-orange-200',
    'S002': 'bg-blue-100 text-blue-700 border-blue-200',
    'S003': 'bg-green-100 text-green-700 border-green-200',
};

const LEVEL_COLORS: Record<string, string> = {
    'Champion': 'bg-purple-100 text-purple-700',
    'Expert': 'bg-blue-100 text-blue-700',
    'Performer': 'bg-green-100 text-green-700',
    'Associate': 'bg-slate-100 text-slate-700',
    'Rookie': 'bg-slate-50 text-slate-400',
};

export default function WarehouseLeaderboard() {
    const weekOptions = getWeekOptions(8);
    const [selectedWeek, setSelectedWeek] = useState(weekOptions[0]);
    
    const { data, loading } = useApi<LeaderboardData>(
        `/api/headoffice/warehouse/global-leaderboard?week=${selectedWeek.week}&year=${selectedWeek.year}&limit=10`, 
        [selectedWeek]
    );

    if (loading) return <div className="p-8 text-center text-muted-foreground">Loading Global Leaderboard...</div>;

    const top3 = data?.leaderboard.slice(0, 3) || [];

    // Rearrange for podium: [2, 1, 3]
    const podiumOrder = top3.length === 3 ? [top3[1], top3[0], top3[2]] : top3;

    return (
        <div className="dashboard-container p-6 max-w-6xl mx-auto">
            <header className="mb-12 flex justify-between items-end">
                <div>
                    <h1 className="text-3xl font-black italic tracking-tight text-navy">GLOBAL ELITE</h1>
                    <p className="text-muted-foreground font-medium uppercase text-xs tracking-widest">Network-wide Top 10 Performers — Week {data?.weekNumber}</p>
                </div>
                <div className="flex items-center gap-3">
                    <select 
                        className="bg-card border-2 border-navy/10 p-2 rounded-xl text-sm font-bold shadow-sm"
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

            {/* Podium Section */}
            <div className="flex justify-center items-end gap-4 md:gap-8 mb-16 px-4">
                {podiumOrder.map((emp) => {
                    const isFirst = emp.rank === 1;
                    const isSecond = emp.rank === 2;
                    const height = isFirst ? 'h-64' : isSecond ? 'h-48' : 'h-40';
                    const color = isFirst ? 'bg-yellow-400' : isSecond ? 'bg-slate-300' : 'bg-orange-300';
                    
                    return (
                        <div key={emp.employeeId} className="flex flex-col items-center group">
                            <div className={`relative mb-4 transition-transform group-hover:scale-105 duration-300`}>
                                <div className={`w-16 h-16 md:w-20 md:h-20 rounded-full border-4 ${isFirst ? 'border-yellow-400' : 'border-slate-200'} overflow-hidden bg-slate-100 flex items-center justify-center shadow-lg`}>
                                    <User size={isFirst ? 40 : 32} className="text-slate-300" />
                                </div>
                                <div className={`absolute -bottom-2 -right-2 w-8 h-8 rounded-full ${color} flex items-center justify-center border-2 border-white shadow-sm font-black text-sm`}>
                                    {emp.rank}
                                </div>
                            </div>
                            <div className="text-center mb-4">
                                <div className="font-black text-sm truncate max-w-[120px]">{emp.name}</div>
                                <div className={`text-[10px] font-bold px-2 py-0.5 rounded-full border inline-block mt-1 ${STORE_COLORS[emp.storeId]}`}>
                                    {emp.storeName.split(' ')[2]}
                                </div>
                            </div>
                            <div className={`${height} w-24 md:w-32 ${isFirst ? 'bg-navy' : 'bg-navy-light'} rounded-t-2xl flex flex-col items-center justify-start pt-6 shadow-2xl relative overflow-hidden`}>
                                <div className="text-white font-black text-2xl md:text-3xl mb-1">{emp.pScore.toFixed(0)}</div>
                                <div className="text-white/50 text-[10px] font-bold uppercase tracking-widest">P-Score</div>
                                {isFirst && (
                                    <div className="absolute -bottom-4 opacity-10">
                                        <Trophy size={100} color="#fff" />
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Leaderboard Table */}
            <div className="bg-white rounded-2xl shadow-xl border border-slate-100 overflow-hidden">
                <table className="w-full">
                    <thead className="bg-slate-50 border-b border-slate-100">
                        <tr>
                            <th className="px-6 py-4 text-left text-[10px] font-black uppercase text-slate-400 tracking-widest">Rank</th>
                            <th className="px-6 py-4 text-left text-[10px] font-black uppercase text-slate-400 tracking-widest">Employee</th>
                            <th className="px-6 py-4 text-left text-[10px] font-black uppercase text-slate-400 tracking-widest">Store</th>
                            <th className="px-6 py-4 text-left text-[10px] font-black uppercase text-slate-400 tracking-widest">Department</th>
                            <th className="px-6 py-4 text-center text-[10px] font-black uppercase text-slate-400 tracking-widest">P-Score</th>
                            <th className="px-6 py-4 text-center text-[10px] font-black uppercase text-slate-400 tracking-widest text-secondary">Revenue</th>
                            <th className="px-6 py-4 text-right text-[10px] font-black uppercase text-slate-400 tracking-widest">Level</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-50">
                        {data?.leaderboard.map((emp) => {
                            const bg = emp.rank === 1 ? 'bg-yellow-50/50' : emp.rank === 2 ? 'bg-slate-50/50' : emp.rank === 3 ? 'bg-orange-50/50' : 'hover:bg-slate-50/30';
                            
                            return (
                                <tr key={emp.employeeId} className={`transition-colors ${bg}`}>
                                    <td className="px-6 py-4">
                                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-black text-sm ${emp.rank <= 3 ? 'bg-navy text-white' : 'text-slate-400'}`}>
                                            {emp.rank}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-3">
                                            <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 font-bold border-2 border-white shadow-sm">
                                                {emp.name.split(' ').map(n => n[0]).join('')}
                                            </div>
                                            <div>
                                                <div className="font-bold text-sm text-slate-900">{emp.name}</div>
                                                <div className="text-[10px] font-medium text-slate-500 flex items-center gap-1">
                                                    <Star size={10} className="text-yellow-500 fill-yellow-500" /> {emp.xp.toLocaleString()} XP
                                                </div>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-sm">
                                        <span className={`px-2 py-1 rounded-md text-[10px] font-black uppercase border ${STORE_COLORS[emp.storeId]}`}>
                                            {emp.storeName.split(' ')[2]}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-sm text-slate-600 font-medium">{emp.department}</td>
                                    <td className="px-6 py-4 text-center">
                                        <div className="text-lg font-black text-navy">{emp.pScore.toFixed(1)}</div>
                                    </td>
                                    <td className="px-6 py-4 text-center font-bold text-slate-700">
                                        ₹{emp.weeklyRevenue.toLocaleString('en-IN')}
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <span className={`px-2 py-1 rounded text-[10px] font-black uppercase ${LEVEL_COLORS[emp.levelLabel] || 'bg-slate-100 text-slate-600'}`}>
                                            {emp.levelLabel}
                                        </span>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
