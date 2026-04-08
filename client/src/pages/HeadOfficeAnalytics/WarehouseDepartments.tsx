import { useApi } from '../../hooks/useApi';
import { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { BarChart3, ShoppingBag, Users, Layers } from 'lucide-react';

interface DeptStat {
    department: string;
    avgPScore: number;
    avgRevenue: number;
    avgBasketSize: number;
    avgAttendance: number;
    headcount: number;
    employees_above_target: number;
}

interface StoreDeptData {
    storeId: string;
    storeName: string;
    departments: DeptStat[];
}

interface WarehouseDeptData {
    weekNumber: number;
    year: number;
    departments: string[];
    stores: StoreDeptData[];
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
    'S001': '#F97316',
    'S002': '#185FA5',
    'S003': '#3B6D11',
};

export default function WarehouseDepartments() {
    const weekOptions = getWeekOptions(8);
    const [selectedWeek, setSelectedWeek] = useState(weekOptions[0]);
    
    const { data: deptData, loading } = useApi<WarehouseDeptData>(
        `/api/headoffice/warehouse/departments?week=${selectedWeek.week}&year=${selectedWeek.year}`, 
        [selectedWeek]
    );

    if (loading) return <div className="p-8 text-center text-muted-foreground">Loading Department Analytics...</div>;

    // Transform data for Grouped Bar Charts
    const transformForGroupedBar = (key: keyof DeptStat) => {
        return deptData?.departments.map(dept => {
            const point: any = { name: dept };
            deptData.stores.forEach(s => {
                const stat = s.departments.find(d => d.department === dept);
                if (stat) point[s.storeName] = stat[key];
            });
            return point;
        });
    };

    const pScoreData = transformForGroupedBar('avgPScore');
    const basketData = transformForGroupedBar('avgBasketSize');
    const attendanceData = transformForGroupedBar('avgAttendance');

    return (
        <div className="dashboard-container p-6">
            <header className="mb-8 flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold flex items-center gap-3">
                        <Layers className="text-navy" size={24} />
                        Cross-Store Department Analysis
                    </h1>
                    <p className="text-muted-foreground">Benchmarking departments across the retail network</p>
                </div>
                <div className="flex items-center gap-3">
                    <span className="text-sm font-medium">Week:</span>
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

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-8">
                {/* Chart 1: Avg P Score per Dept per Store */}
                <div className="card p-6">
                    <div className="flex items-center gap-3 mb-6">
                        <BarChart3 size={18} className="text-navy" />
                        <h3 className="font-bold">Avg Department P-Score</h3>
                    </div>
                    <div className="h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={pScoreData}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                                <XAxis dataKey="name" style={{ fontSize: '0.8rem' }} axisLine={false} tickLine={false} />
                                <YAxis domain={[0, 100]} style={{ fontSize: '0.75rem' }} axisLine={false} tickLine={false} />
                                <Tooltip cursor={{ fill: '#f8fafc' }} contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }} />
                                <Legend wrapperStyle={{ fontSize: '0.8rem', paddingTop: '1rem' }} />
                                {deptData?.stores.map(s => (
                                    <Bar key={s.storeId} dataKey={s.storeName} fill={STORE_COLORS[s.storeId]} radius={[4, 4, 0, 0]} />
                                ))}
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Chart 2: Avg Basket Size per Dept per Store */}
                <div className="card p-6">
                    <div className="flex items-center gap-3 mb-6">
                        <ShoppingBag size={18} className="text-secondary" />
                        <h3 className="font-bold">Avg Basket Size (₹)</h3>
                    </div>
                    <div className="h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={basketData}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                                <XAxis dataKey="name" style={{ fontSize: '0.8rem' }} axisLine={false} tickLine={false} />
                                <YAxis style={{ fontSize: '0.75rem' }} tickFormatter={(v) => `₹${v/1000}k`} axisLine={false} tickLine={false} />
                                <Tooltip cursor={{ fill: '#f8fafc' }} formatter={(v: any) => `₹${v.toLocaleString('en-IN')}`} contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }} />
                                <Legend wrapperStyle={{ fontSize: '0.8rem', paddingTop: '1rem' }} />
                                {deptData?.stores.map(s => (
                                    <Bar key={s.storeId} dataKey={s.storeName} fill={STORE_COLORS[s.storeId]} radius={[4, 4, 0, 0]} />
                                ))}
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Chart 3: Avg Attendance per Dept per Store */}
                <div className="card p-6">
                    <div className="flex items-center gap-3 mb-6">
                        <Users size={18} className="text-green-600" />
                        <h3 className="font-bold">Avg Attendance (%)</h3>
                    </div>
                    <div className="h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={attendanceData}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                                <XAxis dataKey="name" style={{ fontSize: '0.8rem' }} axisLine={false} tickLine={false} />
                                <YAxis domain={[0, 100]} style={{ fontSize: '0.75rem' }} tickFormatter={(v) => `${v}%`} axisLine={false} tickLine={false} />
                                <Tooltip cursor={{ fill: '#f8fafc' }} contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }} />
                                <Legend wrapperStyle={{ fontSize: '0.8rem', paddingTop: '1rem' }} />
                                {deptData?.stores.map(s => (
                                    <Bar key={s.storeId} dataKey={s.storeName} fill={STORE_COLORS[s.storeId]} radius={[4, 4, 0, 0]} />
                                ))}
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Table: Headcount per Dept per Store */}
                <div className="card p-6">
                    <div className="flex items-center gap-3 mb-6">
                        <Users size={18} className="text-slate-600" />
                        <h3 className="font-bold">Employee Headcount (Staff Strength)</h3>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead className="bg-slate-50 text-slate-500 font-bold uppercase text-[10px] tracking-wider">
                                <tr>
                                    <th className="px-4 py-3 text-left">Department</th>
                                    {deptData?.stores.map(s => (
                                        <th key={s.storeId} className="px-4 py-3 text-center" style={{ color: STORE_COLORS[s.storeId] }}>
                                            {s.storeName.split(' ').pop()}
                                        </th>
                                    ))}
                                    <th className="px-4 py-3 text-center bg-slate-100 italic">Total</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {deptData?.departments.map(dept => {
                                    const total = deptData.stores.reduce((acc, s) => acc + (s.departments.find(d => d.department === dept)?.headcount || 0), 0);
                                    return (
                                        <tr key={dept} className="hover:bg-slate-50/50">
                                            <td className="px-4 py-4 font-bold">{dept}</td>
                                            {deptData.stores.map(s => (
                                                <td key={s.storeId} className="px-4 py-4 text-center text-slate-600 font-medium">
                                                    {s.departments.find(d => d.department === dept)?.headcount || 0}
                                                </td>
                                            ))}
                                            <td className="px-4 py-4 text-center font-black bg-slate-50">{total}</td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
}
