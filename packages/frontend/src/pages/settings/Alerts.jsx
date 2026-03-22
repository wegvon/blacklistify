import { useEffect, useState } from "react";
import { createAlertRule, listAlertRules, deleteAlertRule, listWebhooks } from "../../services/settings";
import toast from "react-hot-toast";

export default function Alerts() {
  const [rules, setRules] = useState([]);
  const [webhooks, setWebhooks] = useState([]);
  const [form, setForm] = useState({ name: "", condition_type: "blacklist_detected", threshold: "", subnet_filter: "", webhook_id: "" });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchRules(), fetchWebhooks()]).finally(() => setLoading(false));
  }, []);

  const fetchRules = async () => {
    try { setRules(await listAlertRules()); } catch { toast.error("Failed to load alert rules"); }
  };

  const fetchWebhooks = async () => {
    try { setWebhooks(await listWebhooks()); } catch {}
  };

  const handleCreate = async () => {
    if (!form.name || !form.webhook_id) {
      toast.error("Name and webhook are required");
      return;
    }
    try {
      await createAlertRule({
        name: form.name,
        condition_type: form.condition_type,
        threshold: form.threshold ? parseFloat(form.threshold) : null,
        subnet_filter: form.subnet_filter || null,
        webhook_id: parseInt(form.webhook_id),
      });
      setForm({ name: "", condition_type: "blacklist_detected", threshold: "", subnet_filter: "", webhook_id: "" });
      fetchRules();
      toast.success("Alert rule created");
    } catch {
      toast.error("Failed to create alert rule");
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Delete this alert rule?")) return;
    try { await deleteAlertRule(id); fetchRules(); toast.success("Alert rule deleted"); } catch { toast.error("Failed to delete"); }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><p className="text-slate-400">Loading...</p></div>;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-white mb-6">Alert Rules</h1>

      <div className="bg-slate-800 rounded-xl p-4 mb-6">
        <h2 className="text-sm font-medium text-slate-300 mb-3">Create Alert Rule</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <input type="text" placeholder="Rule name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="px-3 py-2 bg-slate-700 rounded-lg text-white text-sm border border-slate-600 outline-none" />
          <select value={form.condition_type} onChange={(e) => setForm({ ...form, condition_type: e.target.value })} className="px-3 py-2 bg-slate-700 rounded-lg text-white text-sm border border-slate-600 outline-none">
            <option value="blacklist_detected">Blacklist Detected</option>
            <option value="blacklist_rate_above">Blacklist Rate Above Threshold</option>
            <option value="scan_failed">Scan Failed</option>
          </select>
          <input type="text" placeholder="Threshold (e.g. 0.05)" value={form.threshold} onChange={(e) => setForm({ ...form, threshold: e.target.value })} className="px-3 py-2 bg-slate-700 rounded-lg text-white text-sm border border-slate-600 outline-none" />
          <select value={form.webhook_id} onChange={(e) => setForm({ ...form, webhook_id: e.target.value })} className="px-3 py-2 bg-slate-700 rounded-lg text-white text-sm border border-slate-600 outline-none">
            <option value="">Select Webhook</option>
            {webhooks.map((w) => <option key={w.id} value={w.id}>{w.url}</option>)}
          </select>
        </div>
        <button onClick={handleCreate} className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm">Create Rule</button>
      </div>

      <div className="bg-slate-800 rounded-xl overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-slate-700">
            <tr>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">Name</th>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">Condition</th>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">Threshold</th>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">Status</th>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            {rules.map((r) => (
              <tr key={r.id}>
                <td className="px-4 py-3 text-sm text-white">{r.name}</td>
                <td className="px-4 py-3 text-sm text-slate-300">{r.condition_type}</td>
                <td className="px-4 py-3 text-sm text-slate-300">{r.threshold || "-"}</td>
                <td className="px-4 py-3"><span className={`px-2 py-1 text-xs rounded-full ${r.is_active ? "bg-emerald-500/20 text-emerald-400" : "bg-rose-500/20 text-rose-400"}`}>{r.is_active ? "Active" : "Disabled"}</span></td>
                <td className="px-4 py-3"><button onClick={() => handleDelete(r.id)} className="text-sm text-rose-400 hover:text-rose-300">Delete</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
