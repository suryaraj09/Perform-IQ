import React from 'react';

const DataExports: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="flex border-b border-slate-100">
          {['Sales', 'Weekly Scores', 'Attendance'].map((tab, i) => (
            <button key={i} className={`px-8 py-4 text-xs font-bold uppercase tracking-widest ${i === 0 ? 'border-b-2 border-orange-500 text-orange-600 bg-orange-50/50' : 'text-slate-400 hover:text-slate-600'}`}>
              {tab}
            </button>
          ))}
        </div>
        
        <div className="p-6 bg-slate-50/50 border-b border-slate-100 flex justify-between items-center gap-4">
           <div className="flex gap-4">
              <select className="bg-white border border-slate-200 rounded-lg px-4 py-2 text-sm font-medium">
                 <option>All Stores</option>
                 <option>S001 - Navrangpura</option>
              </select>
              <input type="date" className="bg-white border border-slate-200 rounded-lg px-4 py-2 text-sm font-medium" />
           </div>
           <button className="px-6 py-2 bg-[#1a2332] text-white rounded-lg text-sm font-bold shadow-lg flex items-center gap-2 hover:scale-105 transition-transform">
             Export CSV
           </button>
        </div>
        
        <div className="p-0 overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-slate-50 text-slate-500 text-[10px] uppercase font-bold tracking-widest border-b border-slate-100">
              <tr>
                <th className="px-6 py-4">Date</th>
                <th className="px-6 py-4">Employee</th>
                <th className="px-6 py-4">Store</th>
                <th className="px-6 py-4">Amount</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Flagged</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm text-slate-600 italic">
              <tr>
                 <td colSpan={6} className="px-6 py-12 text-center text-slate-400">Apply filters to preview data.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      
      <div className="bg-white rounded-2xl shadow-sm border border-red-100 overflow-hidden p-8">
         <h3 className="font-bold text-red-800 uppercase tracking-wider text-sm mb-4">Data Health Monitor</h3>
         <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-orange-50 border border-orange-100 p-4 rounded-xl flex items-center gap-4">
               <div className="bg-orange-500 p-2 rounded-lg text-white font-bold text-xs uppercase">Warning</div>
               <div>
                  <p className="text-sm font-bold text-slate-800">12 employees have no targets set for this week.</p>
                  <p className="text-[10px] text-orange-600 uppercase font-bold tracking-tight">Requires Attention</p>
               </div>
            </div>
         </div>
      </div>
    </div>
  );
};

export default DataExports;
