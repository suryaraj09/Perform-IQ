import { useState, useEffect } from 'react';
import { api } from '../../utils/api';
import { Activity, RefreshCw, Play, CheckCircle, XCircle, Clock } from 'lucide-react';

interface EtlRun {
  id: number;
  run_at: string;
  stores_processed: number;
  rows_inserted: number;
  status: string;
}

interface EtlResponse {
  runs: EtlRun[];
}

export default function WHEtlRuns() {
  const [runs, setRuns] = useState<EtlRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await api<EtlResponse>('/api/warehouse/etl-runs?limit=50');
      setRuns(res.runs || []);
    } catch (e) {
      console.error('Failed to load ETL runs:', e);
      setRuns([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const triggerEtl = async () => {
    setTriggering(true);
    try {
      await api('/api/warehouse/run-etl', { method: 'POST', body: JSON.stringify({}) });
      // Refresh the list after triggering
      await fetchData();
    } catch (e) {
      console.error('ETL trigger failed:', e);
    } finally {
      setTriggering(false);
    }
  };

  // Stats
  const successCount = runs.filter((r) => r.status === 'success').length;
  const errorCount = runs.filter((r) => r.status === 'error').length;
  const totalRowsInserted = runs.reduce((s, r) => s + r.rows_inserted, 0);
  const lastRun = runs.length > 0 ? runs[0] : null;

  return (
    <div className="wh-page">
      <div className="wh-page-header">
        <div>
          <h1 className="wh-page-title">ETL Pipeline Runs</h1>
          <p className="wh-page-subtitle">Execution log and manual trigger for the Data Warehouse ETL</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="wh-btn wh-btn-primary" onClick={triggerEtl} disabled={triggering}>
            <Play size={16} />
            {triggering ? 'Running...' : 'Run ETL Now'}
          </button>
          <button className="wh-btn wh-btn-secondary" onClick={fetchData} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'wh-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="stats-grid" style={{ marginBottom: 24 }}>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(34, 197, 94, 0.15)', color: '#22C55E' }}>
            <CheckCircle size={20} />
          </div>
          <div className="stat-value">{successCount}</div>
          <div className="stat-label">Successful Runs</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#EF4444' }}>
            <XCircle size={20} />
          </div>
          <div className="stat-value">{errorCount}</div>
          <div className="stat-label">Failed Runs</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#A855F7' }}>
            <Activity size={20} />
          </div>
          <div className="stat-value">{totalRowsInserted.toLocaleString()}</div>
          <div className="stat-label">Total Rows Inserted</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(6, 182, 212, 0.15)', color: '#06B6D4' }}>
            <Clock size={20} />
          </div>
          <div className="stat-value" style={{ fontSize: '1rem' }}>
            {lastRun ? new Date(lastRun.run_at).toLocaleDateString() : '—'}
          </div>
          <div className="stat-label">Last Run</div>
        </div>
      </div>

      {/* Runs Table */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Execution History</span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{runs.length} runs</span>
        </div>

        {loading ? (
          <div className="wh-loading">Loading ETL runs...</div>
        ) : runs.length === 0 ? (
          <div className="wh-empty">
            <Activity size={40} />
            <p>No ETL runs recorded yet.</p>
            <p style={{ fontSize: '0.8rem' }}>Click "Run ETL Now" to trigger the first execution.</p>
          </div>
        ) : (
          <div className="wh-table-wrap">
            <table className="wh-table">
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>Timestamp</th>
                  <th>Stores Processed</th>
                  <th>Rows Inserted</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.id}>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.8rem', color: 'var(--text-muted)' }}>#{run.id}</td>
                    <td className="wh-cell-date">
                      {new Date(run.run_at).toLocaleString('en-IN', {
                        dateStyle: 'medium',
                        timeStyle: 'short',
                      })}
                    </td>
                    <td>{run.stores_processed}</td>
                    <td style={{ fontWeight: 600 }}>{run.rows_inserted.toLocaleString()}</td>
                    <td>
                      <span className={`wh-status-badge ${run.status}`}>
                        {run.status === 'success' ? <CheckCircle size={12} /> : <XCircle size={12} />}
                        {run.status}
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
