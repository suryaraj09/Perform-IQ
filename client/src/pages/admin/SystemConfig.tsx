import React from 'react';

const SystemConfig: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden p-8">
        <h3 className="font-bold text-slate-800 uppercase tracking-wider text-sm mb-6 border-b border-slate-100 pb-4">Metric Weights (P-Score Formula)</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[
            { key: 'M1', label: 'Revenue vs Target', val: '0.30' },
            { key: 'M2', label: 'Basket Size', val: '0.25' },
            { key: 'M3', label: 'Manager Rating', val: '0.15' },
            { key: 'M4', label: 'Growth Trend', val: '0.10' },
            { key: 'M5', label: 'Stability Index', val: '0.10' },
            { key: 'M7', label: 'Attendance', val: '0.05' },
            { key: 'M8', label: 'Punctuality', val: '0.05' },
          ].map((m, i) => (
            <div key={i} className="space-y-2">
              <label className="text-[10px] uppercase font-bold text-slate-400">{m.label} ({m.key})</label>
              <input type="text" className="w-full bg-slate-50 border border-slate-200 rounded-lg px-4 py-2 font-mono font-bold text-orange-600" defaultValue={m.val} />
            </div>
          ))}
        </div>
        <div className="mt-8 flex items-center justify-between border-t border-slate-100 pt-6">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-slate-800">Current Total:</span>
            <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-bold border border-green-200">1.00 ✓</span>
          </div>
          <button className="px-6 py-2 bg-orange-500 text-white rounded-lg text-sm font-bold shadow-lg shadow-orange-500/20 hover:scale-105 transition-transform">
            Save Config Changes
          </button>
        </div>
      </div>
      
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden p-8">
        <h3 className="font-bold text-slate-800 uppercase tracking-wider text-sm mb-6 border-b border-slate-100 pb-4">Thresholds & XP</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="space-y-4">
             <h4 className="text-xs font-bold text-slate-500">Flag Thresholds</h4>
             <div className="space-y-2">
                <label className="text-[10px] text-slate-400 uppercase font-bold">High Sale Multiplier</label>
                <input type="text" className="w-full bg-slate-50 border border-slate-200 rounded-lg px-4 py-2 font-mono font-bold" defaultValue="3" />
             </div>
             <div className="space-y-2">
                <label className="text-[10px] text-slate-400 uppercase font-bold">High Item Count</label>
                <input type="text" className="w-full bg-slate-50 border border-slate-200 rounded-lg px-4 py-2 font-mono font-bold" defaultValue="15" />
             </div>
          </div>
          <div className="space-y-4">
             <h4 className="text-xs font-bold text-slate-500">Punctuality Grace</h4>
             <div className="space-y-2">
                <label className="text-[10px] text-slate-400 uppercase font-bold">Full Score (Min)</label>
                <input type="text" className="w-full bg-slate-50 border border-slate-200 rounded-lg px-4 py-2 font-mono font-bold" defaultValue="15" />
             </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemConfig;
