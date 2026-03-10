import { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Navigate } from 'react-router-dom';
import { Zap, Mail, Lock, User, ArrowRight, Eye, EyeOff, Sun, Moon } from 'lucide-react';

export default function Login() {
    const { profile, loading, error, handleSignIn, handleSignUp, loginAsDemo } = useAuth();
    const [isSignUp, setIsSignUp] = useState(false);
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [role, setRole] = useState<'employee' | 'manager'>('employee');
    const [submitting, setSubmitting] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    const [localError, setLocalError] = useState('');
    const [theme, setTheme] = useState<'dark' | 'light'>(() =>
        (localStorage.getItem('theme') as 'dark' | 'light') || 'light'
    );

    useEffect(() => {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    }, [theme]);

    const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark');

    // If already authenticated, redirect to dashboard
    if (!loading && profile) {
        return <Navigate to={profile.role === 'manager' ? '/manager/dashboard' : '/employee/dashboard'} replace />;
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLocalError('');
        setSubmitting(true);
        try {
            if (isSignUp) {
                if (!name.trim()) { setLocalError('Name is required.'); setSubmitting(false); return; }
                await handleSignUp(email, password, name, role);
            } else {
                await handleSignIn(email, password);
            }
        } catch {
            // Error is set via context
        } finally {
            setSubmitting(false);
        }
    };

    const displayError = localError || error;

    return (
        <div className="auth-page">
            <div className="auth-bg-pattern" />

            {/* Theme Toggle */}
            <button
                className="theme-toggle"
                onClick={toggleTheme}
                title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
                style={{ position: 'absolute', top: 24, right: 24, zIndex: 10 }}
            >
                {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
            </button>

            <div className="auth-card animate-in">
                {/* Logo */}
                <div className="auth-logo">
                    <div className="auth-logo-icon">
                        <Zap size={28} />
                    </div>
                    <h1>PerformIQ</h1>
                    <p>Gamified Retail Workforce Analytics</p>
                </div>

                {/* Tab Toggle */}
                <div className="auth-tabs">
                    <button className={!isSignUp ? 'active' : ''} onClick={() => { setIsSignUp(false); setLocalError(''); }}>
                        Sign In
                    </button>
                    <button className={isSignUp ? 'active' : ''} onClick={() => { setIsSignUp(true); setLocalError(''); }}>
                        Sign Up
                    </button>
                </div>

                {/* Error */}
                {displayError && (
                    <div className="auth-error animate-in">
                        {displayError}
                    </div>
                )}

                <form onSubmit={handleSubmit}>
                    {/* Name (sign-up only) */}
                    {isSignUp && (
                        <div className="auth-field animate-in">
                            <User size={18} className="auth-field-icon" />
                            <input
                                type="text"
                                placeholder="Full Name"
                                value={name}
                                onChange={e => setName(e.target.value)}
                                required
                                autoComplete="name"
                            />
                        </div>
                    )}

                    {/* Email */}
                    <div className="auth-field">
                        <Mail size={18} className="auth-field-icon" />
                        <input
                            type="email"
                            placeholder="Email Address"
                            value={email}
                            onChange={e => setEmail(e.target.value)}
                            required
                            autoComplete="email"
                        />
                    </div>

                    {/* Password */}
                    <div className="auth-field">
                        <Lock size={18} className="auth-field-icon" />
                        <input
                            type={showPassword ? 'text' : 'password'}
                            placeholder="Password"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            required
                            minLength={6}
                            autoComplete={isSignUp ? 'new-password' : 'current-password'}
                        />
                        <button type="button" className="auth-eye" onClick={() => setShowPassword(!showPassword)}>
                            {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                        </button>
                    </div>

                    {/* Role Selector (sign-up only) */}
                    {isSignUp && (
                        <div className="auth-role-selector animate-in">
                            <span className="auth-role-label">I am a:</span>
                            <div className="auth-role-options">
                                <button
                                    type="button"
                                    className={`auth-role-btn ${role === 'employee' ? 'active' : ''}`}
                                    onClick={() => setRole('employee')}
                                >
                                    <span className="auth-role-emoji">👤</span>
                                    <span>Employee</span>
                                </button>
                                <button
                                    type="button"
                                    className={`auth-role-btn ${role === 'manager' ? 'active' : ''}`}
                                    onClick={() => setRole('manager')}
                                >
                                    <span className="auth-role-emoji">👔</span>
                                    <span>Manager</span>
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Submit */}
                    <button className="auth-submit" type="submit" disabled={submitting || loading}>
                        {submitting ? (
                            <span className="auth-spinner" />
                        ) : (
                            <>
                                {isSignUp ? 'Create Account' : 'Sign In'}
                                <ArrowRight size={18} />
                            </>
                        )}
                    </button>
                </form>

                <p className="auth-switch">
                    {isSignUp ? 'Already have an account?' : "Don't have an account?"}
                    <button onClick={() => { setIsSignUp(!isSignUp); setLocalError(''); }}>
                        {isSignUp ? 'Sign In' : 'Sign Up'}
                    </button>
                </p>

                {/* Demo Quick Access */}
                <div style={{
                    marginTop: 20, paddingTop: 20,
                    borderTop: '1px solid var(--border)',
                    textAlign: 'center',
                }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: 10 }}>
                        Quick Test Access
                    </span>
                    <div style={{ display: 'flex', gap: 10 }}>
                        <button
                            type="button"
                            onClick={() => loginAsDemo('employee')}
                            style={{
                                flex: 1, padding: '10px 16px', borderRadius: 10,
                                border: '1px solid var(--border)', background: 'var(--bg-input)',
                                color: 'var(--text-primary)', cursor: 'pointer', fontSize: '0.8rem',
                                fontWeight: 600, fontFamily: "'Inter', sans-serif",
                                transition: 'var(--transition)',
                            }}
                        >
                            👤 Test as Employee
                        </button>
                        <button
                            type="button"
                            onClick={() => loginAsDemo('manager')}
                            style={{
                                flex: 1, padding: '10px 16px', borderRadius: 10,
                                border: '1px solid var(--border)', background: 'var(--bg-input)',
                                color: 'var(--text-primary)', cursor: 'pointer', fontSize: '0.8rem',
                                fontWeight: 600, fontFamily: "'Inter', sans-serif",
                                transition: 'var(--transition)',
                            }}
                        >
                            👔 Test as Manager
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
