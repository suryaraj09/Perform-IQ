import { useState, useEffect } from 'react';
import { api } from '../../utils/api';
import { BarChart3, RefreshCw } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface BenchmarkRow {
  store_id: string;
  store_name: string;
  department: string;
  date: string;
  avg_p_score: number;
  dept_rank: number;
}

interface BenchmarkResponse {
  startDate: string;
  endDate: string;
  rows: BenchmarkRow[];
}

const STORE_COLORS = ['#06B6D4', '#F97316', '#A855F7', '#22C55E', '#EF4444', '#3B82F6'];

export default function WHDeptBenchmark() {
  const [data, setData] = useState<BenchmarkRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 7);
    return d.toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await api<BenchmarkResponse>(
        `/api/warehouse/dept-benchmarks?start_date=${startDate}&end_date=${endDate}`
      );
      setData(res.rows || []);
    } catch (e) {
      console.error('Failed to load benchmarks:', e);
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [startDate, endDate]);

  // Transform data for grouped bar chart:
  // Each department is a group, with one bar per store
  const stores = [...new Set(data.map((r) => r.store_name || r.store_id))];
  const departments = [...new Set(data.map((r) => r.department))];

  const chartData = departments.map((dept) => {
    const entry: Record<string, string | number> = { department: dept };
    data
      .filter((r) => r.department === dept)
      .forEach((r) => {
        const storeName = r.store_name || r.store_id;
        entry[storeName] = Math.round(r.avg_p_score * 10) / 10;
      });
    return entry;
  });

  return (
    <div className="wh-page">
      <div className="wh-page-header">
        <div>
          <h1 className="wh-page-title">Department Benchmarks</h1>
          <p className="wh-page-subtitle">Average P-Score by department across stores</p>
        </div>
        <button className="wh-btn wh-btn-secondary" onClick={fetchData} disabled={loading}>
          <RefreshCw size={16} className={loading ? 'wh-spin' : ''} />
          Refresh
        </button>
      </div>

      <div className="wh-filters">
        <div className="wh-filter-group">
          <label>Start Date</label>
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="wh-input" />
        </div>
        <div className="wh-filter-group">
          <label>End Date</label>
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="wh-input" />
        </div>
      </div>

      {/* Chart */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <span className="card-title">P-Score Comparison by Department</span>
        </div>
        {loading ? (
          <div className="wh-loading">Loading chart...</div>
        ) : chartData.length === 0 ? (
          <div className="wh-empty">
            <BarChart3 size={40} />
            <p>No benchmark data available.</p>
          </div>
        ) : (
          <div style={{ width: '100%', height: 400 }}>
            <ResponsiveContainer>
              <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="department" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
                <YAxis domain={[0, 100]} tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
                <Tooltip
                  contentStyle={{
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border)',
                    borderRadius: 12,
                    color: 'var(--text-primary)',
                    fontSize: '0.85rem',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }} />
                {stores.map((store, idx) => (
                  <Bar
                    key={store}
                    dataKey={store}
                    fill={STORE_COLORS[idx % STORE_COLORS.length]}
                    radius={[6, 6, 0, 0]}
                    maxBarSize={48}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Ranking Table */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Department Rankings</span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{data.length} records</span>
        </div>
        {data.length > 0 && (
          <div className="wh-table-wrap">
            <table className="wh-table">
              <thead>
                <tr>
                  <th>Department</th>
                  <th>Store</th>
                  <th>Avg P-Score</th>
                  <th>Rank</th>
                </tr>
              </thead>
              <tbody>
                {data.map((row, i) => (
                  <tr key={`${row.store_id}-${row.department}-${i}`}>
                    <td style={{ fontWeight: 600 }}>{row.department}</td>
                    <td><span className="wh-store-badge">{row.store_name || row.store_id}</span></td>
                    <td>
                      <span className={`wh-score ${row.avg_p_score >= 70 ? 'high' : row.avg_p_score >= 40 ? 'mid' : 'low'}`}>
                        {row.avg_p_score.toFixed(1)}
                      </span>
                    </td>
                    <td>
                      <span className={`wh-rank-badge ${row.dept_rank === 1 ? 'gold' : row.dept_rank === 2 ? 'silver' : 'bronze'}`}>
                        #{row.dept_rank}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
