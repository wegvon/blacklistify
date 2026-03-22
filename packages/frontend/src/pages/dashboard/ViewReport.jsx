import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import ResultTable from '../../components/blacklist/ResultTable';

export default function ViewReport() {
  const location = useLocation();
  const navigate = useNavigate();
  const hostnameData = location.state?.hostnameData;

  if (!hostnameData) {
    return (
      <section className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
        <p className="text-slate-500 text-sm">No report data available.</p>
        <button
          className="mt-3 text-sm font-medium text-cyan-700 hover:text-cyan-800"
          onClick={() => navigate('/dashboard/blacklist-monitor')}
        >
          Back to Monitors
        </button>
      </section>
    );
  }

  return (
    <section className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
      <div className="rounded-xl border border-slate-200 p-4">
        <div className="inline-block min-w-full py-2">
          <h1 className="text-2xl font-semibold mb-4 text-slate-900">Report of {hostnameData.hostname}</h1>
          <ResultTable data={hostnameData.result}/>
        </div>
      </div>
    </section>
  )
}
