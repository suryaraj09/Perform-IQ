import { useState, useCallback } from 'react';
import { useApi } from '../../hooks/useApi';
import { api } from '../../utils/api';
import { MapPin, Clock, CheckCircle, XCircle } from 'lucide-react';

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
}

export default function Attendance({ employeeId }: { employeeId: number }) {
    const { data: status, refetch: refetchStatus } = useApi<AttendanceStatus>(`/api/attendance/status/${employeeId}`);
    const { data: history } = useApi<AttendanceRecord[]>(`/api/attendance?employee_id=${employeeId}`);
    const [punching, setPunching] = useState(false);
    const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);

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
            refetchStatus();
        } catch (err) {
            setResult({ success: false, message: err instanceof GeolocationPositionError ? 'Location access denied. Please enable GPS.' : 'Failed to process attendance.' });
        } finally {
            setPunching(false);
        }
    }, [employeeId, status, refetchStatus]);

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
                                <td>
                                    <span className={`status status-${record.punch_in_status}`}>
                                        {record.punch_in_status === 'approved' ? '✓ Verified' : '✗ Rejected'}
                                    </span>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
