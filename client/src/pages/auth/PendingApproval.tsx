import { useAuth } from '../../context/AuthContext';
import { LogOut, Clock } from 'lucide-react';

export default function PendingApproval() {
    const { profile, handleSignOut } = useAuth();
    
    return (
        <div className="auth-page">
            <div className="auth-bg-pattern" />
            <div className="auth-card animate-in" style={{ textAlign: 'center', maxWidth: 450, padding: 40 }}>
                <div style={{
                    width: 64, height: 64, borderRadius: '50%',
                    background: 'rgba(245, 158, 11, 0.15)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    margin: '0 auto 24px', color: '#F59E0B'
                }}>
                    <Clock size={32} />
                </div>
                
                <h2 style={{ fontSize: '1.5rem', marginBottom: 12 }}>Account Pending Approval</h2>
                
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 24 }}>
                    Hi {profile?.name}, your account registration has been received. 
                    A manager must review and approve your account before you can access the PerformIQ dashboard.
                </p>
                
                <div style={{ background: 'var(--bg-input)', padding: 16, borderRadius: 12, marginBottom: 32, fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                    Please check back later or contact your store manager.
                </div>
                
                <button 
                    onClick={handleSignOut}
                    className="auth-submit"
                    style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
                >
                    <LogOut size={18} />
                    Sign Out
                </button>
            </div>
        </div>
    );
}
