import { useState, useEffect, useCallback, useRef } from 'react';
import { API_BASE_URL } from '../utils/api';

interface SSEAlert {
    type: string;
    message: string;
    timestamp: string;
    [key: string]: unknown;
}

export function useSSE() {
    const [alerts, setAlerts] = useState<SSEAlert[]>([]);
    const [connected, setConnected] = useState(false);
    const eventSourceRef = useRef<EventSource | null>(null);

    const connect = useCallback(() => {
        const es = new EventSource(`${API_BASE_URL}/api/stream/alerts`);
        eventSourceRef.current = es;

        es.onopen = () => setConnected(true);

        es.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data && data.type) {
                    setAlerts(prev => [data, ...prev].slice(0, 50));
                }
            } catch { /* keepalive ping */ }
        };

        es.onerror = () => {
            setConnected(false);
            es.close();
            // Reconnect after 5s
            setTimeout(connect, 5000);
        };
    }, []);

    useEffect(() => {
        connect();
        return () => eventSourceRef.current?.close();
    }, [connect]);

    const clearAlerts = useCallback(() => setAlerts([]), []);

    return { alerts, connected, clearAlerts };
}
