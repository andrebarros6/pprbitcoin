import axios from 'axios';
import type { PPR, PortfolioRequest, PortfolioResponse, CompareRequest, CompareResponse } from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// PPR endpoints
export const getPPRs = async (): Promise<PPR[]> => {
  const response = await apiClient.get<{ data: PPR[]; total: number }>('/api/v1/pprs');
  return response.data.data;
};

export const getPPR = async (id: number): Promise<PPR> => {
  const response = await apiClient.get<PPR>(`/api/v1/pprs/${id}`);
  return response.data;
};

// Portfolio calculation endpoints
export const calculatePortfolio = async (request: PortfolioRequest): Promise<PortfolioResponse> => {
  const response = await apiClient.post<PortfolioResponse>('/api/v1/portfolio/calculate', request);
  return response.data;
};

export const comparePortfolios = async (request: CompareRequest): Promise<CompareResponse> => {
  const response = await apiClient.post<CompareResponse>('/api/v1/portfolio/compare', request);
  return response.data;
};

// Health check
export const healthCheck = async (): Promise<{ status: string }> => {
  const response = await apiClient.get<{ status: string }>('/health');
  return response.data;
};

export default apiClient;
