import React from 'react';

const EmployeeManagement: React.FC = () => {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="p-6 border-b border-slate-100 flex justify-between items-center">
        <h3 className="font-bold text-slate-800 uppercase tracking-wider text-sm">Employee Directory</h3>
        <button className="px-4 py-2 bg-orange-500 text-white rounded-lg text-sm font-bold shadow-lg shadow-orange-500/20 hover:scale-105 transition-transform">
          Add New Employee
        </button>
      </div>
      <table className="w-full text-left">
        <thead className="bg-slate-50 text-slate-500 text-[10px] uppercase font-bold tracking-widest border-b border-slate-100">
          <tr>
            <th className="px-6 py-4">ID</th>
            <th className="px-6 py-4">Name</th>
            <th className="px-6 py-4">Store</th>
            <th className="px-6 py-4">Dept</th>
            <th className="px-6 py-4">Shift</th>
            <th className="px-6 py-4">P Score</th>
            <th className="px-6 py-4">Status</th>
            <th className="px-6 py-4">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 text-sm text-slate-600">
          <tr>
            <td className="px-6 py-4 font-mono">E001001</td>
            <td className="px-6 py-4 font-bold text-slate-800">Suryaraj Sinh</td>
            <td className="px-6 py-4 font-bold">Navrangpura (S001)</td>
            <td className="px-6 py-4">Men's Wear</td>
            <td className="px-6 py-4 font-mono text-xs">09:00 - 18:00</td>
            <td className="px-6 py-4 text-orange-600 font-bold">88.5</td>
            <td className="px-6 py-4">
              <span className="px-2 py-1 bg-green-100 text-green-700 rounded-md text-[10px] font-bold uppercase border border-green-200">Active</span>
            </td>
            <td className="px-6 py-4 space-x-2">
              <button className="text-blue-500 font-bold hover:underline">Edit</button>
              <button className="text-red-500 font-bold hover:underline">Password</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
};

export default EmployeeManagement;
