// API types matching the backend Pydantic models

export interface PPR {
  id: string;  // UUID
  nome: string;  // Portuguese: name
  gestor: string;  // Portuguese: manager
  isin: string | null;
  categoria: string | null;  // Portuguese: category
  taxa_gestao: number | null;  // Portuguese: management fee (TER) - stored as percentage (e.g., 1.95 for 1.95%)
  market_rank: number | null;  // Position by AUM among Portuguese PPRs; null outside the top 10
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
  contribution_amount?: number;  // Recurring contribution in EUR (0 = lump sum)
  contribution_frequency?: 'none' | 'monthly' | 'quarterly';
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
  invested_capital: string;  // Decimal from backend: total cash paid in
  // Money-weighted annualised return (XIRR). Null when the cashflows admit
  // no solution. This is the figure to show once contributions exist.
  irr: string | null;
  // True when contributions are present, meaning cagr is an approximation
  // and irr is the correct headline return.
  is_money_weighted: boolean;
}

export interface HistoricalDataPoint {
  data: string;  // Date from backend (renamed from 'date' to 'data')
  portfolio_value: string;  // Decimal from backend (renamed from 'value')
  ppr_value: string;  // Decimal from backend
  bitcoin_value: string;  // Decimal from backend
  invested_capital: string;  // Decimal from backend: cash paid in by this date
  total_return: string;  // Decimal from backend
  drawdown: string;  // Decimal from backend
}

export interface PortfolioResponse {
  portfolio_config: PortfolioRequest;
  metrics: PortfolioMetrics;
  historical_data: HistoricalDataPoint[];  // Renamed from time_series
  // The backend also returns allocation_breakdown. It is deliberately not
  // declared here: nothing renders it, and the previous declaration had
  // drifted from the API (asset_name/final_value where the backend sends
  // ppr_name/current_value) without anything catching it. Declare it from
  // the real response shape when a component actually needs it.
  calculation_date: string;  // Date from backend
}

export interface CompareRequest {
  portfolios: PortfolioRequest[];
  portfolio_names?: string[];
}

export interface CompareResponse {
  portfolios: PortfolioResponse[];
  comparison_summary: ComparisonSummary;
}

/**
 * Shape actually returned by POST /api/v1/portfolio/compare.
 *
 * Each entry of metrics_comparison names the winning portfolio for that
 * metric. "Best" is metric-aware on the backend: lowest wins for volatility
 * and drawdown, highest for the rest.
 */
export interface MetricComparison {
  values: number[];
  best_index: number;
  best_portfolio: string;
}

export interface ComparisonSummary {
  portfolios: string[];
  metrics_comparison: {
    total_return_percentage: MetricComparison;
    cagr: MetricComparison;
    volatility: MetricComparison;
    sharpe_ratio: MetricComparison;
    max_drawdown: MetricComparison;
    final_value: MetricComparison;
  };
  recommended_portfolio: {
    index: number;
    name: string;
    reason: string;
  };
}
