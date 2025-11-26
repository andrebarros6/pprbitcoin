// API types matching the backend Pydantic models

export interface PPR {
  id: string;  // UUID
  nome: string;  // Portuguese: name
  gestor: string;  // Portuguese: manager
  isin: string | null;
  categoria: string | null;  // Portuguese: category
  taxa_gestao: number | null;  // Portuguese: management fee (TER) - stored as percentage (e.g., 1.95 for 1.95%)
}

export interface PPRAllocation {
  ppr_id: string;  // UUID string
  allocation_percentage: number;  // 0-100
}

export interface PortfolioRequest {
  ppr_allocations: PPRAllocation[];
  bitcoin_percentage: number;  // 0-100
  initial_investment: number;
  start_date: string;
  end_date?: string;
  rebalancing_frequency: 'none' | 'monthly' | 'quarterly' | 'yearly';
}

export interface PortfolioMetrics {
  total_return: string;  // Decimal from backend
  total_return_percentage: string;  // Decimal from backend
  annualized_return: string;  // Decimal from backend
  cagr: string;  // Decimal from backend
  volatility: string;  // Decimal from backend
  sharpe_ratio: string;  // Decimal from backend
  sortino_ratio: string;  // Decimal from backend
  max_drawdown: string;  // Decimal from backend
  max_drawdown_duration_days: number;
  final_value: string;  // Decimal from backend
  best_month: string;  // Decimal from backend
  worst_month: string;  // Decimal from backend
  positive_months: number;
  total_months: number;
}

export interface HistoricalDataPoint {
  data: string;  // Date from backend (renamed from 'date' to 'data')
  portfolio_value: string;  // Decimal from backend (renamed from 'value')
  ppr_value: string;  // Decimal from backend
  bitcoin_value: string;  // Decimal from backend
  total_return: string;  // Decimal from backend
  drawdown: string;  // Decimal from backend
}

export interface PortfolioResponse {
  portfolio_config: PortfolioRequest;
  metrics: PortfolioMetrics;
  historical_data: HistoricalDataPoint[];  // Renamed from time_series
  allocation_breakdown: Array<{
    asset_name: string;
    allocation_percentage: string;  // Decimal from backend
    final_value: string;  // Decimal from backend
    contribution_to_return: string;  // Decimal from backend
  }>;
  calculation_date: string;  // Date from backend
}

export interface CompareRequest {
  portfolios: PortfolioRequest[];
  portfolio_names?: string[];
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
