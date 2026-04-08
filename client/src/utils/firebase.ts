import { initializeApp } from 'firebase/app';
import {
    getAuth,
    createUserWithEmailAndPassword,
    signInWithEmailAndPassword,
    signOut as firebaseSignOut,
    onAuthStateChanged,
    updateProfile,
    type User,
} from 'firebase/auth';
import { api } from './api';


const firebaseConfig = {
    apiKey: "AIzaSyDpMZ0B7NUo7e1fnv5pzmc3bC1LX75pbNs",
    authDomain: "perform-iq.firebaseapp.com",
    projectId: "perform-iq",
    storageBucket: "perform-iq.firebasestorage.app",
    messagingSenderId: "327513423132",
    appId: "1:327513423132:web:2286b867104cbc363d0ed9",
    measurementId: "G-WX06QM1430"
};

const firebaseApp = initializeApp(firebaseConfig);
export const auth = getAuth(firebaseApp);

export interface EmployeeProfile {
    id: number;
    name: string;
    email: string;
    role: 'employee' | 'manager' | 'HEAD_OFFICE';
    department_id: number;
    store_id: number | string;
    department_name: string;
    store_name: string;
    total_xp: number;
    level: number;
    level_title: string;
    firebase_uid: string;
    status: 'pending' | 'approved' | 'rejected';
}

export async function signUp(
    email: string,
    password: string,
    name: string,
    role: 'employee' | 'manager'
): Promise<EmployeeProfile> {
    // 1. Create Firebase user
    const cred = await createUserWithEmailAndPassword(auth, email, password);
    await updateProfile(cred.user, { displayName: name });

    // 2. Register in our backend DB
    const profile = await api<EmployeeProfile>('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify({
            firebase_uid: cred.user.uid,
            name,
            email,
            role,
            store_id: 1,       // default store
            department_id: 1,   // default department
        }),
    });

    return profile;
}

export async function signIn(email: string, password: string): Promise<EmployeeProfile> {
    const cred = await signInWithEmailAndPassword(auth, email, password);
    const profile = await api<EmployeeProfile>(`/api/auth/profile/${cred.user.uid}`);
    return profile;
}

export async function signOutUser(): Promise<void> {
    await firebaseSignOut(auth);
}

export function onAuthChange(callback: (user: User | null) => void) {
    return onAuthStateChanged(auth, callback);
}
