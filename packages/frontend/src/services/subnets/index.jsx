import axios from "axios";

const api = axios.create({ timeout: 30000 });

export const listSubnets = async () => {
  const response = await api.get("/api/api/v1/subnets/");
  return response.data;
};

export const getSubnetsSummary = async () => {
  const response = await api.get("/api/api/v1/subnets/summary");
  return response.data;
};

export const getSubnetStatus = async (subnetId) => {
  const response = await api.get(`/api/api/v1/subnets/${subnetId}/status`);
  return response.data;
};

export const getSubnetResults = async (subnetId, blacklistedOnly = false) => {
  const params = blacklistedOnly ? { blacklisted_only: true } : {};
  const response = await api.get(`/api/api/v1/subnets/${subnetId}/results`, { params });
  return response.data;
};

export const triggerSubnetScan = async (subnetId) => {
  const response = await api.post(`/api/api/v1/subnets/${subnetId}/scan`);
  return response.data;
};
