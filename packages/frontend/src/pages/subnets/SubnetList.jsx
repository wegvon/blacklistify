import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listBlocks, getSubnetsSummary } from "../../services/subnets";
import toast from "react-hot-toast";

export default function SubnetList() {
  const [subnets, setSubnets] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [blockData, summaryData] = await Promise.all([
          listBlocks(),
          getSubnetsSummary(),
        ]);
        setSubnets(blockData);
        setSummary(summaryData);
      } catch (err) {
        toast.error("Failed to load subnet data");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center h-64"><p className="text-slate-400">Loading subnets...</p></div>;
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-white mb-6">Subnet Monitoring</h1>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <SummaryCard title="Total Subnets" value={summary.total_subnets} color="sky" />
          <SummaryCard title="Total IPs" value={summary.total_ips?.toLocaleString()} color="emerald" />
          <SummaryCard title="Blacklisted" value={summary.blacklisted_ips} color="rose" />
          <SummaryCard title="Blacklist Rate" value={`${(summary.blacklist_rate * 100).toFixed(2)}%`} color="amber" />
        </div>
      )}

      {/* Subnet Table */}
      <div className="bg-slate-800 rounded-xl overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-slate-700">
            <tr>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">CIDR</th>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">Description</th>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">Status</th>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            {subnets.map((subnet) => (
              <tr key={subnet.id} className="hover:bg-slate-750">
                <td className="px-4 py-3 text-sm font-mono text-white">{subnet.cidr}</td>
                <td className="px-4 py-3 text-sm text-slate-300">{subnet.description || "-"}</td>
                <td className="px-4 py-3">
                  <span className="px-2 py-1 text-xs rounded-full bg-emerald-500/20 text-emerald-400">
                    {subnet.status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => navigate(`/dashboard/subnets/${subnet.id}`)}
                    className="text-sm text-cyan-400 hover:text-cyan-300"
                  >
                    View Details
                  </button>
                </td>
              </tr>
            ))}
            {subnets.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-slate-400">
                  No subnets found. Connect Supabase to load Ripefy subnet data.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SummaryCard({ title, value, color }) {
  const colorMap = {
    sky: "text-sky-400",
    emerald: "text-emerald-400",
    rose: "text-rose-400",
    amber: "text-amber-400",
  };

  return (
    <div className="bg-slate-800 rounded-xl p-4">
      <p className="text-sm text-slate-400">{title}</p>
      <p className={`text-2xl font-bold mt-1 ${colorMap[color]}`}>{value}</p>
    </div>
  );
}
