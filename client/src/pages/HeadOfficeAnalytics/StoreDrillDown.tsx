// PerformIQ Store Drill Down
import { useParams, useNavigate } from 'react-router-dom';
import ManagerDashboard from '../manager/Dashboard';
import { ArrowLeft, ShieldCheck } from 'lucide-react';

export default function StoreDrillDown() {
    const { storeId } = useParams<{ storeId: string }>();
    const navigate = useNavigate();

    return (
        <div className="animate-in">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
                <button 
                    onClick={() => navigate('/headoffice/departments')} 
                    className="btn btn-sm"
                    style={{ gap: 8 }}
                >
                    <ArrowLeft size={16} /> Back to Overview
                </button>

                <div style={{ 
                    display: 'flex', alignItems: 'center', gap: 8, 
                    background: 'rgba(59, 130, 246, 0.1)', 
                    color: '#3b82f6', 
                    padding: '6px 16px', 
                    borderRadius: 20,
                    fontSize: '0.85rem',
                    fontWeight: 700,
                    border: '1px solid rgba(59, 130, 246, 0.2)'
                }}>
                    <ShieldCheck size={16} /> Head Office View — {storeId}
                </div>
            </div>

            <ManagerDashboard storeId={storeId} />
        </div>
    );
}
