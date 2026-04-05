import { useState, useEffect, useCallback } from 'react';
import { api } from '../../utils/api';
import { Flag, CheckCircle, XCircle, ShieldCheck, AlertTriangle, Clock, Eye } from 'lucide-react';

interface FlagItem {
    rule: string;
    detail: string;
}

interface FlaggedSale {
    saleId: number;
    employeeId: number;
    employeeName: string;
    department: string;
    saleAmount: number;
    numberOfItems: number;
    basketSize: number;
    receiptPhoto: string | null;
    submittedAt: string;
    flags: FlagItem[];
    isFlagged: boolean;
    resolvedByAdmin: boolean;
    currentPScore: number;
    projectedPScore: number;
}

const FLAG_LABELS: Record<string, string> = {
    HIGH_SALE_AMOUNT: 'Unusually High Sale Amount',
    HIGH_ITEM_COUNT: 'Unrealistic Item Count',
    RAPID_SUBMISSION: 'Rapid Consecutive Submission',
    NO_ACTIVE_SESSION: 'Submitted Without Punch In',
};

export default function FlaggedSales() {
    const [sales, setSales] = useState<FlaggedSale[]>([]);
    const [loading, setLoading] = useState(true);
    const [resolving, setResolving] = useState<number | null>(null);
    const [confirmDialog, setConfirmDialog] = useState<{ saleId: number; action: 'CONFIRMED' | 'REJECTED' } | null>(null);
    const [toast, setToast] = useState<{ message: string; type: 'success' | 'info' } | null>(null);
    const [fadingOut, setFadingOut] = useState<number | null>(null);

    const fetchFlagged = useCallback(async () => {
        try {
            const data = await api<FlaggedSale[]>('/api/admin/flagged-sales');
            setSales(data);
        } catch {
            // silent
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchFlagged();
        const interval = setInterval(fetchFlagged, 60000);
        return () => clearInterval(interval);
    }, [fetchFlagged]);

    const showToast = (message: string, type: 'success' | 'info' = 'success') => {
        setToast({ message, type });
        setTimeout(() => setToast(null), 3000);
    };

    const handleAction = async (saleId: number, action: 'CONFIRMED' | 'REJECTED') => {
        setResolving(saleId);
        try {
            await api(`/api/admin/flagged-sales/${saleId}`, {
                method: 'PATCH',
                body: JSON.stringify({ action }),
            });
            setFadingOut(saleId);
            setTimeout(() => {
                setSales(prev => prev.filter(s => s.saleId !== saleId));
                setFadingOut(null);
            }, 400);
            showToast(
                action === 'CONFIRMED'
                    ? 'Sale confirmed'
                    : 'Sale rejected and score updated'
            );
        } catch {
            showToast('Failed to process action', 'info');
        } finally {
            setResolving(null);
            setConfirmDialog(null);
        }
    };

    if (loading) {
        return (
            <div className="animate-in" style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
                <div style={{ width: 36, height: 36, border: '3px solid var(--border)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
            </div>
        );
    }

    return (
        <div className="animate-in">
            {/* Toast */}
            {toast && (
                <div
                    className={`alert-item ${toast.type === 'success' ? 'alert-success' : ''}`}
                    style={{
                        position: 'fixed', top: 24, right: 24, zIndex: 1000,
                        padding: '12px 20px', borderRadius: 12,
                        background: toast.type === 'success' ? 'rgba(34, 197, 94, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                        color: toast.type === 'success' ? '#22c55e' : '#f59e0b',
                        boxShadow: '0 4px 20px rgba(0,0,0,0.2)',
                        animation: 'slideIn 0.3s ease',
                    }}
                >
                    {toast.type === 'success' ? <CheckCircle size={18} /> : <AlertTriangle size={18} />}
                    {toast.message}
                </div>
            )}

            {/* Confirm Dialog */}
            {confirmDialog && (
                <div style={{
                    position: 'fixed', inset: 0, zIndex: 999, background: 'rgba(0,0,0,0.5)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                }} onClick={() => setConfirmDialog(null)}>
                    <div className="card" style={{ maxWidth: 420, padding: 24, animation: 'slideIn 0.2s ease' }} onClick={e => e.stopPropagation()}>
                        <h3 style={{ marginBottom: 12 }}>
                            {confirmDialog.action === 'CONFIRMED' ? 'Confirm this sale?' : 'Reject this sale?'}
                        </h3>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: 1.5, marginBottom: 20 }}>
                            {confirmDialog.action === 'CONFIRMED'
                                ? "It will remain in the employee's score."
                                : "It will be removed from the employee's score and weekly totals will be recalculated."}
                        </p>
                        <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
                            <button className="btn" onClick={() => setConfirmDialog(null)} style={{ fontSize: '0.85rem' }}>Cancel</button>
                            <button
                                className="btn btn-primary"
                                onClick={() => handleAction(confirmDialog.saleId, confirmDialog.action)}
                                disabled={resolving === confirmDialog.saleId}
                                style={{
                                    fontSize: '0.85rem',
                                    background: confirmDialog.action === 'REJECTED' ? '#ef4444' : '#22c55e',
                                }}
                            >
                                {resolving === confirmDialog.saleId ? 'Processing...' : confirmDialog.action === 'CONFIRMED' ? 'Yes, Confirm' : 'Yes, Reject'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
                <div>
                    <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Flag size={22} color="var(--accent)" /> Flagged Sales
                    </h2>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: '4px 0 0' }}>
                        Review and confirm or reject suspicious sale submissions
                    </p>
                </div>
                {sales.length > 0 && (
                    <span style={{
                        marginLeft: 'auto', background: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b',
                        padding: '6px 16px', borderRadius: 20, fontWeight: 600, fontSize: '0.85rem',
                    }}>
                        {sales.length} Pending Review
                    </span>
                )}
            </div>

            {/* Empty State */}
            {sales.length === 0 && (
                <div className="card" style={{ textAlign: 'center', padding: '48px 24px' }}>
                    <ShieldCheck size={56} color="#22c55e" style={{ marginBottom: 16 }} />
                    <h3 style={{ color: '#22c55e', marginBottom: 8 }}>All caught up</h3>
                    <p style={{ color: 'var(--text-secondary)' }}>No flagged sales pending review</p>
                </div>
            )}

            {/* Flagged Sale Cards */}
            {sales.map(sale => (
                <div
                    key={sale.saleId}
                    className="card"
                    style={{
                        marginBottom: 16,
                        opacity: fadingOut === sale.saleId ? 0 : 1,
                        transform: fadingOut === sale.saleId ? 'translateX(40px)' : 'none',
                        transition: 'opacity 0.4s ease, transform 0.4s ease',
                    }}
                >
                    {/* Employee Info Header */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
                        <div style={{
                            width: 40, height: 40, borderRadius: '50%', background: 'var(--accent)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            color: '#fff', fontWeight: 700, fontSize: '0.85rem', flexShrink: 0,
                        }}>
                            {sale.employeeName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)}
                        </div>
                        <div style={{ flex: 1 }}>
                            <div style={{ fontWeight: 600 }}>{sale.employeeName}</div>
                            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{sale.department}</div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 4 }}>
                                <Clock size={12} />
                                {new Date(sale.submittedAt).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}
                            </div>
                        </div>
                    </div>

                    {/* Sale Details */}
                    <div style={{ padding: '14px 20px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, borderBottom: '1px solid var(--border)' }}>
                        <div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Sale Amount</div>
                            <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>₹{sale.saleAmount.toLocaleString('en-IN')}</div>
                        </div>
                        <div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Items</div>
                            <div style={{ fontWeight: 600 }}>{sale.numberOfItems}</div>
                        </div>
                        <div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Basket Size</div>
                            <div style={{ fontWeight: 600 }}>₹{sale.basketSize.toLocaleString('en-IN')}</div>
                        </div>
                        <div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Receipt</div>
                            {sale.receiptPhoto ? (
                                <a href={sale.receiptPhoto} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.9rem' }}>
                                    <Eye size={14} /> View Photo
                                </a>
                            ) : (
                                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No receipt</span>
                            )}
                        </div>
                    </div>

                    {/* Flags */}
                    <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)' }}>
                        <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#f59e0b', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
                            🚩 FLAGS TRIGGERED
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                            {sale.flags.map((flag, i) => (
                                <div key={i} style={{
                                    background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.25)',
                                    borderRadius: 10, padding: '8px 14px', maxWidth: 320,
                                }}>
                                    <div style={{ fontWeight: 600, fontSize: '0.8rem', color: '#f59e0b' }}>
                                        {FLAG_LABELS[flag.rule] || flag.rule}
                                    </div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 2 }}>
                                        {flag.detail}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Score Impact Delta */}
                    {(() => {
                        const delta = Math.round((sale.currentPScore - sale.projectedPScore) * 10) / 10;
                        const deltaColor = delta > 5 ? '#ef4444' : delta >= 2 ? '#f59e0b' : 'var(--text-muted)';
                        return (
                            <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 24 }}>
                                <div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Current Score</div>
                                    <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>{sale.currentPScore}</div>
                                </div>
                                <div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>If Rejected</div>
                                    <div style={{ fontWeight: 700, fontSize: '1.1rem', color: deltaColor }}>{sale.projectedPScore}</div>
                                </div>
                                <div style={{
                                    marginLeft: 'auto',
                                    padding: '4px 12px',
                                    borderRadius: 8,
                                    background: delta > 5 ? 'rgba(239, 68, 68, 0.1)' : delta >= 2 ? 'rgba(245, 158, 11, 0.1)' : 'rgba(128, 128, 128, 0.1)',
                                    color: deltaColor,
                                    fontWeight: 700,
                                    fontSize: '0.85rem',
                                }}>
                                    ▼ {delta.toFixed(1)} points
                                </div>
                            </div>
                        );
                    })()}

                    {/* Actions */}
                    <div style={{ padding: '14px 20px', display: 'flex', gap: 12 }}>
                        <button
                            className="btn"
                            onClick={() => setConfirmDialog({ saleId: sale.saleId, action: 'CONFIRMED' })}
                            style={{
                                flex: 1, justifyContent: 'center', background: 'rgba(34, 197, 94, 0.1)',
                                color: '#22c55e', border: '1px solid rgba(34, 197, 94, 0.3)', fontWeight: 600,
                            }}
                        >
                            <CheckCircle size={16} /> Confirm Sale
                        </button>
                        <button
                            className="btn"
                            onClick={() => setConfirmDialog({ saleId: sale.saleId, action: 'REJECTED' })}
                            style={{
                                flex: 1, justifyContent: 'center', background: 'rgba(239, 68, 68, 0.1)',
                                color: '#ef4444', border: '1px solid rgba(239, 68, 68, 0.3)', fontWeight: 600,
                            }}
                        >
                            <XCircle size={16} /> Reject Sale
                        </button>
                    </div>
                </div>
            ))}
        </div>
    );
}
