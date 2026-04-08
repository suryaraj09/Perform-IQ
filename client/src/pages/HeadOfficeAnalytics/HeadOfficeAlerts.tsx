import { useState, useCallback, useEffect } from 'react';
import { api } from '../../utils/api';
import { AlertCircle, Store, CheckCircle, XCircle, ShieldCheck, Flag, Zap } from 'lucide-react';

interface GeofenceAlert {
    id: number;
    employee_id: number;
    employee_name: string;
    store_name: string;
    punch_in_time: string;
    first_fail_time: string;
    second_fail_time: string;
    created_at: string;
}

interface FlaggedSale {
    id: number;
    employee_id: number;
    employee_name: string;
    store_name: string;
    revenue: number;
    num_items: number;
    is_flagged: boolean;
    submitted_at: string;
}

interface AlertsData {
    geofence_alerts: GeofenceAlert[];
    flagged_sales: FlaggedSale[];
    total_unresolved: number;
}

export default function HeadOfficeAlerts() {
    const [data, setData] = useState<AlertsData | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchAlerts = useCallback(async () => {
        try {
            const res = await api<AlertsData>('/api/headoffice/alerts');
            setData(res);
        } catch (err) {
            console.error('Failed to fetch alerts', err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchAlerts();
    }, [fetchAlerts]);

    const getTimeSince = (timestamp: string) => {
        const diff = Date.now() - new Date(timestamp).getTime();
        const mins = Math.floor(diff / 60000);
        if (mins < 60) return `${mins}m ago`;
        const hrs = Math.floor(mins / 60);
        if (hrs < 24) return `${hrs}h ago`;
        return `${Math.floor(hrs / 24)}d ago`;
    };

    if (loading) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Monitoring network alerts...</div>;

    return (
        <div className="animate-in">
            <div style={{ marginBottom: 24 }}>
                <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 10 }}>
                    <AlertCircle size={24} color="var(--accent)" /> Network Health Center
                </h2>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: '4px 0 0' }}>
                    Critical alerts and suspicious activities from all store locations
                </p>
            </div>

            <div className="stats-grid" style={{ marginBottom: 24 }}>
                <div className="stat-card">
                    <div className="stat-value" style={{ color: 'var(--danger)' }}>{data?.geofence_alerts.length || 0}</div>
                    <div className="stat-label">Geofence Violations</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value" style={{ color: 'var(--warning)' }}>{data?.flagged_sales.length || 0}</div>
                    <div className="stat-label">Flagged Sales</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value" style={{ color: 'var(--accent)' }}>3</div>
                    <div className="stat-label">Active Stores</div>
                </div>
            </div>

            {/* Section 1: Geofence Alerts */}
            <div style={{ marginBottom: 40 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                    <Zap size={18} color="var(--danger)" />
                    <h3 style={{ margin: 0, fontSize: '1.1rem' }}>Geofence Alerts</h3>
                    <span style={{ fontSize: '0.75rem', background: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', padding: '2px 8px', borderRadius: 8, fontWeight: 700 }}>
                        Needs Store Attention
                    </span>
                </div>
                
                <div className="alerts-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16 }}>
                    {data?.geofence_alerts.map(alert => (
                        <div className="card" key={alert.id} style={{ borderLeft: '4px solid var(--danger)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                                <span style={{ background: 'var(--bg-input)', padding: '4px 10px', borderRadius: 8, fontSize: '0.75rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 4 }}>
                                    <Store size={12} /> {alert.store_name}
                                </span>
                                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{getTimeSince(alert.created_at)}</span>
                            </div>
                            <div style={{ fontWeight: 700, fontSize: '0.95rem', marginBottom: 2 }}>{alert.employee_name}</div>
                            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: 12 }}>Unresolved Geofence Exit</div>
                            
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: '0.75rem', color: 'var(--text-muted)', background: 'var(--bg-input)', padding: 10, borderRadius: 8 }}>
                                <div>
                                    <div style={{ opacity: 0.6 }}>Punch In</div>
                                    <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{new Date(alert.punch_in_time).toLocaleTimeString()}</div>
                                </div>
                                <div>
                                    <div style={{ opacity: 0.6 }}>Last Exit</div>
                                    <div style={{ color: 'var(--danger)', fontWeight: 600 }}>{alert.second_fail_time ? new Date(alert.second_fail_time).toLocaleTimeString() : 'N/A'}</div>
                                </div>
                            </div>
                        </div>
                    ))}
                    {data?.geofence_alerts.length === 0 && (
                        <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', background: 'var(--bg-card)', borderRadius: 16, border: '1px solid var(--border)', gridColumn: '1 / -1' }}>
                            <ShieldCheck size={32} style={{ opacity: 0.2, marginBottom: 8 }} />
                            <p>No active geofence violations.</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Section 2: Flagged Sales */}
            <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                    <Flag size={18} color="var(--warning)" />
                    <h3 style={{ margin: 0, fontSize: '1.1rem' }}>Flagged Sales</h3>
                    <span style={{ fontSize: '0.75rem', background: 'rgba(245, 158, 11, 0.1)', color: 'var(--warning)', padding: '2px 8px', borderRadius: 8, fontWeight: 700 }}>
                        Review Required
                    </span>
                </div>

                <div className="alerts-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16 }}>
                    {data?.flagged_sales.map(sale => (
                        <div className="card" key={sale.id} style={{ borderLeft: '4px solid var(--warning)' }}>
                             <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                                <span style={{ background: 'var(--bg-input)', padding: '4px 10px', borderRadius: 8, fontSize: '0.75rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 4 }}>
                                    <Store size={12} /> {sale.store_name}
                                </span>
                                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{getTimeSince(sale.submitted_at)}</span>
                            </div>
                            <div style={{ fontWeight: 700, fontSize: '0.95rem', marginBottom: 2 }}>{sale.employee_name}</div>
                            <div style={{ fontSize: '0.85rem', fontWeight: 700, marginBottom: 12, color: 'var(--text-primary)' }}>
                                \u20b9{sale.revenue.toLocaleString('en-IN')} · {sale.num_items} items
                            </div>
                            
                            <div style={{ display: 'flex', gap: 8, marginTop: 'auto' }}>
                                <button className="btn btn-sm" style={{ flex: 1, justifyContent: 'center', fontSize: '0.75rem', background: 'rgba(34, 197, 94, 0.1)', color: 'var(--success)' }}>
                                    <CheckCircle size={14} /> Confirm
                                </button>
                                <button className="btn btn-sm" style={{ flex: 1, justifyContent: 'center', fontSize: '0.75rem', background: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)' }}>
                                    <XCircle size={14} /> Reject
                                </button>
                            </div>
                        </div>
                    ))}
                    {data?.flagged_sales.length === 0 && (
                        <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)', background: 'var(--bg-card)', borderRadius: 16, border: '1px solid var(--border)', gridColumn: '1 / -1' }}>
                            <ShieldCheck size={32} style={{ opacity: 0.2, marginBottom: 8 }} />
                            <p>No suspicious sales detected.</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
