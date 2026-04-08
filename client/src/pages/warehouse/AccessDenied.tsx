import { useNavigate } from 'react-router-dom';
import { ShieldX } from 'lucide-react';

export default function AccessDenied() {
  const navigate = useNavigate();

  return (
    <div className="auth-page">
      <div className="auth-bg-pattern" />
      <div className="auth-card" style={{ textAlign: 'center' }}>
        <div style={{
          width: 72, height: 72, borderRadius: 18,
          background: 'rgba(239, 68, 68, 0.15)',
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          marginBottom: 24,
        }}>
          <ShieldX size={36} color="var(--danger)" />
        </div>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 8 }}>Access Denied</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: 24, lineHeight: 1.5 }}>
          You don't have the required permissions to access the Data Warehouse portal.
          This area is restricted to Head Office administrators only.
        </p>
        <button
          className="auth-submit"
          onClick={() => navigate('/')}
          style={{ maxWidth: 200, margin: '0 auto' }}
        >
          Go to Dashboard
        </button>
      </div>
    </div>
  );
}
