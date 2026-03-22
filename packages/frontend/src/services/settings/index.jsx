import axios from "axios";

const api = axios.create({ timeout: 30000 });

// API Keys
export const createApiKey = async (data) => {
  const response = await api.post("/api/api-keys/", data);
  return response.data;
};

export const listApiKeys = async () => {
  const response = await api.get("/api/api-keys/");
  return response.data;
};

export const revokeApiKey = async (keyId) => {
  await api.delete(`/api/api-keys/${keyId}`);
};

// Webhooks
export const createWebhook = async (data) => {
  const response = await api.post("/api/webhooks/", data);
  return response.data;
};

export const listWebhooks = async () => {
  const response = await api.get("/api/webhooks/");
  return response.data;
};

export const deleteWebhook = async (webhookId) => {
  await api.delete(`/api/webhooks/${webhookId}`);
};

export const testWebhook = async (webhookId) => {
  const response = await api.post(`/api/webhooks/${webhookId}/test`);
  return response.data;
};

// Alert Rules
export const createAlertRule = async (data) => {
  const response = await api.post("/api/webhooks/alerts/", data);
  return response.data;
};

export const listAlertRules = async () => {
  const response = await api.get("/api/webhooks/alerts/");
  return response.data;
};

export const deleteAlertRule = async (ruleId) => {
  await api.delete(`/api/webhooks/alerts/${ruleId}`);
};
