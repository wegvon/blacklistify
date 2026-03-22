import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getSubnetStatus, getSubnetResults, triggerSubnetScan } from "../../services/subnets";
import toast from "react-hot-toast";

export default function SubnetDetail() {
  const { subnetId } = useParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);

  useEffect(() => {
    fetchData();
  }, [subnetId]);

  const fetchData = async () => {
    try {
      const [statusData, resultsData] = await Promise.all([
        getSubnetStatus(subnetId).catch(() => null),
        getSubnetResults(subnetId, true).catch(() => []),
      ]);
      setStatus(statusData);
      setResults(resultsData);
    } catch (err) {
      toast.error("Failed to load subnet data");
    } finally {
      setLoading(false);
    }
  };

  const handleScan = async () => {
    setScanning(true);
    try {
      const result = await triggerSubnetScan(subnetId);
      toast.success(`Scan started: ${result.total_ips} IPs in ${result.batches} batches`);
    } catch (err) {
      toast.error("Failed to trigger scan");
    } finally {
      setScanning(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><p className="text-slate-400">Loading...</p></div>;
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <button onClick={() => navigate("/dashboard/subnets")} className="text-sm text-slate-400 hover:text-white mb-2">
            &larr; Back to Subnets
          </button>
          <h1 className="text-2xl font-bold text-white font-mono">
            {status?.subnet_cidr || subnetId}
          </h1>
        </div>
        <button
          onClick={handleScan}
          disabled={scanning}
          className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm disabled:opacity-50"
        >
          {scanning ? "Scanning..." : "Run Scan"}
        </button>
      </div>

      {/* Status Cards */}
      {status && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-slate-800 rounded-xl p-4">
            <p className="text-sm text-slate-400">Total IPs</p>
            <p className="text-2xl font-bold text-sky-400">{status.total_ips}</p>
          </div>
          <div className="bg-slate-800 rounded-xl p-4">
            <p className="text-sm text-slate-400">Blacklisted</p>
            <p className="text-2xl font-bold text-rose-400">{status.blacklisted_ips}</p>
          </div>
          <div className="bg-slate-800 rounded-xl p-4">
            <p className="text-sm text-slate-400">Clean</p>
            <p className="text-2xl font-bold text-emerald-400">{status.clean_ips}</p>
          </div>
          <div className="bg-slate-800 rounded-xl p-4">
            <p className="text-sm text-slate-400">Blacklist Rate</p>
            <p className="text-2xl font-bold text-amber-400">
              {(status.blacklist_rate * 100).toFixed(2)}%
            </p>
          </div>
        </div>
      )}

      {/* Blacklisted IPs Table */}
      <h2 className="text-lg font-semibold text-white mb-4">Blacklisted IPs</h2>
      <div className="bg-slate-800 rounded-xl overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-slate-700">
            <tr>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">IP Address</th>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">Providers</th>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">Checked At</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            {results.map((r) => (
              <tr key={r.id}>
                <td className="px-4 py-3 text-sm font-mono text-white">{r.ip_address}</td>
                <td className="px-4 py-3 text-sm text-slate-300">
                  {(r.providers_detected || []).map((p) => p.provider).join(", ") || "-"}
                </td>
                <td className="px-4 py-3 text-sm text-slate-400">
                  {r.checked_at ? new Date(r.checked_at).toLocaleString() : "-"}
                </td>
              </tr>
            ))}
            {results.length === 0 && (
              <tr>
                <td colSpan={3} className="px-4 py-8 text-center text-slate-400">
                  {status ? "No blacklisted IPs found" : "No scan data yet. Run a scan to check this subnet."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
