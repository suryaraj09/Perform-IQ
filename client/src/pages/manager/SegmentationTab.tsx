import { useState, useEffect, useMemo } from 'react';
import { useApi } from '../../hooks/useApi';
import { useAuth } from '../../context/AuthContext';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ZAxis, ReferenceLine, Legend } from 'recharts';

interface SegmentationEmployee {
    id: string;
    name: string;
    department: string;
    M1: number; M2: number; M3: number; M4: number;
    M5: number; M7: number; M8: number; P: number;
    xValue: number;
    yValue: number;
    cluster: number;
}

interface ClusterCentroid {
    cluster: number;
    label: string;
    M1: number;
    M2: number;
}

interface SegmentationData {
    employees: SegmentationEmployee[];
    clusterCentroids: ClusterCentroid[];
}

interface WeekCombo {
    week_number: number;
    year: number;
}

const METRIC_LABELS: Record<string, string> = {
    P_score: 'P Score',
    M1: 'M1 Revenue',
    M2: 'M2 Basket',
    M3: 'M3 Rating',
    M4: 'M4 Growth',
    M5: 'M5 Stability',
    M7: 'M7 Attendance',
    M8: 'M8 Punctuality',
};

const CLUSTER_LABELS = [
    'High Vol High Basket',
    'High Vol Low Basket',
    'Low Vol High Basket',
    'Low Vol Low Basket'
];

const CLUSTER_COLORS = ['#22C55E', '#3B82F6', '#F59E0B', '#EF4444'];

const NINE_BOX_CELLS = [
    { label: 'Hidden Potential', row: 0, col: 0, action: 'Investigate blockers, reassign or coach' },
    { label: 'Rising Star', row: 0, col: 1, action: 'Accelerate development, assign mentoring role' },
    { label: 'Top Talent', row: 0, col: 2, action: 'Retain & stretch with leadership opportunities', highlight: 'success' },
    { label: 'Developing', row: 1, col: 0, action: 'Structured coaching plan needed' },
    { label: 'Core Performer', row: 1, col: 1, action: 'Maintain engagement, set incremental goals' },
    { label: 'Strong Asset', row: 1, col: 2, action: 'Recognise consistency, prevent stagnation' },
    { label: 'Needs Coaching', row: 2, col: 0, action: 'Priority intervention — escalate to HR', highlight: 'danger' },
    { label: 'Inconsistent', row: 2, col: 1, action: 'Identify root cause of variance' },
    { label: 'Plateaued', row: 2, col: 2, action: 'Re-energise with new challenges or targets' },
];

export default function SegmentationTab() {
    const { activeStoreId } = useAuth();
    const [selectedX, setSelectedX] = useState('P_score');
    const [selectedY, setSelectedY] = useState('M4');
    const [selectedDept, setSelectedDept] = useState('All');
    const [selectedWeek, setSelectedWeek] = useState<WeekCombo | null>(null);

    const { data: weeks } = useApi<WeekCombo[]>('/api/manager/available-weeks', [activeStoreId]);
    
    useEffect(() => {
        if (weeks && weeks.length > 0 && !selectedWeek) {
            setSelectedWeek(weeks[0]);
        }
    }, [weeks, selectedWeek]);

    const segmentationUrl = useMemo(() => {
        if (!selectedWeek) return null;
        const params = new URLSearchParams({
            week: selectedWeek.week_number.toString(),
            year: selectedWeek.year.toString(),
            xMetric: selectedX,
            yMetric: selectedY,
        });
        return `/api/manager/segmentation?${params.toString()}`;
    }, [selectedWeek, selectedX, selectedY]);

    const { data, loading } = useApi<SegmentationData>(segmentationUrl || '', [activeStoreId]);

    const filteredEmployees = useMemo(() => {
        if (!data) return [];
        if (selectedDept === 'All') return data.employees;
        return data.employees.filter(e => e.department === selectedDept);
    }, [data, selectedDept]);

    const getCellEmployees = (row: number, col: number) => {
        return filteredEmployees.filter(emp => {
            const rowIdx = emp.yValue > 66 ? 0 : emp.yValue > 33 ? 1 : 2;
            const colIdx = emp.xValue > 66 ? 2 : emp.xValue > 33 ? 1 : 0;
            return rowIdx === row && colIdx === col;
        });
    };

    if (!selectedWeek) return <div style={{ padding: 40, textAlign: 'center' }}>Loading weeks...</div>;

    return (
        <div className="animate-in">
            {/* Filters Bar */}
            <div style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 6 }}>Analysis Week</label>
                    <select 
                        value={selectedWeek ? `${selectedWeek.week_number}-${selectedWeek.year}` : ''}
                        onChange={(e) => {
                            const [w, y] = e.target.value.split('-').map(Number);
                            setSelectedWeek({ week_number: w, year: y });
                        }}
                        style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border)', background: 'var(--bg-card)', color: 'var(--text-primary)', fontSize: '0.9rem', outline: 'none' }}
                    >
                        {weeks?.map(wk => (
                            <option key={`${wk.week_number}-${wk.year}`} value={`${wk.week_number}-${wk.year}`}>
                                Week {wk.week_number}, {wk.year}
                            </option>
                        ))}
                    </select>
                </div>

                <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 6 }}>X-Axis Metric</label>
                    <select 
                        value={selectedX}
                        onChange={(e) => setSelectedX(e.target.value)}
                        style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border)', background: 'var(--bg-card)', color: 'var(--text-primary)', fontSize: '0.9rem', outline: 'none' }}
                    >
                        {Object.entries(METRIC_LABELS).map(([k, v]) => (
                            <option key={k} value={k} disabled={k === selectedY}>{v}</option>
                        ))}
                    </select>
                </div>

                <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 6 }}>Y-Axis Metric</label>
                    <select 
                        value={selectedY}
                        onChange={(e) => setSelectedY(e.target.value)}
                        style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border)', background: 'var(--bg-card)', color: 'var(--text-primary)', fontSize: '0.9rem', outline: 'none' }}
                    >
                        {Object.entries(METRIC_LABELS).map(([k, v]) => (
                            <option key={k} value={k} disabled={k === selectedX}>{v}</option>
                        ))}
                    </select>
                </div>

                <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
                    {['All', "Women's Wear", "Men's Wear", 'Accessories'].map(dept => (
                        <button
                            key={dept}
                            onClick={() => setSelectedDept(dept)}
                            style={{
                                padding: '8px 16px', borderRadius: 20, border: selectedDept === dept ? 'none' : '1px solid var(--border)',
                                background: selectedDept === dept ? '#F97316' : 'transparent',
                                color: selectedDept === dept ? '#fff' : 'var(--text-secondary)',
                                fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer', transition: 'all 0.2s'
                            }}
                        >
                            {dept}
                        </button>
                    ))}
                </div>
            </div>

            {loading ? <div style={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>Calculating segmentation...</div> : (
                <>
                    {/* 9-Box Grid Title */}
                    <div style={{ marginBottom: 16 }}>
                        <h3 style={{ fontSize: '1.2rem', fontWeight: 700 }}>Performance 9-Box Grid</h3>
                        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{METRIC_LABELS[selectedX]} vs {METRIC_LABELS[selectedY]} — {filteredEmployees.length} employees</p>
                    </div>

                    {/* 9-Box Grid */}
                    <div style={{ 
                        display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gridTemplateRows: 'repeat(3, 1fr)',
                        gap: 12, height: 600, marginBottom: 40, position: 'relative'
                    }}>
                        {/* Axis Labels */}
                        <div style={{ position: 'absolute', bottom: -25, left: '50%', transform: 'translateX(-50%)', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', display: 'flex', gap: 40 }}>
                            <span>Low {METRIC_LABELS[selectedX]}</span>
                            <span>Mid</span>
                            <span>High</span>
                        </div>
                        <div style={{ position: 'absolute', top: '50%', left: -45, transform: 'translateY(-50%) rotate(-90deg)', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', display: 'flex', gap: 40 }}>
                            <span>High {METRIC_LABELS[selectedY]}</span>
                            <span>Mid</span>
                            <span>Low</span>
                        </div>

                        {NINE_BOX_CELLS.map((cell, idx) => {
                            const CellEmps = getCellEmployees(cell.row, cell.col);
                            return (
                                <div 
                                    key={idx}
                                    style={{
                                        background: cell.highlight === 'success' ? 'rgba(34, 197, 94, 0.08)' : cell.highlight === 'danger' ? 'rgba(239, 68, 68, 0.08)' : 'var(--bg-card)',
                                        border: '1px solid var(--border)', borderRadius: 12, padding: 16, display: 'flex', flexDirection: 'column',
                                        boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)', transition: 'transform 0.2s', position: 'relative', overflow: 'hidden'
                                    }}
                                >
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                                        <div>
                                            <div style={{ fontWeight: 800, fontSize: '0.95rem', color: cell.highlight === 'success' ? '#166534' : cell.highlight === 'danger' ? '#991b1b' : 'var(--text-primary)' }}>{cell.label}</div>
                                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{CellEmps.length} employees</div>
                                        </div>
                                    </div>
                                    
                                    {/* Action Text */}
                                    <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontStyle: 'italic', marginBottom: 12, lineHeight: 1.3 }}>
                                        {cell.action}
                                    </div>

                                    {/* Employee Bubbles */}
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, maxHeight: 100, overflowY: 'auto' }}>
                                        {CellEmps.map(emp => (
                                            <div 
                                                key={emp.id}
                                                title={`${emp.name} (${emp.department})\n${METRIC_LABELS[selectedX]}: ${emp.xValue}\n${METRIC_LABELS[selectedY]}: ${emp.yValue}\nP Score: ${emp.P}`}
                                                style={{
                                                    width: 28, height: 28, borderRadius: '50%', background: CLUSTER_COLORS[emp.cluster] || '#888',
                                                    display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: '0.65rem', fontWeight: 800,
                                                    cursor: 'help', border: '2px solid #fff', boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                                                }}
                                            >
                                                {emp.name.split(' ').map(n => n[0]).join('')}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            );
                        })}
                    </div>

                    {/* K-Means Scatter Chart */}
                    <div className="card">
                        <div className="card-header">
                            <div>
                                <span className="card-title">Revenue × Basket Cluster Map</span>
                                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
                                    K-Means Clustering ($k=4$) · Bubble size indicates P Score
                                </div>
                            </div>
                        </div>
                        <div className="chart-container" style={{ height: 500 }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                                    <XAxis type="number" dataKey="M1" name="Revenue vs Target" domain={[0, 100]} label={{ value: 'Revenue vs Target (M1)', position: 'bottom', offset: 0, fill: 'var(--text-muted)', fontSize: 12 }} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                                    <YAxis type="number" dataKey="M2" name="Basket Performance" domain={[0, 100]} label={{ value: 'Basket Performance (M2)', angle: -90, position: 'insideLeft', fill: 'var(--text-muted)', fontSize: 12 }} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                                    <ZAxis type="number" dataKey="P" range={[100, 1000]} name="P Score" />
                                    <Tooltip 
                                        content={({ payload }) => {
                                            if (!payload?.[0]) return null;
                                            const d = payload[0].payload;
                                            return (
                                                <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 12, padding: 16, boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }}>
                                                    <div style={{ fontWeight: 800, marginBottom: 4 }}>{d.name}</div>
                                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 8 }}>{d.department}</div>
                                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                                                        <div>
                                                            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>REVENUE (M1)</div>
                                                            <div style={{ fontWeight: 700 }}>{d.M1}</div>
                                                        </div>
                                                        <div>
                                                            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>BASKET (M2)</div>
                                                            <div style={{ fontWeight: 700 }}>{d.M2}</div>
                                                        </div>
                                                        <div>
                                                            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>P SCORE</div>
                                                            <div style={{ fontWeight: 800, color: '#F97316' }}>{d.P}</div>
                                                        </div>
                                                        <div>
                                                            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>CLUSTER</div>
                                                            <div style={{ fontWeight: 700, color: CLUSTER_COLORS[d.cluster] }}>{CLUSTER_LABELS[d.cluster]}</div>
                                                        </div>
                                                    </div>
                                                </div>
                                            );
                                        }}
                                    />
                                    <Legend verticalAlign="top" height={36}/>
                                    {CLUSTER_LABELS.map((label, idx) => (
                                        <Scatter 
                                            key={label}
                                            name={label} 
                                            data={filteredEmployees.filter(e => e.cluster === idx)} 
                                            fill={CLUSTER_COLORS[idx]} 
                                        />
                                    ))}
                                    <ReferenceLine x={50} stroke="var(--border)" strokeDasharray="3 3" />
                                    <ReferenceLine y={50} stroke="var(--border)" strokeDasharray="3 3" />
                                </ScatterChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
