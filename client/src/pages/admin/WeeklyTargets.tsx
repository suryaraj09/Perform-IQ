import React from 'react';

const WeeklyTargets: React.FC = () => {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="p-6 border-b border-slate-100 flex justify-between items-center">
        <h3 className="font-bold text-slate-800 uppercase tracking-wider text-sm">Target Management (Week 14)</h3>
        <button className="px-4 py-2 bg-orange-500 text-white rounded-lg text-sm font-bold shadow-lg shadow-orange-500/20 hover:scale-105 transition-transform">
          Copy Last Week
        </button>
      </div>
      <table className="w-full text-left">
        <thead className="bg-slate-50 text-slate-500 text-[10px] uppercase font-bold tracking-widest border-b border-slate-100">
          <tr>
            <th className="px-6 py-4">Employee</th>
            <th className="px-6 py-4">Store</th>
            <th className="px-6 py-4">Dept</th>
            <th className="px-6 py-4 text-center">Last Week Target</th>
            <th className="px-6 py-4 text-center">Target (Current Week)</th>
            <th className="px-6 py-4">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 text-sm text-slate-600">
          <tr>
            <td className="px-6 py-4 font-bold text-slate-800">Suryaraj Sinh</td>
            <td className="px-6 py-4">Navrangpura (S001)</td>
            <td className="px-6 py-4">Men's Wear</td>
            <td className="px-6 py-4 text-center text-slate-400 font-mono italic">₹ 2,50,000</td>
            <td className="px-6 py-4">
              <input type="text" className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-1 text-center font-bold text-orange-600 focus:border-orange-500 transition-colors" defaultValue="₹ 2,75,000" />
            </td>
            <td className="px-6 py-4">
              <button className="text-orange-500 font-bold hover:underline">Update</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
};

export default WeeklyTargets;
