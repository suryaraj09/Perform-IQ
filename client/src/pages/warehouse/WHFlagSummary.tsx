import { useState, useEffect } from 'react';
import { api } from '../../utils/api';
import { Flag, RefreshCw, AlertTriangle, Zap, MapPin, ShoppingCart } from 'lucide-react';

interface FlagLogRow {
  store_id: string;
  store_name: string;
  flag_type: string;
  date: string;
  count: number;
}

interface FlagResponse {
  startDate: string;
  endDate: string;
  rows: FlagLogRow[];
}

const FLAG_META: Record<string, { label: string; icon: typeof Flag; color: string }> = {
  HIGH_SALE_AMOUNT: { label: 'High Amount', icon: AlertTriangle, color: '#EF4444' },
  NO_ACTIVE_SESSION: { label: 'No Active Session', icon: MapPin, color: '#EAB308' },
  RAPID_SUBMISSION: { label: 'Rapid Submission', icon: Zap, color: '#A855F7' },
  HIGH_ITEM_COUNT: { label: 'High Item Count', icon: ShoppingCart, color: '#3B82F6' },
};

export default function WHFlagSummary() {
  const [data, setData] = useState<FlagLogRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return d.toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await api<FlagResponse>(
        `/api/warehouse/flag-summary?start_date=${startDate}&end_date=${endDate}`
      );
      setData(res.rows || []);
    } catch (e) {
      console.error('Failed to load flag summary:', e);
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [startDate, endDate]);

  // Group by flag type for summary cards
  const typeTotals: Record<string, number> = {};
  data.forEach((r) => {
    typeTotals[r.flag_type] = (typeTotals[r.flag_type] || 0) + r.count;
  });

  const totalFlags = Object.values(typeTotals).reduce((s, c) => s + c, 0);

  return (
    <div className="wh-page">
      <div className="wh-page-header">
        <div>
          <h1 className="wh-page-title">Flag Summary</h1>
          <p className="wh-page-subtitle">Sale flag breakdown by type and store</p>
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

      {/* Flag type summary cards */}
      <div className="stats-grid" style={{ marginBottom: 24 }}>
        {Object.entries(FLAG_META).map(([key, meta]) => {
          const count = typeTotals[key] || 0;
          const Icon = meta.icon;
          const pct = totalFlags > 0 ? ((count / totalFlags) * 100).toFixed(0) : '0';
          return (
            <div className="stat-card" key={key}>
              <div className="stat-icon" style={{ background: `${meta.color}20`, color: meta.color }}>
                <Icon size={20} />
              </div>
              <div className="stat-value">{count}</div>
              <div className="stat-label">{meta.label}</div>
              <div className="stat-change" style={{ color: meta.color }}>{pct}% of total</div>
            </div>
          );
        })}
      </div>

      {/* Detail Table */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Flag Log Details</span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{data.length} records</span>
        </div>

        {loading ? (
          <div className="wh-loading">Loading flag data...</div>
        ) : data.length === 0 ? (
          <div className="wh-empty">
            <Flag size={40} />
            <p>No flag data available for this date range.</p>
          </div>
        ) : (
          <div className="wh-table-wrap">
            <table className="wh-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Store</th>
                  <th>Flag Type</th>
                  <th>Count</th>
                </tr>
              </thead>
              <tbody>
                {data.map((row, i) => {
                  const meta = FLAG_META[row.flag_type];
                  return (
                    <tr key={`${row.store_id}-${row.flag_type}-${row.date}-${i}`}>
                      <td className="wh-cell-date">{row.date}</td>
                      <td><span className="wh-store-badge">{row.store_name || row.store_id}</span></td>
                      <td>
                        <span className="wh-flag-type" style={{ color: meta?.color || 'var(--text-primary)' }}>
                          {meta?.label || row.flag_type}
                        </span>
                      </td>
                      <td style={{ fontWeight: 700 }}>{row.count}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
