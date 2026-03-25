import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getScanJob, getScanJobResults } from "../../services/scans";
import toast from "react-hot-toast";

export default function ScanDetail() {
  const { scanId } = useParams();
  const [job, setJob] = useState(null);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, [scanId]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const jobData = await getScanJob(scanId);
      setJob(jobData);

      const resultsData = await getScanJobResults(scanId, false);
      setResults(resultsData.results || []);
    } catch (err) {
      toast.error("Failed to load scan details");
    } finally {
      setLoading(false);
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

  if (!job) {
    return <div className="flex items-center justify-center h-64"><p className="text-slate-400">Scan not found</p></div>;
  }

  const blacklistedCount = results.filter(r => r.is_blacklisted).length;

  return (
    <div className="p-6">
      <div className="flex items-center gap-4 mb-6">
        <Link to="/dashboard/scans" className="text-slate-400 hover:text-white">
          ← Back
        </Link>
        <h1 className="text-2xl font-bold text-white">Job #{job.id}</h1>
        <span>{statusBadge(job.status)}</span>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-slate-800 rounded-lg p-4">
          <p className="text-xs text-slate-400">Type</p>
          <p className="text-xl font-bold text-white">{job.job_type}</p>
        </div>
        <div className="bg-slate-800 rounded-lg p-4">
          <p className="text-xs text-slate-400">Total IPs</p>
          <p className="text-2xl font-bold text-white">{job.total_ips}</p>
        </div>
        <div className="bg-slate-800 rounded-lg p-4">
          <p className="text-xs text-slate-400">Scanned</p>
          <p className="text-2xl font-bold text-cyan-400">{job.scanned_ips}</p>
        </div>
        <div className="bg-slate-800 rounded-lg p-4">
          <p className="text-xs text-slate-400">Blacklisted</p>
          <p className="text-2xl font-bold text-rose-400">{job.blacklisted_ips}</p>
        </div>
        <div className="bg-slate-800 rounded-lg p-4">
          <p className="text-xs text-slate-400">Started</p>
          <p className="text-lg font-medium text-white">
            {job.started_at ? new Date(job.started_at).toLocaleString() : "-"}
          </p>
        </div>
        <div className="bg-slate-800 rounded-lg p-4">
          <p className="text-xs text-slate-400">Completed</p>
          <p className="text-lg font-medium text-white">
            {job.completed_at ? new Date(job.completed_at).toLocaleString() : "-"}
          </p>
        </div>
      </div>

      <div className="bg-slate-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-white">
            Scan Results
            {blacklistedCount > 0 && (
              <span className="ml-2 text-rose-400">({blacklistedCount} blacklisted)</span>
            )}
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-slate-700">
              <tr>
                <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">IP Address</th>
                <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">Status</th>
                <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">Providers</th>
                <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">Checked At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {results.map((result) => (
                <tr key={result.id} className={result.is_blacklisted ? "bg-rose-900/20" : ""}>
                  <td className="px-4 py-3 text-sm font-mono text-white">{result.ip_address}</td>
                  <td className="px-4 py-3">
                    {result.is_blacklisted ? (
                      <span className="px-2 py-1 text-xs rounded-full bg-rose-500/20 text-rose-400">Blacklisted</span>
                    ) : (
                      <span className="px-2 py-1 text-xs rounded-full bg-emerald-500/20 text-emerald-400">Clean</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-300">
                    {result.is_blacklisted && result.providers_detected ? (
                      <span className="text-rose-400">
                        {result.providers_detected.map(p => p.provider).join(", ")}
                      </span>
                    ) : "-"}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-400">
                    {result.checked_at ? new Date(result.checked_at).toLocaleString() : "-"}
                  </td>
                </tr>
              ))}
              {results.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-slate-400">No results found</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
