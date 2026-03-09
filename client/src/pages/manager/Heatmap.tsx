import { useApi } from '../../hooks/useApi';

interface CorrelationData {
    matrix: number[][];
    labels: string[];
}

export default function Heatmap() {
    const { data, loading } = useApi<CorrelationData>('/api/correlations');

    if (loading) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Computing correlations...</div>;
    if (!data || !data.matrix.length) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Not enough data for correlations.</div>;

    const getColor = (value: number) => {
        if (value >= 0.7) return '#F97316';
        if (value >= 0.4) return '#FB923C';
        if (value >= 0.1) return '#FDBA74';
        if (value >= -0.1) return 'var(--bg-input)';
        if (value >= -0.4) return '#93C5FD';
        if (value >= -0.7) return '#3B82F6';
        return '#1D4ED8';
    };

    const getTextColor = (value: number) => {
        return Math.abs(value) > 0.5 ? 'white' : 'var(--text-primary)';
    };

    return (
        <div className="animate-in">
            <p style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>
                Pearson correlation between performance metrics across all employees
            </p>

            <div className="card">
                <div className="card-header">
                    <span className="card-title">Correlation Heatmap</span>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                            <span style={{ width: 12, height: 12, background: '#1D4ED8', borderRadius: 2 }} /> -1
                        </span>
                        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                            <span style={{ width: 12, height: 12, background: 'var(--bg-input)', borderRadius: 2 }} /> 0
                        </span>
                        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                            <span style={{ width: 12, height: 12, background: '#F97316', borderRadius: 2 }} /> +1
                        </span>
                    </div>
                </div>

                <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: 3 }}>
                        <thead>
                            <tr>
                                <th style={{ width: 120 }} />
                                {data.labels.map((label, i) => (
                                    <th key={i} style={{
                                        fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)',
                                        padding: 8, textAlign: 'center', minWidth: 80,
                                        transform: 'rotate(-30deg)', transformOrigin: 'bottom left', height: 80,
                                    }}>
                                        {label}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {data.matrix.map((row, i) => (
                                <tr key={i}>
                                    <td style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', padding: '8px 12px', whiteSpace: 'nowrap' }}>
                                        {data.labels[i]}
                                    </td>
                                    {row.map((value, j) => (
                                        <td
                                            key={j}
                                            className="heatmap-cell"
                                            style={{
                                                background: getColor(value),
                                                color: getTextColor(value),
                                                padding: 12,
                                                textAlign: 'center',
                                                borderRadius: 6,
                                                fontWeight: 600,
                                                fontSize: '0.8rem',
                                                cursor: 'default',
                                            }}
                                            title={`${data.labels[i]} ↔ ${data.labels[j]}: ${value.toFixed(3)}`}
                                        >
                                            {value.toFixed(2)}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                <div style={{ marginTop: 24, padding: 16, background: 'var(--glass)', borderRadius: 12 }}>
                    <p style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: 8 }}>Key Insights:</p>
                    <ul style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', paddingLeft: 20 }}>
                        <li>Values close to <strong>+1</strong> indicate strong positive correlation (metrics move together)</li>
                        <li>Values close to <strong>-1</strong> indicate strong negative correlation (inverse relationship)</li>
                        <li>Values near <strong>0</strong> indicate no significant relationship</li>
                    </ul>
                </div>
            </div>
        </div>
    );
}
