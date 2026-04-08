import { useState, useEffect } from 'react';
import { api } from '../../utils/api';
import { Users, Search, RefreshCw } from 'lucide-react';

interface EmployeeFactRow {
  employee_id: number;
  employee_name: string;
  store_id: string;
  store_name: string;
  department: string;
  date: string;
  p_score: number;
  cluster_label: string | null;
  xp: number;
}

interface FactsResponse {
  date: string;
  rows: EmployeeFactRow[];
}

const CLUSTER_COLORS: Record<string, string> = {
  'High Performer': '#22C55E',
  'Consistent Mid': '#3B82F6',
  'Needs Development': '#EAB308',
  'At Risk': '#EF4444',
};

export default function WHEmployeeFacts() {
  const [data, setData] = useState<EmployeeFactRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [storeFilter, setStoreFilter] = useState('');
  const [deptFilter, setDeptFilter] = useState('');
  const [dateFilter, setDateFilter] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 1);
    return d.toISOString().split('T')[0];
  });
  const [searchQuery, setSearchQuery] = useState('');

  const fetchData = async () => {
    setLoading(true);
    try {
      let url = `/api/warehouse/employee-facts?date=${dateFilter}`;
      if (storeFilter) url += `&store_id=${storeFilter}`;
      if (deptFilter) url += `&department=${encodeURIComponent(deptFilter)}`;
      const res = await api<FactsResponse>(url);
      setData(res.rows || []);
    } catch (e) {
      console.error('Failed to load employee facts:', e);
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [storeFilter, deptFilter, dateFilter]);

  // Extract unique stores and departments for filter dropdowns
  const stores = [...new Set(data.map((r) => r.store_id))];
  const departments = [...new Set(data.map((r) => r.department).filter(Boolean))];

  // Apply text search
  const filtered = data.filter((r) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      r.employee_name?.toLowerCase().includes(q) ||
      r.department?.toLowerCase().includes(q) ||
      r.store_name?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="wh-page">
      <div className="wh-page-header">
        <div>
          <h1 className="wh-page-title">Employee Fact Table</h1>
          <p className="wh-page-subtitle">Per-employee P-Scores and cluster labels</p>
        </div>
        <button className="wh-btn wh-btn-secondary" onClick={fetchData} disabled={loading}>
          <RefreshCw size={16} className={loading ? 'wh-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="wh-filters">
        <div className="wh-filter-group">
          <label>Date</label>
          <input
            type="date"
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
            className="wh-input"
          />
        </div>
        <div className="wh-filter-group">
          <label>Store</label>
          <select value={storeFilter} onChange={(e) => setStoreFilter(e.target.value)} className="wh-input">
            <option value="">All Stores</option>
            {stores.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div className="wh-filter-group">
          <label>Department</label>
          <select value={deptFilter} onChange={(e) => setDeptFilter(e.target.value)} className="wh-input">
            <option value="">All Departments</option>
            {departments.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </div>
        <div className="wh-filter-group wh-filter-search">
          <label>Search</label>
          <div style={{ position: 'relative' }}>
            <Search size={16} style={{ position: 'absolute', left: 10, top: 10, color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Name, department..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="wh-input"
              style={{ paddingLeft: 34 }}
            />
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Employee Performance Data</span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            {filtered.length} employees
          </span>
        </div>

        {loading ? (
          <div className="wh-loading">Loading employee facts...</div>
        ) : filtered.length === 0 ? (
          <div className="wh-empty">
            <Users size={40} />
            <p>No employee data available.</p>
          </div>
        ) : (
          <div className="wh-table-wrap">
            <table className="wh-table">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Store</th>
                  <th>Department</th>
                  <th>P-Score</th>
                  <th>Cluster</th>
                  <th>XP</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((row) => (
                  <tr key={`${row.employee_id}-${row.date}`}>
                    <td style={{ fontWeight: 600 }}>{row.employee_name}</td>
                    <td><span className="wh-store-badge">{row.store_name || row.store_id}</span></td>
                    <td>{row.department || '—'}</td>
                    <td>
                      <span className={`wh-score ${row.p_score >= 70 ? 'high' : row.p_score >= 40 ? 'mid' : 'low'}`}>
                        {row.p_score.toFixed(1)}
                      </span>
                    </td>
                    <td>
                      {row.cluster_label ? (
                        <span
                          className="wh-cluster-badge"
                          style={{ borderColor: CLUSTER_COLORS[row.cluster_label] || 'var(--border)', color: CLUSTER_COLORS[row.cluster_label] || 'var(--text-secondary)' }}
                        >
                          {row.cluster_label}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>—</span>
                      )}
                    </td>
                    <td style={{ fontWeight: 600, color: 'var(--accent)' }}>{row.xp.toLocaleString()}</td>
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
