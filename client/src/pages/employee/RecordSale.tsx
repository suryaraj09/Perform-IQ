import { useState, useRef, useCallback, useEffect } from 'react';
import { api, uploadFile } from '../../utils/api';
import { Camera, Upload, Check, ShoppingBag, X, RefreshCw, AlertTriangle } from 'lucide-react';

interface SaleResponse {
    success: boolean;
    id: number;
    status: string;
    message: string;
    weeklyRevenue: number;
    totalBills: number;
    avgBasketSize: number;
}

export default function RecordSale({ employeeId }: { employeeId: number }) {
    const [revenue, setRevenue] = useState('');
    const [numItems, setNumItems] = useState('1');
    const [receiptFile, setReceiptFile] = useState<File | null>(null);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);
    const [success, setSuccess] = useState<'clean' | 'flagged' | null>(null);
    const [billsToday, setBillsToday] = useState(0);

    // Camera state
    const [cameraOpen, setCameraOpen] = useState(false);
    const [cameraError, setCameraError] = useState<string | null>(null);
    const videoRef = useRef<HTMLVideoElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const streamRef = useRef<MediaStream | null>(null);

    const stopCamera = useCallback(() => {
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
        }
        setCameraOpen(false);
    }, []);

    const startCamera = useCallback(async () => {
        setCameraError(null);
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
            });
            streamRef.current = stream;
            if (videoRef.current) {
                videoRef.current.srcObject = stream;
            }
            setCameraOpen(true);
        } catch (err) {
            setCameraError('Camera access denied. Please allow camera permission or use file upload.');
            setCameraOpen(false);
        }
    }, []);

    const capturePhoto = useCallback(() => {
        const video = videoRef.current;
        const canvas = canvasRef.current;
        if (!video || !canvas) return;

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        ctx.drawImage(video, 0, 0);
        canvas.toBlob(blob => {
            if (blob) {
                const file = new File([blob], `receipt_${Date.now()}.jpg`, { type: 'image/jpeg' });
                setReceiptFile(file);
                setPreviewUrl(URL.createObjectURL(blob));
                stopCamera();
            }
        }, 'image/jpeg', 0.85);
    }, [stopCamera]);

    // Fallback file input for when camera is unavailable
    const fileInputRef = useRef<HTMLInputElement>(null);
    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            setReceiptFile(file);
            setPreviewUrl(URL.createObjectURL(file));
        }
    };

    const clearPhoto = () => {
        setReceiptFile(null);
        setPreviewUrl(null);
    };

    // Cleanup camera on unmount
    useEffect(() => {
        return () => {
            if (streamRef.current) {
                streamRef.current.getTracks().forEach(track => track.stop());
            }
        };
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!revenue) return;

        setSubmitting(true);
        try {
            let photoPath = '';
            if (receiptFile) {
                const upload = await uploadFile(receiptFile, 'receipts');
                photoPath = upload.path;
            }

            const res = await api<SaleResponse>('/api/sales', {
                method: 'POST',
                body: JSON.stringify({
                    employee_id: employeeId,
                    revenue: parseFloat(revenue),
                    num_items: parseInt(numItems),
                    receipt_photo_path: photoPath,
                }),
            });

            // Cast to any to access the new isFlagged property even if SaleResponse interface isn't fully updated everywhere yet
            const isFlagged = (res as any).isFlagged;
            setSuccess(isFlagged ? 'flagged' : 'clean');
            
            setBillsToday(prev => prev + 1);
            setRevenue('');
            setNumItems('1');
            setReceiptFile(null);
            setPreviewUrl(null);
            setTimeout(() => setSuccess(null), 3000);
        } catch (err) {
            alert('Failed to submit sale');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="animate-in" style={{ maxWidth: 600 }}>
            {success && (
                <div 
                    className={`alert-item ${success === 'clean' ? 'alert-success' : ''}`} 
                    style={{ 
                        marginBottom: 16,
                        ...(success === 'flagged' ? {
                            background: 'rgba(245, 158, 11, 0.15)',
                            color: '#f59e0b',
                            border: '1px solid rgba(245, 158, 11, 0.3)'
                        } : {})
                    }}
                >
                    {success === 'clean' ? <Check size={20} /> : <AlertTriangle size={20} />}
                    {success === 'clean' ? `Sale recorded! ₹${revenue || '0'} · ${numItems} items` : `Sale recorded and under review`}
                </div>
            )}

            {billsToday > 0 && (
                <div className="card" style={{ marginBottom: 16, padding: '12px 20px', display: 'flex', alignItems: 'center', gap: 12 }}>
                    <ShoppingBag size={20} color="var(--accent)" />
                    <span style={{ fontWeight: 600 }}>Bills Today:</span>
                    <span style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--accent)' }}>{billsToday}</span>
                </div>
            )}

            <div className="card">
                <div className="card-header">
                    <span className="card-title">Submit New Sale</span>
                </div>

                <form onSubmit={handleSubmit}>
                    {/* Receipt Photo — Camera Capture */}
                    <div className="form-group">
                        <label className="form-label">Receipt Photo</label>

                        {/* Camera viewfinder */}
                        {cameraOpen && (
                            <div style={{ position: 'relative', borderRadius: 12, overflow: 'hidden', marginBottom: 12, background: '#000' }}>
                                <video
                                    ref={videoRef}
                                    autoPlay
                                    playsInline
                                    muted
                                    style={{ width: '100%', display: 'block', borderRadius: 12 }}
                                />
                                <div style={{ display: 'flex', justifyContent: 'center', gap: 16, padding: '12px 0', position: 'absolute', bottom: 0, left: 0, right: 0, background: 'linear-gradient(transparent, rgba(0,0,0,0.7))' }}>
                                    <button
                                        type="button"
                                        onClick={stopCamera}
                                        style={{
                                            width: 44, height: 44, borderRadius: '50%', border: '2px solid rgba(255,255,255,0.6)',
                                            background: 'rgba(255,255,255,0.15)', cursor: 'pointer', display: 'flex',
                                            alignItems: 'center', justifyContent: 'center',
                                        }}
                                    >
                                        <X size={20} color="#fff" />
                                    </button>
                                    <button
                                        type="button"
                                        onClick={capturePhoto}
                                        style={{
                                            width: 64, height: 64, borderRadius: '50%', border: '4px solid #fff',
                                            background: 'var(--accent)', cursor: 'pointer', display: 'flex',
                                            alignItems: 'center', justifyContent: 'center', boxShadow: '0 2px 12px rgba(0,0,0,0.3)',
                                        }}
                                    >
                                        <Camera size={28} color="#fff" />
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* Preview of captured/uploaded photo */}
                        {previewUrl && !cameraOpen && (
                            <div style={{ position: 'relative', marginBottom: 12 }}>
                                <img src={previewUrl} alt="Receipt" style={{ width: '100%', maxHeight: 240, objectFit: 'cover', borderRadius: 12 }} />
                                <div style={{ display: 'flex', gap: 8, marginTop: 8, justifyContent: 'center' }}>
                                    <button type="button" onClick={() => { clearPhoto(); startCamera(); }}
                                        className="btn" style={{ fontSize: '0.85rem', padding: '6px 14px', gap: 6 }}>
                                        <RefreshCw size={14} /> Retake
                                    </button>
                                    <button type="button" onClick={clearPhoto}
                                        className="btn" style={{ fontSize: '0.85rem', padding: '6px 14px', gap: 6 }}>
                                        <X size={14} /> Remove
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* Buttons to open camera or upload file */}
                        {!previewUrl && !cameraOpen && (
                            <div style={{ display: 'flex', gap: 12, marginTop: 4 }}>
                                <button
                                    type="button"
                                    onClick={startCamera}
                                    className="file-upload"
                                    style={{ flex: 1, cursor: 'pointer' }}
                                >
                                    <Camera size={36} color="var(--accent)" />
                                    <p style={{ marginTop: 8, color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Take Photo</p>
                                </button>
                                <button
                                    type="button"
                                    onClick={() => fileInputRef.current?.click()}
                                    className="file-upload"
                                    style={{ flex: 1, cursor: 'pointer' }}
                                >
                                    <Upload size={36} color="var(--text-secondary)" />
                                    <p style={{ marginTop: 8, color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Upload File</p>
                                </button>
                                <input ref={fileInputRef} type="file" accept="image/*" onChange={handleFileChange} style={{ display: 'none' }} />
                            </div>
                        )}

                        {cameraError && (
                            <p style={{ color: 'var(--danger)', fontSize: '0.85rem', marginTop: 8 }}>{cameraError}</p>
                        )}
                    </div>

                    {/* Hidden canvas for photo capture */}
                    <canvas ref={canvasRef} style={{ display: 'none' }} />

                    {/* Revenue */}
                    <div className="form-group">
                        <label className="form-label">Sale Amount (₹)</label>
                        <input className="form-input" type="number" step="0.01" placeholder="Enter revenue amount" value={revenue} onChange={e => setRevenue(e.target.value)} required />
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
