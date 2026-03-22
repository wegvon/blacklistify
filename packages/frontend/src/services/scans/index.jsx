import axios from "axios";

const api = axios.create({ timeout: 30000 });

export const triggerScan = async (jobType = "sampling") => {
  const response = await api.post("/api/api/v1/scans/", { job_type: jobType });
  return response.data;
};

export const listScanJobs = async (status = null, limit = 20) => {
  const params = { limit };
  if (status) params.status = status;
  const response = await api.get("/api/api/v1/scans/", { params });
  return response.data;
};

export const getScanJob = async (jobId) => {
  const response = await api.get(`/api/api/v1/scans/${jobId}`);
  return response.data;
};

export const getScanJobResults = async (jobId, blacklistedOnly = false) => {
  const params = blacklistedOnly ? { blacklisted_only: true } : {};
  const response = await api.get(`/api/api/v1/scans/${jobId}/results`, { params });
  return response.data;
};

export const getDashboardStats = async () => {
  const response = await api.get("/api/api/v1/dashboard/");
  return response.data;
};

export const getWorstSubnets = async (limit = 10) => {
  const response = await api.get("/api/api/v1/dashboard/worst-subnets", { params: { limit } });
  return response.data;
};

export const getBlacklistTimeline = async (days = 30) => {
  const response = await api.get("/api/api/v1/dashboard/timeline", { params: { days } });
  return response.data;
};
