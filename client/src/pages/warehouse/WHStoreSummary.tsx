import { useState, useEffect } from 'react';
import { api } from '../../utils/api';
import { Database, TrendingUp, ShoppingBag, Flag, RefreshCw } from 'lucide-react';

interface StoreSummaryRow {
  store_id: string;
  store_name: string;
  date: string;
  avg_p_score: number;
  total_sales: number;
  total_transactions: number;
  flag_count: number;
}

interface SummaryResponse {
  startDate: string;
  endDate: string;
  rows: StoreSummaryRow[];
}

export default function WHStoreSummary() {
  const [data, setData] = useState<StoreSummaryRow[]>([]);
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
      const res = await api<SummaryResponse>(
        `/api/warehouse/store-summary?start_date=${startDate}&end_date=${endDate}`
      );
      setData(res.rows || []);
    } catch (e) {
      console.error('Failed to load store summary:', e);
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [startDate, endDate]);

  // Aggregate stats for the KPI cards
  const totalSales = data.reduce((s, r) => s + r.total_sales, 0);
  const totalTransactions = data.reduce((s, r) => s + r.total_transactions, 0);
  const avgPScore = data.length > 0
    ? data.reduce((s, r) => s + r.avg_p_score, 0) / data.length
    : 0;
  const totalFlags = data.reduce((s, r) => s + r.flag_count, 0);

  return (
    <div className="wh-page">
      <div className="wh-page-header">
        <div>
          <h1 className="wh-page-title">Store Summary</h1>
          <p className="wh-page-subtitle">Cross-store daily aggregates from the Data Warehouse</p>
        </div>
        <button className="wh-btn wh-btn-secondary" onClick={fetchData} disabled={loading}>
          <RefreshCw size={16} className={loading ? 'wh-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Date filters */}
      <div className="wh-filters">
        <div className="wh-filter-group">
          <label>Start Date</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="wh-input"
          />
        </div>
        <div className="wh-filter-group">
          <label>End Date</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="wh-input"
          />
        </div>
      </div>

      {/* KPI Cards */}
      <div className="stats-grid" style={{ marginBottom: 24 }}>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(6, 182, 212, 0.15)', color: '#06B6D4' }}>
            <Database size={20} />
          </div>
          <div className="stat-value">{avgPScore.toFixed(1)}</div>
          <div className="stat-label">Avg P-Score</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(34, 197, 94, 0.15)', color: '#22C55E' }}>
            <TrendingUp size={20} />
          </div>
          <div className="stat-value">₹{(totalSales / 1000).toFixed(1)}K</div>
          <div className="stat-label">Total Sales</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#A855F7' }}>
            <ShoppingBag size={20} />
          </div>
          <div className="stat-value">{totalTransactions}</div>
          <div className="stat-label">Transactions</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#EF4444' }}>
            <Flag size={20} />
          </div>
          <div className="stat-value">{totalFlags}</div>
          <div className="stat-label">Flagged Sales</div>
        </div>
      </div>

      {/* Data Table */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Store Performance Data</span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            {data.length} records
          </span>
        </div>

        {loading ? (
          <div className="wh-loading">Loading data...</div>
        ) : data.length === 0 ? (
          <div className="wh-empty">
            <Database size={40} />
            <p>No warehouse data available for this date range.</p>
            <p style={{ fontSize: '0.8rem' }}>Run the ETL pipeline to populate warehouse tables.</p>
          </div>
        ) : (
          <div className="wh-table-wrap">
            <table className="wh-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Store</th>
                  <th>Avg P-Score</th>
                  <th>Total Sales (₹)</th>
                  <th>Transactions</th>
                  <th>Flags</th>
                </tr>
              </thead>
              <tbody>
                {data.map((row, i) => (
                  <tr key={`${row.store_id}-${row.date}-${i}`}>
                    <td className="wh-cell-date">{row.date}</td>
                    <td>
                      <span className="wh-store-badge">{row.store_name || row.store_id}</span>
                    </td>
                    <td>
                      <span className={`wh-score ${row.avg_p_score >= 70 ? 'high' : row.avg_p_score >= 40 ? 'mid' : 'low'}`}>
                        {row.avg_p_score.toFixed(1)}
                      </span>
                    </td>
                    <td>₹{row.total_sales.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</td>
                    <td>{row.total_transactions}</td>
                    <td>
                      {row.flag_count > 0 ? (
                        <span className="wh-flag-badge">{row.flag_count}</span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>—</span>
                      )}
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
