import { useApi } from '../../hooks/useApi';
import { Trophy, Medal } from 'lucide-react';

interface LeaderboardEntry {
    id: number;
    name: string;
    total_xp: number;
    level: number;
    level_title: string;
    department_name: string;
    rank: number;
}

export default function Leaderboard() {
    const { data: entries, loading } = useApi<LeaderboardEntry[]>('/api/leaderboard');

    if (loading) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Loading leaderboard...</div>;

    return (
        <div className="animate-in">
            {/* Top 3 Podium */}
            {entries && entries.length >= 3 && (
                <div style={{ display: 'flex', justifyContent: 'center', gap: 24, marginBottom: 32, alignItems: 'flex-end' }}>
                    {[entries[1], entries[0], entries[2]].map((entry, idx) => {
                        const heights = [140, 180, 120];
                        const colors = ['#C0C0C0', '#FFD700', '#CD7F32'];
                        const sizes = [60, 80, 60];
                        return (
                            <div key={entry.id} style={{ textAlign: 'center' }}>
                                <div style={{
                                    width: sizes[idx], height: sizes[idx], borderRadius: '50%', background: `linear-gradient(135deg, ${colors[idx]}, ${colors[idx]}88)`,
                                    display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 8px',
                                    fontSize: idx === 1 ? '2rem' : '1.5rem', boxShadow: `0 4px 16px ${colors[idx]}44`
                                }}>
                                    {idx === 1 ? '👑' : <Medal size={24} />}
                                </div>
                                <div style={{ fontWeight: 700, fontSize: idx === 1 ? '1rem' : '0.9rem' }}>{entry.name}</div>
                                <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>{entry.department_name}</div>
                                <div style={{
                                    width: 100, height: heights[idx], background: `linear-gradient(180deg, ${colors[idx]}, ${colors[idx]}44)`,
                                    borderRadius: '10px 10px 0 0', display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    marginTop: 12, fontWeight: 800, fontSize: '1.2rem', color: '#000'
                                }}>
                                    #{entry.rank}
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Full Table */}
            <div className="card">
                <div className="card-header">
                    <span className="card-title"><Trophy size={16} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 8 }} />Rankings</span>
                </div>
                <table className="leaderboard-table">
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Name</th>
                            <th>Department</th>
                            <th>Level</th>
                            <th>XP</th>
                        </tr>
                    </thead>
                    <tbody>
                        {entries?.map(entry => (
                            <tr key={entry.id}>
                                <td>
                                    <span className={`rank-badge ${entry.rank <= 3 ? `rank-${entry.rank}` : ''}`}
                                        style={entry.rank > 3 ? { background: 'var(--bg-input)', color: 'var(--text-secondary)' } : {}}>
                                        {entry.rank}
                                    </span>
                                </td>
                                <td style={{ fontWeight: 600 }}>{entry.name}</td>
                                <td style={{ color: 'var(--text-secondary)' }}>{entry.department_name}</td>
                                <td>
                                    <span style={{ color: 'var(--accent)', fontWeight: 600 }}>Lv{entry.level}</span>
                                    <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginLeft: 6 }}>{entry.level_title}</span>
                                </td>
                                <td>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                        <div className="xp-bar" style={{ width: 100 }}>
                                            <div className="xp-bar-fill" style={{ width: `${Math.min(100, (entry.total_xp / 10000) * 100)}%` }} />
                                        </div>
                                        <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>{entry.total_xp.toLocaleString()}</span>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
