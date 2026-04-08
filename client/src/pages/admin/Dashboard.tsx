import React from 'react';

const AdminDashboard: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          { label: 'Total Stores Active', value: '3', color: 'bg-blue-500' },
          { label: 'Total Employees Active', value: '42', color: 'bg-emerald-500' },
          { label: 'Targets Set (This Week)', value: '38/42', color: 'bg-orange-500' },
          { label: 'Pending Actions', value: '12', color: 'bg-red-500' },
        ].map((stat, i) => (
          <div key={i} className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
            <p className="text-sm font-medium text-slate-500 mb-1">{stat.label}</p>
            <p className="text-3xl font-bold text-slate-800">{stat.value}</p>
            <div className={`h-1 w-12 ${stat.color} rounded-full mt-4`} />
          </div>
        ))}
      </div>
      
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-8">
        <h3 className="text-lg font-bold text-slate-800 mb-6 uppercase tracking-wider">Recent Activity</h3>
        <p className="text-slate-500 italic">No recent configuration changes found.</p>
      </div>
    </div>
  );
};

export default AdminDashboard;
