import { useState, useCallback, useEffect, useRef } from 'react';
import { useApi } from '../../hooks/useApi';
import { api } from '../../utils/api';
import { MapPin, Clock, CheckCircle, XCircle } from 'lucide-react';
import {
    STORE_LAT,
    STORE_LNG,
    GEOFENCE_RADIUS,
    GEOFENCE_CHECK_INTERVAL,
    haversineDistance,
} from '../../utils/geofenceConfig';

interface AttendanceStatus {
    is_punched_in: boolean;
    completed_today?: boolean;
    hours_worked?: number;
    hours_so_far?: number;
    punch_in_time?: string;
    punch_out_time?: string;
}

interface AttendanceRecord {
    id: number;
    employee_name: string;
    punch_in_time: string;
    punch_out_time: string;
    punch_in_status: string;
    punch_out_status: string;
    hours_worked: number;
    attendance_date: string;
    punch_in_distance_meters: number;
    geofence_flagged?: boolean;
}

export default function Attendance({ employeeId, employeeName }: { employeeId: number; employeeName?: string }) {
    const { data: status, refetch: refetchStatus } = useApi<AttendanceStatus>(`/api/attendance/status/${employeeId}`);
    const { data: history } = useApi<AttendanceRecord[]>(`/api/attendance?employee_id=${employeeId}`);
    const [punching, setPunching] = useState(false);
    const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);

    // Geofence tracking refs (silent — no UI)
    const geofenceIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const consecutiveFailCountRef = useRef(0);
    const firstFailTimeRef = useRef<string | null>(null);

    const stopGeofenceChecks = useCallback(() => {
        if (geofenceIntervalRef.current) {
            clearInterval(geofenceIntervalRef.current);
            geofenceIntervalRef.current = null;
        }
        consecutiveFailCountRef.current = 0;
        firstFailTimeRef.current = null;
    }, []);

    const runGeofenceCheck = useCallback(async () => {
        try {
            const position = await new Promise<GeolocationPosition>((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject, {
                    enableHighAccuracy: true,
                    timeout: 10000,
                });
            });

            const distance = haversineDistance(
                position.coords.latitude,
                position.coords.longitude,
                STORE_LAT,
                STORE_LNG
            );

            if (distance <= GEOFENCE_RADIUS) {
                consecutiveFailCountRef.current = 0;
                firstFailTimeRef.current = null;
            } else {
                handleGeofenceFail();
            }
        } catch {

            handleGeofenceFail();
        }
    }, []);

    const handleGeofenceFail = useCallback(() => {
        const now = new Date().toISOString();

        if (consecutiveFailCountRef.current === 0) {
            firstFailTimeRef.current = now;
        }

        consecutiveFailCountRef.current += 1;

        if (consecutiveFailCountRef.current >= 2) {
            // Send alert to admin
            try {
                api('/api/alerts/geofence', {
                    method: 'POST',
                    body: JSON.stringify({
                        employeeId,
                        employeeName: employeeName || 'Unknown',
                        punchInTime: status?.punch_in_time || new Date().toISOString(),
                        firstFailTime: firstFailTimeRef.current,
                        secondFailTime: now,
                        alertType: 'GEOFENCE_ABSENCE',
                    }),
                });
            } catch {
                // Silent — do not show errors for background checks
            }

            // Reset cycle
            consecutiveFailCountRef.current = 0;
            firstFailTimeRef.current = null;
        }
    }, [employeeId, employeeName, status?.punch_in_time]);

    // Start/stop geofence interval based on punch-in status
    useEffect(() => {
        if (status?.is_punched_in) {
            // Run an immediate check, then every 15 minutes
            runGeofenceCheck();
            geofenceIntervalRef.current = setInterval(runGeofenceCheck, GEOFENCE_CHECK_INTERVAL);
        } else {
            stopGeofenceChecks();
        }

        return () => {
            stopGeofenceChecks();
        };
    }, [status?.is_punched_in, runGeofenceCheck, stopGeofenceChecks]);

    const handlePunch = useCallback(async () => {
        setPunching(true);
        setResult(null);

        try {
            const position = await new Promise<GeolocationPosition>((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject, { enableHighAccuracy: true, timeout: 10000 });
            });

            const endpoint = status?.is_punched_in ? '/api/attendance/punch-out' : '/api/attendance/punch-in';
            const res = await api<{ success: boolean; message: string }>(endpoint, {
                method: 'POST',
                body: JSON.stringify({
                    employee_id: employeeId,
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                }),
            });

            setResult(res);

            // If punching out, stop geofence checks
            if (status?.is_punched_in) {
                stopGeofenceChecks();
            }

            refetchStatus();
        } catch (err) {
            setResult({ success: false, message: err instanceof GeolocationPositionError ? 'Location access denied. Please enable GPS.' : 'Failed to process attendance.' });
        } finally {
            setPunching(false);
        }
    }, [employeeId, status, refetchStatus, stopGeofenceChecks]);

    const getStatusBadge = (record: AttendanceRecord) => {
        if (!record.punch_in_time && !record.punch_out_time) {
            return <span className="status" style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#ef4444' }}>✗ Absent</span>;
        }
        if (record.geofence_flagged) {
            return <span className="status" style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b' }}>⚠ Flagged</span>;
        }
        if (record.punch_in_status === 'approved') {
            return <span className="status status-approved">✓ Verified</span>;
        }
        return <span className="status" style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#ef4444' }}>✗ Rejected</span>;
    };

    return (
        <div className="animate-in">
            {/* Punch Button */}
            <div className="card" style={{ textAlign: 'center', marginBottom: 24 }}>
                <div className="card-header" style={{ justifyContent: 'center' }}>
                    <span className="card-title">
                        {status?.is_punched_in ? '🟢 Currently On Shift' : status?.completed_today ? '✅ Shift Completed' : '⏰ Mark Attendance'}
                    </span>
                </div>

                {status?.is_punched_in && (
                    <p style={{ color: 'var(--text-secondary)', marginBottom: 8 }}>
                        Hours so far: <strong>{status.hours_so_far?.toFixed(1)}h</strong> · Punched in at {status.punch_in_time?.split(' ')[1]}
                    </p>
                )}

                {status?.completed_today && (
                    <p style={{ color: 'var(--success)', marginBottom: 8 }}>
                        Worked <strong>{status.hours_worked?.toFixed(1)}h</strong> today
                    </p>
                )}

                {!status?.completed_today && (
                    <button
                        className={`punch-btn ${status?.is_punched_in ? 'punched-in' : ''}`}
                        onClick={handlePunch}
                        disabled={punching}
                    >
                        <MapPin size={32} />
                        {punching ? 'Getting location...' : status?.is_punched_in ? 'Punch Out' : 'Punch In'}
                    </button>
                )}

                {result && (
                    <div className={`alert-item ${result.success ? 'alert-success' : 'alert-danger'}`} style={{ marginTop: 16, justifyContent: 'center' }}>
                        {result.success ? <CheckCircle size={18} /> : <XCircle size={18} />}
                        {result.message}
                    </div>
                )}
            </div>

            {/* History */}
            <div className="card">
                <div className="card-header">
                    <span className="card-title"><Clock size={16} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 8 }} />Attendance History</span>
                </div>
                <table className="leaderboard-table">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Punch In</th>
                            <th>Punch Out</th>
                            <th>Hours</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {history?.map(record => (
                            <tr key={record.id}>
                                <td>{new Date(record.attendance_date).toLocaleDateString('en-IN', { weekday: 'short', month: 'short', day: 'numeric' })}</td>
                                <td>{record.punch_in_time?.split(' ')[1] || '-'}</td>
                                <td>{record.punch_out_time?.split(' ')[1] || '-'}</td>
                                <td style={{ fontWeight: 600 }}>{record.hours_worked ? `${record.hours_worked.toFixed(1)}h` : '-'}</td>
                                <td>{getStatusBadge(record)}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
