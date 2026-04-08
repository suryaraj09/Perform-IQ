import React from 'react';

const RatingManagement: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
          <div className="flex gap-4 items-center">
            <h3 className="font-bold text-slate-800 uppercase tracking-wider text-sm">Rating Completion Status</h3>
            <div className="px-3 py-1 bg-white border border-slate-200 rounded-lg text-xs font-bold text-slate-600">Today: April 5, 2026</div>
          </div>
          <button className="px-6 py-2 bg-orange-500 text-white rounded-lg text-sm font-bold shadow-lg shadow-orange-500/20 hover:scale-105 transition-transform">
             Manual Overwrite (Bulk)
          </button>
        </div>
        
        <div className="p-8 grid grid-cols-1 md:grid-cols-3 gap-6 border-b border-slate-100">
          {[
            { store: 'Navrangpura', status: 'Completed', count: '14/14', color: 'text-green-600', bg: 'bg-green-100' },
            { store: 'Satellite', status: 'Pending', count: '8/12', color: 'text-orange-600', bg: 'bg-orange-100' },
            { store: 'Bopal', status: 'Incomplete', count: '0/15', color: 'text-red-600', bg: 'bg-red-100' },
          ].map((s, i) => (
             <div key={i} className="p-6 bg-slate-50 rounded-2xl border border-slate-100 space-y-3">
                <div className="flex justify-between items-start">
                   <h4 className="font-bold text-slate-800 uppercase text-xs tracking-widest">{s.store}</h4>
                   <span className={`px-2 py-1 ${s.bg} ${s.color} rounded-md text-[10px] font-bold uppercase`}>{s.status}</span>
                </div>
                <div className="flex items-end justify-between">
                   <p className="text-2xl font-bold text-slate-800">{s.count}</p>
                   <p className="text-[10px] uppercase font-bold text-slate-400 mb-1">Total Employees</p>
                </div>
                <div className="w-full h-1 bg-slate-200 rounded-full overflow-hidden">
                   <div className={`h-full bg-orange-500`} style={{ width: i === 0 ? '100%' : i === 1 ? '66%' : '0%' }} />
                </div>
             </div>
          ))}
        </div>
        
        <div className="p-8 space-y-4">
           <h4 className="text-sm font-bold text-slate-800 uppercase tracking-tight flex items-center gap-2">
             <div className="w-2 h-2 bg-orange-500 rounded-full animate-ping" />
             Potential Rating Bias Warning
           </h4>
           <p className="text-sm text-slate-500 leading-relaxed italic border-l-4 border-orange-200 pl-4 py-1">
             Navrangpura (S001) has reported '5/5' ratings for all 14 employees for the last 3 days. 
             This zero-variance pattern typically indicates mass-approval without individual performance assessment.
           </p>
        </div>
      </div>
    </div>
  );
};

export default RatingManagement;
