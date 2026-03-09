import { useApi } from '../../hooks/useApi';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ZAxis } from 'recharts';

interface ClusterData {
    clusters: Array<{
        cluster_id: number;
        name: string;
        employees: Array<{
            id: number;
            name: string;
            total_revenue: number;
            avg_basket: number;
            app_conversion: number;
        }>;
    }>;
    centroids: Array<{
        cluster_id: number;
        name: string;
        revenue: number;
        basket_size: number;
        app_conversion: number;
    }>;
    n_employees: number;
}

const CLUSTER_COLORS = ['#F97316', '#3B82F6', '#22C55E', '#EAB308', '#8B5CF6'];

export default function Clustering() {
    const { data, loading } = useApi<ClusterData>('/api/clustering');

    if (loading) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Computing clusters...</div>;

    if (!data || !data.clusters.length) {
        return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Not enough data for clustering.</div>;
    }

    // Prepare scatter data
    const scatterData = data.clusters.map((cluster, ci) => ({
        ...cluster,
        color: CLUSTER_COLORS[ci % CLUSTER_COLORS.length],
        data: cluster.employees.map(emp => ({
            x: emp.total_revenue / 1000,
            y: emp.avg_basket,
            z: emp.app_conversion * 1000,
            name: emp.name,
            cluster: cluster.name,
        })),
    }));

    return (
        <div className="animate-in">
            <p style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>
                K-Means clustering of <strong>{data.n_employees}</strong> employees based on revenue, basket size & app conversion
            </p>

            {/* Scatter Plot */}
            <div className="card" style={{ marginBottom: 24 }}>
                <div className="card-header">
                    <span className="card-title">Employee Clusters</span>
                    <div style={{ display: 'flex', gap: 16 }}>
                        {scatterData.map(cluster => (
                            <div key={cluster.cluster_id} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.8rem' }}>
                                <span style={{ width: 10, height: 10, borderRadius: '50%', background: cluster.color, display: 'inline-block' }} />
                                {cluster.name}
                            </div>
                        ))}
                    </div>
                </div>
                <div className="chart-container" style={{ height: 400 }}>
                    <ResponsiveContainer width="100%" height="100%">
                        <ScatterChart>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                            <XAxis type="number" dataKey="x" name="Revenue" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} label={{ value: 'Revenue (₹K)', position: 'bottom', fill: 'var(--text-muted)', fontSize: 12 }} />
                            <YAxis type="number" dataKey="y" name="Basket Size" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} label={{ value: 'Avg Basket (₹)', angle: -90, position: 'insideLeft', fill: 'var(--text-muted)', fontSize: 12 }} />
                            <ZAxis type="number" dataKey="z" range={[40, 200]} />
                            <Tooltip
                                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, color: 'var(--text-primary)' }}
                                formatter={(_value: any, name: any, props: any) => {
                                    if (name === 'x') return [`₹${props.payload.name}`, 'Employee'];
                                    return [_value, name];
                                }}
                                content={({ payload }) => {
                                    if (!payload?.[0]) return null;
                                    const d = payload[0].payload;
                                    return (
                                        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, padding: 12 }}>
                                            <div style={{ fontWeight: 700 }}>{d.name}</div>
                                            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{d.cluster}</div>
                                            <div style={{ fontSize: '0.8rem', marginTop: 4 }}>Revenue: ₹{(d.x * 1000).toFixed(0)}</div>
                                            <div style={{ fontSize: '0.8rem' }}>Basket: ₹{d.y.toFixed(0)}</div>
                                        </div>
                                    );
                                }}
                            />
                            {scatterData.map(cluster => (
                                <Scatter key={cluster.cluster_id} name={cluster.name} data={cluster.data} fill={cluster.color} />
                            ))}
                        </ScatterChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Cluster Details */}
            <div className="stats-grid" style={{ gridTemplateColumns: `repeat(${data.clusters.length}, 1fr)` }}>
                {data.clusters.map((cluster, ci) => (
                    <div className="card" key={cluster.cluster_id}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                            <span style={{ width: 12, height: 12, borderRadius: '50%', background: CLUSTER_COLORS[ci % CLUSTER_COLORS.length] }} />
                            <span style={{ fontWeight: 700 }}>{cluster.name}</span>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>({cluster.employees.length})</span>
                        </div>
                        {cluster.employees.map(emp => (
                            <div key={emp.id} style={{ padding: '6px 0', borderBottom: '1px solid var(--border)', fontSize: '0.85rem' }}>
                                <span style={{ fontWeight: 600 }}>{emp.name}</span>
                                <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                                    ₹{(emp.total_revenue / 1000).toFixed(1)}K rev · ₹{emp.avg_basket.toFixed(0)} basket
                                </div>
                            </div>
                        ))}
                    </div>
                ))}
            </div>
        </div>
    );
}
