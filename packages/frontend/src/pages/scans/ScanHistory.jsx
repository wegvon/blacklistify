import { useEffect, useState } from "react";
import { listScanJobs, triggerScan } from "../../services/scans";
import toast from "react-hot-toast";

export default function ScanHistory() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchJobs();
  }, []);

  const fetchJobs = async () => {
    try {
      const data = await listScanJobs(null, 50);
      setJobs(data);
    } catch (err) {
      toast.error("Failed to load scan history");
    } finally {
      setLoading(false);
    }
  };

  const handleTrigger = async (type) => {
    try {
      await triggerScan(type);
      toast.success(`${type} scan triggered`);
      setTimeout(fetchJobs, 2000);
    } catch (err) {
      toast.error("Failed to trigger scan");
    }
  };

  const statusBadge = (status) => {
    const colors = {
      pending: "bg-slate-500/20 text-slate-400",
      running: "bg-cyan-500/20 text-cyan-400",
      completed: "bg-emerald-500/20 text-emerald-400",
      failed: "bg-rose-500/20 text-rose-400",
    };
    return (
      <span className={`px-2 py-1 text-xs rounded-full ${colors[status] || colors.pending}`}>
        {status}
      </span>
    );
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><p className="text-slate-400">Loading...</p></div>;
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Scan History</h1>
        <div className="flex gap-2">
          <button
            onClick={() => handleTrigger("sampling")}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm"
          >
            Sampling Scan
          </button>
          <button
            onClick={() => handleTrigger("full")}
            className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-sm"
          >
            Full Scan
          </button>
        </div>
      </div>

      <div className="bg-slate-800 rounded-xl overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-slate-700">
            <tr>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">ID</th>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">Type</th>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">Status</th>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">IPs</th>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">Blacklisted</th>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">Started</th>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">Completed</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            {jobs.map((job) => (
              <tr key={job.id} className="hover:bg-slate-750">
                <td className="px-4 py-3 text-sm text-white">#{job.id}</td>
                <td className="px-4 py-3 text-sm text-slate-300">{job.job_type}</td>
                <td className="px-4 py-3">{statusBadge(job.status)}</td>
                <td className="px-4 py-3 text-sm text-slate-300">
                  {job.scanned_ips}/{job.total_ips}
                </td>
                <td className="px-4 py-3 text-sm text-rose-400">{job.blacklisted_ips}</td>
                <td className="px-4 py-3 text-sm text-slate-400">
                  {job.started_at ? new Date(job.started_at).toLocaleString() : "-"}
                </td>
                <td className="px-4 py-3 text-sm text-slate-400">
                  {job.completed_at ? new Date(job.completed_at).toLocaleString() : "-"}
                </td>
              </tr>
            ))}
            {jobs.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                  No scans yet. Trigger a sampling or full scan to get started.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
