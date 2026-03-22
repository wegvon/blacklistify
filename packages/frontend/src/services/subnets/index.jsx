import axios from "axios";

export const listSubnets = async () => {
  const response = await axios.get("/api/api/v1/subnets/prefixes");
  return response.data;
};

export const listBlocks = async (status = null) => {
  const params = status ? { status } : {};
  const response = await axios.get("/api/api/v1/subnets/blocks", { params });
  return response.data;
};

export const getSubnetsSummary = async () => {
  const response = await axios.get("/api/api/v1/subnets/summary");
  return response.data;
};

export const getBlockStatus = async (blockId) => {
  const response = await axios.get(`/api/api/v1/subnets/blocks/${blockId}/status`);
  return response.data;
};

export const getBlockResults = async (blockId, blacklistedOnly = false) => {
  const params = blacklistedOnly ? { blacklisted_only: true } : {};
  const response = await axios.get(`/api/api/v1/subnets/blocks/${blockId}/results`, { params });
  return response.data;
};

export const triggerBlockScan = async (blockId) => {
  const response = await axios.post(`/api/api/v1/subnets/blocks/${blockId}/scan`);
  return response.data;
};
