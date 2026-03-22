import { useEffect, useState } from "react";
import { createWebhook, listWebhooks, deleteWebhook, testWebhook } from "../../services/settings";
import toast from "react-hot-toast";

const AVAILABLE_EVENTS = [
  "blacklist.detected",
  "blacklist.resolved",
  "scan.completed",
  "scan.failed",
  "alert.threshold",
];

export default function Webhooks() {
  const [webhooks, setWebhooks] = useState([]);
  const [url, setUrl] = useState("");
  const [selectedEvents, setSelectedEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchWebhooks();
  }, []);

  const fetchWebhooks = async () => {
    try {
      const data = await listWebhooks();
      setWebhooks(data);
    } catch (err) {
      toast.error("Failed to load webhooks");
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!url.trim() || selectedEvents.length === 0) {
      toast.error("URL and at least one event required");
      return;
    }
    try {
      await createWebhook({ url, events: selectedEvents });
      setUrl("");
      setSelectedEvents([]);
      fetchWebhooks();
      toast.success("Webhook created");
    } catch (err) {
      toast.error("Failed to create webhook");
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Delete this webhook?")) return;
    try {
      await deleteWebhook(id);
      fetchWebhooks();
      toast.success("Webhook deleted");
    } catch (err) {
      toast.error("Failed to delete webhook");
    }
  };

  const handleTest = async (id) => {
    try {
      const result = await testWebhook(id);
      if (result.success) {
        toast.success(`Test delivered (HTTP ${result.status_code})`);
      } else {
        toast.error(`Test failed: ${result.error || "Unknown error"}`);
      }
    } catch (err) {
      toast.error("Test request failed");
    }
  };

  const toggleEvent = (event) => {
    setSelectedEvents((prev) =>
      prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event]
    );
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-white mb-6">Webhooks</h1>

      {/* Create Webhook */}
      <div className="bg-slate-800 rounded-xl p-4 mb-6">
        <h2 className="text-sm font-medium text-slate-300 mb-3">Create Webhook</h2>
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://your-endpoint.com/webhook"
          className="w-full px-3 py-2 bg-slate-700 rounded-lg text-white text-sm border border-slate-600 focus:border-cyan-500 outline-none mb-3"
        />
        <div className="flex flex-wrap gap-2 mb-3">
          {AVAILABLE_EVENTS.map((event) => (
            <button
              key={event}
              onClick={() => toggleEvent(event)}
              className={`px-3 py-1 text-xs rounded-full border ${
                selectedEvents.includes(event)
                  ? "border-cyan-500 bg-cyan-500/20 text-cyan-400"
                  : "border-slate-600 text-slate-400 hover:border-slate-500"
              }`}
            >
              {event}
            </button>
          ))}
        </div>
        <button
          onClick={handleCreate}
          className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm"
        >
          Create Webhook
        </button>
      </div>

      {/* Webhooks Table */}
      <div className="bg-slate-800 rounded-xl overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-slate-700">
            <tr>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">URL</th>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">Events</th>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">Status</th>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            {webhooks.map((w) => (
              <tr key={w.id}>
                <td className="px-4 py-3 text-sm text-white max-w-xs truncate">{w.url}</td>
                <td className="px-4 py-3 text-sm text-slate-300">
                  {(w.events || []).join(", ")}
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    w.is_active ? "bg-emerald-500/20 text-emerald-400" : "bg-rose-500/20 text-rose-400"
                  }`}>
                    {w.is_active ? "Active" : "Disabled"}
                  </span>
                </td>
                <td className="px-4 py-3 flex gap-2">
                  <button onClick={() => handleTest(w.id)} className="text-sm text-cyan-400 hover:text-cyan-300">Test</button>
                  <button onClick={() => handleDelete(w.id)} className="text-sm text-rose-400 hover:text-rose-300">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
