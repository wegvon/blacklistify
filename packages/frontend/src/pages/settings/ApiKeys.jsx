import { useEffect, useState } from "react";
import { createApiKey, listApiKeys, revokeApiKey } from "../../services/settings";
import toast from "react-hot-toast";

export default function ApiKeys() {
  const [keys, setKeys] = useState([]);
  const [newKeyName, setNewKeyName] = useState("");
  const [createdKey, setCreatedKey] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchKeys();
  }, []);

  const fetchKeys = async () => {
    try {
      const data = await listApiKeys();
      setKeys(data);
    } catch (err) {
      toast.error("Failed to load API keys");
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!newKeyName.trim()) return;
    try {
      const result = await createApiKey({ name: newKeyName, scopes: ["read", "scan"] });
      setCreatedKey(result.key);
      setNewKeyName("");
      fetchKeys();
      toast.success("API key created");
    } catch (err) {
      toast.error("Failed to create API key");
    }
  };

  const handleRevoke = async (id) => {
    if (!confirm("Revoke this API key?")) return;
    try {
      await revokeApiKey(id);
      fetchKeys();
      toast.success("API key revoked");
    } catch (err) {
      toast.error("Failed to revoke key");
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-white mb-6">API Keys</h1>

      {/* Create Key */}
      <div className="bg-slate-800 rounded-xl p-4 mb-6">
        <h2 className="text-sm font-medium text-slate-300 mb-3">Create New API Key</h2>
        <div className="flex gap-2">
          <input
            type="text"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            placeholder="Key name (e.g., Ripefy Production)"
            className="flex-1 px-3 py-2 bg-slate-700 rounded-lg text-white text-sm border border-slate-600 focus:border-cyan-500 outline-none"
          />
          <button
            onClick={handleCreate}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm"
          >
            Create
          </button>
        </div>

        {createdKey && (
          <div className="mt-3 p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
            <p className="text-xs text-amber-400 mb-1">Copy this key now. It will not be shown again.</p>
            <code className="text-sm text-amber-300 break-all">{createdKey}</code>
          </div>
        )}
      </div>

      {/* Keys Table */}
      <div className="bg-slate-800 rounded-xl overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-slate-700">
            <tr>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">Name</th>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">Prefix</th>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">Scopes</th>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">Last Used</th>
              <th className="px-4 py-3 text-xs font-medium text-slate-300 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            {keys.map((k) => (
              <tr key={k.id}>
                <td className="px-4 py-3 text-sm text-white">{k.name}</td>
                <td className="px-4 py-3 text-sm font-mono text-slate-300">{k.key_prefix}...</td>
                <td className="px-4 py-3 text-sm text-slate-300">{(k.scopes || []).join(", ")}</td>
                <td className="px-4 py-3 text-sm text-slate-400">
                  {k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : "Never"}
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => handleRevoke(k.id)}
                    className="text-sm text-rose-400 hover:text-rose-300"
                  >
                    Revoke
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
