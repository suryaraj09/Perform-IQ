import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { type User } from 'firebase/auth';
import { onAuthChange, signIn, signUp, signOutUser, type EmployeeProfile } from '../utils/firebase';
import { api, setGlobalStoreId } from '../utils/api';

interface AuthState {
    firebaseUser: User | null;
    profile: EmployeeProfile | null;
    role: 'employee' | 'manager' | 'HEAD_OFFICE' | null;
    storeId: string | null;
    activeStoreId: string | null;
    setActiveStoreId: (id: string) => void;
    storeName: string | null;
    employeeId: string | null;
    storeLat: number | null;
    storeLng: number | null;
    geofenceRadius: number | null;
    loading: boolean;
    error: string | null;
    handleSignIn: (email: string, password: string) => Promise<void>;
    handleSignUp: (email: string, password: string, name: string, role: 'employee' | 'manager') => Promise<void>;
    handleSignOut: () => Promise<void>;
    loginAsDemo: (role: 'employee' | 'manager') => void;
}

const AuthContext = createContext<AuthState>({
    firebaseUser: null,
    profile: null,
    role: null,
    storeId: null,
    activeStoreId: null,
    setActiveStoreId: () => { },
    storeName: null,
    employeeId: null,
    storeLat: null,
    storeLng: null,
    geofenceRadius: null,
    loading: true,
    error: null,
    handleSignIn: async () => { },
    handleSignUp: async () => { },
    handleSignOut: async () => { },
    loginAsDemo: () => { },
});

export function useAuth() {
    return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: ReactNode }) {
    const [firebaseUser, setFirebaseUser] = useState<User | null>(null);
    const [profile, setProfile] = useState<EmployeeProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [activeStoreId, setActiveStoreId] = useState<string | null>(null);
    const [storeName, setStoreName] = useState<string | null>(null);
    const [storeLat, setStoreLat] = useState<number | null>(null);
    const [storeLng, setStoreLng] = useState<number | null>(null);
    const [geofenceRadius, setGeofenceRadius] = useState<number | null>(null);
    const [authClaims, setAuthClaims] = useState<{ role?: string; storeId?: string; employeeId?: string }>({});

    // Keep global store id in sync for non-hook api calls
    useEffect(() => {
        setGlobalStoreId(activeStoreId);
    }, [activeStoreId]);

    // Listen for Firebase auth state changes
    useEffect(() => {
        const unsubscribe = onAuthChange(async (user) => {
            setFirebaseUser(user);
            if (user) {
                try {
                    await user.getIdToken(true);
                    const idTokenResult = await user.getIdTokenResult();
                    const sId = idTokenResult.claims.storeId as string;
                    setAuthClaims({
                        role: idTokenResult.claims.role as string,
                        storeId: sId,
                        employeeId: idTokenResult.claims.employeeId as string,
                    });
                    
                    if (sId) setActiveStoreId(sId);
                    
                    const emp = await api<EmployeeProfile>(`/api/auth/profile/${user.uid}`);
                    setProfile(emp);
                    setError(null);
                    
                    // Fetch store config
                    const storeCfg = await api<any>(`/api/store/config${sId ? `?store_id=${sId}` : ''}`);
                    setStoreName(storeCfg.storeName);
                    setStoreLat(storeCfg.storeLat);
                    setStoreLng(storeCfg.storeLng);
                    setGeofenceRadius(storeCfg.geofenceRadius);
                    
                } catch {
                    setProfile(null);
                }
            } else {
                setProfile(null);
                setAuthClaims({});
                setActiveStoreId(null);
                setStoreName(null);
            }
            setLoading(false);
        });
        return unsubscribe;
    }, []);

    // Effect to refetch store info if activeStoreId changes (for Head Office)
    useEffect(() => {
        if (firebaseUser && activeStoreId) {
            api<any>(`/api/store/config?store_id=${activeStoreId}`).then((cfg: any) => {
                setStoreName(cfg.storeName);
                setStoreLat(cfg.storeLat);
                setStoreLng(cfg.storeLng);
                setGeofenceRadius(cfg.geofenceRadius);
            }).catch(console.error);
        }
    }, [activeStoreId, firebaseUser]);

    const handleSignIn = async (email: string, password: string) => {
        setError(null);
        setLoading(true);
        try {
            const emp = await signIn(email, password);
            setProfile(emp);
        } catch (err: any) {
            const msg = err?.message || 'Sign in failed';
            // Friendlier Firebase error messages
            if (msg.includes('user-not-found') || msg.includes('invalid-credential')) {
                setError('Invalid email or password.');
            } else if (msg.includes('wrong-password')) {
                setError('Incorrect password.');
            } else if (msg.includes('too-many-requests')) {
                setError('Too many attempts. Please try again later.');
            } else {
                setError(msg);
            }
            throw err;
        } finally {
            setLoading(false);
        }
    };

    const handleSignUp = async (email: string, password: string, name: string, role: 'employee' | 'manager') => {
        setError(null);
        setLoading(true);
        try {
            const emp = await signUp(email, password, name, role);
            setProfile(emp);
        } catch (err: any) {
            const msg = err?.message || 'Sign up failed';
            if (msg.includes('email-already-in-use')) {
                setError('An account with this email already exists.');
            } else if (msg.includes('weak-password')) {
                setError('Password must be at least 6 characters.');
            } else if (msg.includes('invalid-email')) {
                setError('Please enter a valid email address.');
            } else {
                setError(msg);
            }
            throw err;
        } finally {
            setLoading(false);
        }
    };

    const handleSignOut = async () => {
        try { await signOutUser(); } catch { /* demo mode has no firebase session */ }
        setProfile(null);
        setFirebaseUser(null);
    };

    const loginAsDemo = (demoRole: 'employee' | 'manager') => {
        setProfile({
            id: demoRole === 'employee' ? 1 : 16,
            name: demoRole === 'employee' ? 'Demo Employee' : 'Demo Manager',
            email: demoRole === 'employee' ? 'employee@demo.com' : 'manager@demo.com',
            role: demoRole,
            department_id: 1,
            store_id: 'S001',
            department_name: 'Electronics',
            store_name: 'Blue Buddha Navrangpura',
            total_xp: demoRole === 'employee' ? 4200 : 0,
            level: demoRole === 'employee' ? 5 : 1,
            level_title: demoRole === 'employee' ? 'Performer' : 'Manager',
            firebase_uid: 'demo',
            status: 'approved',
        });
        setActiveStoreId('S001');
        setLoading(false);
        setError(null);
    };

    return (
        <AuthContext.Provider value={{
            firebaseUser,
            profile,
            role: (authClaims.role as AuthState["role"]) || (profile?.role as AuthState["role"]) || null,
            storeId: authClaims.storeId || null,
            activeStoreId,
            setActiveStoreId,
            storeName,
            employeeId: authClaims.employeeId || null,
            storeLat,
            storeLng,
            geofenceRadius,
            loading,
            error,
            handleSignIn,
            handleSignUp,
            handleSignOut,
            loginAsDemo,
        }}>
            {children}
        </AuthContext.Provider>
    );
}
