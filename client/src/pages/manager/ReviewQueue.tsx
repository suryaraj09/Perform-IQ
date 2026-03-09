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
    downloads: Array<{
        id: number;
        employee_name: string;
        screenshot_photo_path: string;
        customer_name: string;
        submitted_at: string;
    }>;
    total: number;
}

export default function ReviewQueue() {
    const { data, loading, refetch } = useApi<ReviewQueueData>('/api/manager/review-queue');
    const [reviewingId, setReviewingId] = useState<number | null>(null);

    const handleReview = async (type: 'sale' | 'download', id: number, status: 'approved' | 'rejected') => {
        setReviewingId(id);
        const endpoint = type === 'sale' ? `/api/sales/${id}/review` : `/api/app-downloads/${id}/review`;
        try {
            await api(endpoint, {
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
            <div className="card" style={{ marginBottom: 24 }}>
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
                            <button className="btn btn-success btn-sm" onClick={() => handleReview('sale', sale.id, 'approved')} disabled={reviewingId === sale.id}>
                                <Check size={16} /> Approve
                            </button>
                            <button className="btn btn-danger btn-sm" onClick={() => handleReview('sale', sale.id, 'rejected')} disabled={reviewingId === sale.id}>
                                <X size={16} /> Reject
                            </button>
                        </div>
                    </div>
                ))}

                {(!data?.sales.length) && (
                    <p style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>No pending sale submissions.</p>
                )}
            </div>

            {/* Download Reviews */}
            <div className="card">
                <div className="card-header">
                    <span className="card-title">App Download Submissions ({data?.downloads.length || 0})</span>
                </div>

                {data?.downloads.map(dl => (
                    <div className="review-item" key={dl.id}>
                        <div className="review-thumbnail" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            {dl.screenshot_photo_path ? (
                                <img src={`http://localhost:8000/${dl.screenshot_photo_path}`} alt="Screenshot" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 10 }} />
                            ) : (
                                <Image size={24} color="var(--text-muted)" />
                            )}
                        </div>

                        <div className="review-info">
                            <div style={{ fontWeight: 600 }}>{dl.employee_name}</div>
                            {dl.customer_name && <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Customer: {dl.customer_name}</div>}
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
                                {new Date(dl.submitted_at).toLocaleString('en-IN')}
                            </div>
                        </div>

                        <div className="review-actions">
                            <button className="btn btn-success btn-sm" onClick={() => handleReview('download', dl.id, 'approved')} disabled={reviewingId === dl.id}>
                                <Check size={16} /> Approve
                            </button>
                            <button className="btn btn-danger btn-sm" onClick={() => handleReview('download', dl.id, 'rejected')} disabled={reviewingId === dl.id}>
                                <X size={16} /> Reject
                            </button>
                        </div>
                    </div>
                ))}

                {(!data?.downloads.length) && (
                    <p style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>No pending download submissions.</p>
                )}
            </div>
        </div>
    );
}
