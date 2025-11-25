// API types matching the backend Pydantic models

export interface PPR {
  id: string;  // UUID
  nome: string;  // Portuguese: name
  gestor: string;  // Portuguese: manager
  isin: string | null;
  categoria: string | null;  // Portuguese: category
  taxa_gestao: number | null;  // Portuguese: management fee (TER) - stored as percentage (e.g., 1.95 for 1.95%)
}

export interface PortfolioRequest {
  ppr_ids: string[];  // UUID strings
  bitcoin_allocation: number;
  initial_investment: number;
  monthly_contribution: number;
  start_date: string;
  end_date: string;
  rebalancing_frequency: 'none' | 'monthly' | 'quarterly' | 'yearly';
}

export interface PortfolioMetrics {
  total_value: number;
  total_invested: number;
  total_return: number;
  return_percentage: number;
  cagr: number;
  volatility: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown: number;
  max_drawdown_date: string;
  best_month: number;
  worst_month: number;
}

export interface PortfolioTimeSeries {
  date: string;
  value: number;
  invested: number;
  ppr_value: number;
  bitcoin_value: number;
}

export interface PortfolioResponse {
  portfolio_id: string;
  metrics: PortfolioMetrics;
  time_series: PortfolioTimeSeries[];
  allocation: {
    ppr_ids: number[];
    bitcoin_allocation: number;
  };
  parameters: {
    initial_investment: number;
    monthly_contribution: number;
    start_date: string;
    end_date: string;
    rebalancing_frequency: string;
  };
}

export interface CompareRequest {
  portfolios: PortfolioRequest[];
}

export interface CompareResponse {
  portfolios: PortfolioResponse[];
  comparison_summary: {
    best_return: string;
    best_sharpe: string;
    best_sortino: string;
    lowest_volatility: string;
    lowest_drawdown: string;
  };
}
