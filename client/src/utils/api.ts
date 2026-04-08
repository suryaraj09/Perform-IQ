import { auth } from './firebase';

const API_BASE = 'http://localhost:8000';

let globalStoreId: string | null = null;
export const setGlobalStoreId = (id: string | null) => {
  globalStoreId = id;
};

export async function api<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const token = await auth.currentUser?.getIdToken() || 'demo-token';
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string> || {}),
    'Authorization': `Bearer ${token}`,
  };

  let url = `${API_BASE}${endpoint}`;
  if (globalStoreId && (!options?.method || options.method.toUpperCase() === 'GET')) {
    const separator = url.includes('?') ? '&' : '?';
    if (!url.includes('store_id=')) {
        url += `${separator}store_id=${globalStoreId}`;
    }
  }

  const res = await fetch(url, {
    ...options,
    headers,
  });
  
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

export async function uploadFile(file: File, category: string = 'receipts'): Promise<{ path: string; filename: string }> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('category', category);

  const token = await auth.currentUser?.getIdToken() || 'demo-token';
  const headers: Record<string, string> = {
    'Authorization': `Bearer ${token}`,
  };

  const res = await fetch(`${API_BASE}/api/upload`, {
    method: 'POST',
    body: formData,
    headers,
  });
  return res.json();
}

export const API_BASE_URL = API_BASE;
