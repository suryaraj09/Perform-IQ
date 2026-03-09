import { useApi } from '../../hooks/useApi';

interface Sale {
    id: number;
    revenue: number;
    basket_size: number;
    num_items: number;
    status: string;
    submitted_at: string;
    sale_date: string;
    receipt_photo_path: string;
}

export default function MySales({ employeeId }: { employeeId: number }) {
    const { data: sales, loading } = useApi<Sale[]>(`/api/sales?employee_id=${employeeId}`);

    if (loading) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Loading sales...</div>;

    return (
        <div className="animate-in">
            <div className="card">
                <div className="card-header">
                    <span className="card-title">My Sales History</span>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{sales?.length || 0} records</span>
                </div>

                <table className="leaderboard-table">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Revenue</th>
                            <th>Basket Size</th>
                            <th>Items</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sales?.map(sale => (
                            <tr key={sale.id}>
                                <td>{new Date(sale.sale_date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })}</td>
                                <td style={{ fontWeight: 600 }}>₹{sale.revenue.toLocaleString()}</td>
                                <td>₹{sale.basket_size.toLocaleString()}</td>
                                <td>{sale.num_items}</td>
                                <td>
                                    <span className={`status status-${sale.status}`}>
                                        {sale.status.charAt(0).toUpperCase() + sale.status.slice(1)}
                                    </span>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>

                {(!sales || sales.length === 0) && (
                    <p style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)' }}>No sales recorded yet.</p>
                )}
            </div>
        </div>
    );
}
