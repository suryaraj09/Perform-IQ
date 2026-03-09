import { useState } from 'react';
import { api, uploadFile } from '../../utils/api';
import { Camera, Upload, Check } from 'lucide-react';

export default function RecordSale({ employeeId }: { employeeId: number }) {
    const [revenue, setRevenue] = useState('');
    const [basketSize, setBasketSize] = useState('');
    const [numItems, setNumItems] = useState('1');
    const [receiptFile, setReceiptFile] = useState<File | null>(null);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);
    const [success, setSuccess] = useState(false);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            setReceiptFile(file);
            setPreviewUrl(URL.createObjectURL(file));
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!revenue || !basketSize) return;

        setSubmitting(true);
        try {
            let photoPath = '';
            if (receiptFile) {
                const upload = await uploadFile(receiptFile, 'receipts');
                photoPath = upload.path;
            }

            await api('/api/sales', {
                method: 'POST',
                body: JSON.stringify({
                    employee_id: employeeId,
                    revenue: parseFloat(revenue),
                    basket_size: parseFloat(basketSize),
                    num_items: parseInt(numItems),
                    receipt_photo_path: photoPath,
                }),
            });

            setSuccess(true);
            setRevenue('');
            setBasketSize('');
            setNumItems('1');
            setReceiptFile(null);
            setPreviewUrl(null);
            setTimeout(() => setSuccess(false), 3000);
        } catch (err) {
            alert('Failed to submit sale');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="animate-in" style={{ maxWidth: 600 }}>
            {success && (
                <div className="alert-item alert-success" style={{ marginBottom: 16 }}>
                    <Check size={20} /> Sale submitted successfully! Pending manager review.
                </div>
            )}

            <div className="card">
                <div className="card-header">
                    <span className="card-title">Submit New Sale</span>
                </div>

                <form onSubmit={handleSubmit}>
                    {/* Receipt Photo */}
                    <div className="form-group">
                        <label className="form-label">Receipt Photo</label>
                        <label className="file-upload">
                            <input type="file" accept="image/*" capture="environment" onChange={handleFileChange} style={{ display: 'none' }} />
                            {previewUrl ? (
                                <img src={previewUrl} alt="Receipt" style={{ maxHeight: 200, borderRadius: 8 }} />
                            ) : (
                                <>
                                    <Camera size={40} color="var(--accent)" />
                                    <p style={{ marginTop: 12, color: 'var(--text-secondary)' }}>Tap to take photo or upload receipt</p>
                                </>
                            )}
                        </label>
                    </div>

                    {/* Revenue */}
                    <div className="form-group">
                        <label className="form-label">Sale Amount (₹)</label>
                        <input className="form-input" type="number" step="0.01" placeholder="Enter revenue amount" value={revenue} onChange={e => setRevenue(e.target.value)} required />
                    </div>

                    {/* Basket Size */}
                    <div className="form-group">
                        <label className="form-label">Basket Size (₹)</label>
                        <input className="form-input" type="number" step="0.01" placeholder="Average item value" value={basketSize} onChange={e => setBasketSize(e.target.value)} required />
                    </div>

                    {/* Number of Items */}
                    <div className="form-group">
                        <label className="form-label">Number of Items</label>
                        <input className="form-input" type="number" min="1" value={numItems} onChange={e => setNumItems(e.target.value)} />
                    </div>

                    <button className="btn btn-primary" type="submit" disabled={submitting} style={{ width: '100%', justifyContent: 'center', marginTop: 8 }}>
                        {submitting ? 'Submitting...' : <><Upload size={18} /> Submit Sale</>}
                    </button>
                </form>
            </div>
        </div>
    );
}
