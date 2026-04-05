import { useState } from 'react';
import { useApi } from '../../hooks/useApi';
import { api } from '../../utils/api';
import { Check, X, Image } from 'lucide-react';

interface ReviewQueueData {
    sales: Array<{
        id: number;
        employee_name: string;
        revenue: number;
        basket_size: number;
        num_items: number;
        receipt_photo_path: string;
        submitted_at: string;
    }>;
    total: number;
}

export default function ReviewQueue() {
    const { data, loading, refetch } = useApi<ReviewQueueData>('/api/manager/review-queue');
    const [reviewingId, setReviewingId] = useState<number | null>(null);

    const handleReview = async (id: number, status: 'approved' | 'rejected') => {
        setReviewingId(id);
        try {
            await api(`/api/sales/${id}/review`, {
                method: 'PUT',
                body: JSON.stringify({ status, reviewer_id: 14, rejection_reason: status === 'rejected' ? 'Needs correction' : null }),
            });
            refetch();
        } catch (err) {
            alert('Review failed');
        } finally {
            setReviewingId(null);
        }
    };

    if (loading) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Loading review queue...</div>;

    return (
        <div className="animate-in">
            <p style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>
                <strong>{data?.total || 0}</strong> submissions pending review
            </p>

            {/* Sales Reviews */}
            <div className="card">
                <div className="card-header">
                    <span className="card-title">Sale Submissions ({data?.sales.length || 0})</span>
                </div>

                {data?.sales.map(sale => (
                    <div className="review-item" key={sale.id}>
                        <div className="review-thumbnail" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            {sale.receipt_photo_path ? (
                                <img src={`http://localhost:8000/${sale.receipt_photo_path}`} alt="Receipt" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 10 }} />
                            ) : (
                                <Image size={24} color="var(--text-muted)" />
                            )}
                        </div>

                        <div className="review-info">
                            <div style={{ fontWeight: 600 }}>{sale.employee_name}</div>
                            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                Revenue: <strong>₹{sale.revenue.toLocaleString()}</strong> · Basket: ₹{sale.basket_size.toLocaleString()} · Items: {sale.num_items}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
                                {new Date(sale.submitted_at).toLocaleString('en-IN')}
                            </div>
                        </div>

                        <div className="review-actions">
                            <button className="btn btn-success btn-sm" onClick={() => handleReview(sale.id, 'approved')} disabled={reviewingId === sale.id}>
                                <Check size={16} /> Approve
                            </button>
                            <button className="btn btn-danger btn-sm" onClick={() => handleReview(sale.id, 'rejected')} disabled={reviewingId === sale.id}>
                                <X size={16} /> Reject
                            </button>
                        </div>
                    </div>
                ))}

                {(!data?.sales.length) && (
                    <p style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>No pending sale submissions.</p>
                )}
            </div>
        </div>
    );
}
