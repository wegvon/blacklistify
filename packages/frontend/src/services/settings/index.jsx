import axios from "axios";



// API Keys
export const createApiKey = async (data) => {
  const response = await axios.post("/api/api-keys/", data);
  return response.data;
};

export const listApiKeys = async () => {
  const response = await axios.get("/api/api-keys/");
  return response.data;
};

export const revokeApiKey = async (keyId) => {
  await axios.delete(`/api/api-keys/${keyId}`);
};

// Webhooks
export const createWebhook = async (data) => {
  const response = await axios.post("/api/webhooks/", data);
  return response.data;
};

export const listWebhooks = async () => {
  const response = await axios.get("/api/webhooks/");
  return response.data;
};

export const deleteWebhook = async (webhookId) => {
  await axios.delete(`/api/webhooks/${webhookId}`);
};

export const testWebhook = async (webhookId) => {
  const response = await axios.post(`/api/webhooks/${webhookId}/test`);
  return response.data;
};

// Alert Rules
export const createAlertRule = async (data) => {
  const response = await axios.post("/api/webhooks/alerts/", data);
  return response.data;
};

export const listAlertRules = async () => {
  const response = await axios.get("/api/webhooks/alerts/");
  return response.data;
};

export const deleteAlertRule = async (ruleId) => {
  await axios.delete(`/api/webhooks/alerts/${ruleId}`);
};
