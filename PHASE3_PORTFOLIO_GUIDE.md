# Phase 3: Portfolio Calculation Engine - Implementation Guide

## What Was Implemented

Phase 3 adds the **core portfolio comparison logic** - the main value proposition of the PPR Bitcoin application. Users can now:

- Calculate historical portfolio performance with PPR + Bitcoin
- Compare multiple investment strategies side-by-side
- Analyze comprehensive financial metrics (CAGR, Sharpe ratio, drawdown, etc.)
- Test different Bitcoin allocation percentages
- Simulate portfolio rebalancing strategies

---

## Files Created/Modified

### New Files

1. **[backend/models/portfolio.py](backend/models/portfolio.py)** - Pydantic schemas for portfolio requests/responses
2. **[backend/services/portfolio_calculator.py](backend/services/portfolio_calculator.py)** - Core calculation engine
3. **[backend/api/routes/portfolio.py](backend/api/routes/portfolio.py)** - REST API endpoints
4. **[backend/tests/test_portfolio_calculator.py](backend/tests/test_portfolio_calculator.py)** - Unit tests

### Modified Files

1. **[backend/app.py](backend/app.py)** - Added portfolio router
2. **[backend/README.md](backend/README.md)** - Updated with Phase 3 documentation
3. **[backend/test_api.py](backend/test_api.py)** - Added portfolio endpoint tests

---

## New API Endpoints

### 1. Calculate Portfolio Performance

**Endpoint:** `POST /api/v1/portfolio/calculate`

Calculate the historical performance of a portfolio with configurable PPR and Bitcoin allocations.

**Example Request:**
```json
{
  "ppr_allocations": [
    {
      "ppr_id": "your-ppr-uuid-here",
      "allocation_percentage": 70
    }
  ],
  "bitcoin_percentage": 30,
  "initial_investment": 10000,
  "start_date": "2020-01-01",
  "end_date": "2024-12-31",
  "rebalancing_frequency": "quarterly"
}
```

**Returns:**
- Complete performance metrics (CAGR, Sharpe ratio, volatility, drawdown)
- Historical portfolio values for charting
- Allocation breakdown with contribution analysis

---

### 2. Compare Portfolio Strategies

**Endpoint:** `POST /api/v1/portfolio/compare`

Compare 2-5 different portfolio strategies to find the optimal allocation.

**Example Request:**
```json
{
  "portfolios": [
    {
      "ppr_allocations": [{"ppr_id": "uuid", "allocation_percentage": 100}],
      "bitcoin_percentage": 0,
      "initial_investment": 10000,
      "start_date": "2020-01-01",
      "rebalancing_frequency": "quarterly"
    },
    {
      "ppr_allocations": [{"ppr_id": "uuid", "allocation_percentage": 70}],
      "bitcoin_percentage": 30,
      "initial_investment": 10000,
      "start_date": "2020-01-01",
      "rebalancing_frequency": "quarterly"
    }
  ],
  "portfolio_names": ["100% PPR", "70% PPR + 30% BTC"]
}
```

**Returns:**
- Full results for each portfolio
- Side-by-side comparison summary
- Recommended strategy based on Sharpe ratio

---

### 3. Get Metrics Documentation

**Endpoint:** `GET /api/v1/portfolio/metrics`

Get detailed documentation for all available financial metrics.

---

## Financial Metrics Calculated

| Metric | Description |
|--------|-------------|
| **Total Return** | Absolute and percentage gain/loss |
| **CAGR** | Compound Annual Growth Rate |
| **Annualized Return** | Average yearly return percentage |
| **Volatility** | Annualized standard deviation (risk measure) |
| **Sharpe Ratio** | Risk-adjusted return (higher is better) |
| **Sortino Ratio** | Downside risk-adjusted return |
| **Max Drawdown** | Largest peak-to-trough decline |
| **Max Drawdown Duration** | Longest period underwater (days) |
| **Best/Worst Month** | Extreme monthly performance |
| **Positive Months** | Number of profitable months |

---

## Testing the Implementation

### Step 1: Start the Database

```bash
# In project root
docker-compose up -d
```

Wait ~10 seconds for PostgreSQL to initialize.

### Step 2: Seed the Database (if not already done)

```bash
cd data/seeds
python setup_database.py
```

This populates:
- 10 PPR funds
- Bitcoin historical data
- Sample PPR historical data

### Step 3: Start the API Server

```bash
cd backend
python app.py
```

The server starts at: http://localhost:8000

### Step 4: Test with Swagger UI

1. Open http://localhost:8000/docs
2. Navigate to the **Portfolio** section
3. Try the `/portfolio/calculate` endpoint:
   - Click "Try it out"
   - Get a PPR ID from the `/pprs` endpoint first
   - Fill in the request body with your desired allocation
   - Click "Execute"

### Step 5: Run Automated Tests

```bash
cd backend
python test_api.py
```

This runs comprehensive tests including:
- System endpoints
- PPR endpoints
- Bitcoin endpoints
- **Portfolio endpoints (NEW)**
- Data integrity checks

---

## Example Usage Scenarios

### Scenario 1: Conservative Investor (100% PPR)

```json
{
  "ppr_allocations": [{"ppr_id": "uuid", "allocation_percentage": 100}],
  "bitcoin_percentage": 0,
  "initial_investment": 10000,
  "start_date": "2020-01-01",
  "rebalancing_frequency": "none"
}
```

**Expected:** Low volatility, modest returns, minimal drawdown

---

### Scenario 2: Moderate Investor (10% Bitcoin)

```json
{
  "ppr_allocations": [{"ppr_id": "uuid", "allocation_percentage": 90}],
  "bitcoin_percentage": 10,
  "initial_investment": 10000,
  "start_date": "2020-01-01",
  "rebalancing_frequency": "quarterly"
}
```

**Expected:** Slightly higher returns with controlled volatility

---

### Scenario 3: Aggressive Investor (30% Bitcoin)

```json
{
  "ppr_allocations": [{"ppr_id": "uuid", "allocation_percentage": 70}],
  "bitcoin_percentage": 30,
  "initial_investment": 10000,
  "start_date": "2020-01-01",
  "rebalancing_frequency": "quarterly"
}
```

**Expected:** Higher returns but increased volatility and drawdown

---

## Rebalancing Strategies

| Frequency | Description | Use Case |
|-----------|-------------|----------|
| **none** | Buy and hold - no rebalancing | Long-term, low-maintenance |
| **monthly** | Rebalance every ~30 days | Active management, minimize drift |
| **quarterly** | Rebalance every ~90 days | **Recommended** - balanced approach |
| **yearly** | Rebalance every ~365 days | Minimize transaction costs |

---

## How Portfolio Calculation Works

1. **Data Fetching**
   - Retrieves historical PPR quota values from database
   - Retrieves historical Bitcoin prices (EUR)
   - Aligns data to common dates (handles missing data)

2. **Initial Allocation**
   - Calculates units of each asset based on initial investment
   - Allocates according to specified percentages

3. **Rebalancing** (if enabled)
   - Checks if rebalancing is needed based on frequency
   - Sells/buys to restore target allocations
   - Maintains portfolio value while adjusting units

4. **Metrics Calculation**
   - Calculates daily returns from portfolio values
   - Computes volatility (annualized standard deviation)
   - Calculates Sharpe ratio (return/risk)
   - Identifies maximum drawdown and duration
   - Aggregates monthly statistics

5. **Response Generation**
   - Returns complete metrics
   - Provides historical data points for charting
   - Breaks down contribution by asset

---

## Best Practices

### 1. Date Range Selection
- **Minimum:** 1 year for meaningful metrics
- **Recommended:** 3-5 years for stable Sharpe ratio
- **Maximum:** Limited by available historical data

### 2. Allocation Validation
- Total allocation MUST equal 100%
- Allocations are validated automatically
- Can mix multiple PPRs with Bitcoin

### 3. Rebalancing Frequency
- More frequent = stays closer to target allocation
- Less frequent = lower transaction costs
- **Quarterly is a good default**

### 4. Error Handling
- API returns clear error messages
- 404: PPR not found
- 400: Invalid date range
- 422: Insufficient historical data

---

## Next Steps (Phase 4)

With the portfolio calculation engine complete, the next phase is:

1. **React Frontend** - Build user interface
2. **Interactive Charts** - Visualize portfolio performance
3. **Strategy Comparison UI** - Side-by-side comparison view
4. **Export Functionality** - Download results as PDF/CSV

---

## Troubleshooting

### "PPR not found" error
- Ensure database is seeded: `cd data/seeds && python setup_database.py`
- Get valid PPR IDs from `/api/v1/pprs` endpoint

### "Insufficient historical data" error
- Choose a date range within available data
- Check Bitcoin data availability: `/api/v1/bitcoin/historical`
- Check PPR data: `/api/v1/pprs/{id}/historical`

### "Allocations don't sum to 100%" error
- Ensure PPR allocations + Bitcoin percentage = 100%
- Example: 70% PPR + 30% Bitcoin = 100% ✓

### Calculation is slow
- Reduce date range for faster results
- Database indexes are optimized for common queries
- Consider caching results for identical requests

---

## Technical Details

### Performance
- Calculations use **Pandas** for efficient time-series operations
- **NumPy** for statistical calculations
- Async database queries for better performance

### Accuracy
- Uses **Decimal** type for financial calculations (avoids floating-point errors)
- Properly handles missing data with forward-fill
- Validates data integrity before calculation

### Testing
- Unit tests cover core calculation logic
- Integration tests verify API endpoints
- Test cases include edge cases (100% PPR, 100% Bitcoin, missing data)

---

## Example API Response

```json
{
  "portfolio_config": { ... },
  "metrics": {
    "total_return": 5234.67,
    "total_return_percentage": 52.35,
    "annualized_return": 12.45,
    "cagr": 12.45,
    "volatility": 15.32,
    "sharpe_ratio": 0.81,
    "sortino_ratio": 1.12,
    "max_drawdown": -18.45,
    "max_drawdown_duration_days": 124,
    "final_value": 15234.67,
    "best_month": 8.23,
    "worst_month": -12.45,
    "positive_months": 38,
    "total_months": 48
  },
  "historical_data": [
    {
      "date": "2020-01-01",
      "portfolio_value": 10000.00,
      "ppr_value": 7000.00,
      "bitcoin_value": 3000.00,
      "total_return": 0.00,
      "drawdown": 0.00
    },
    ...
  ],
  "allocation_breakdown": [
    {
      "ppr_id": "uuid",
      "ppr_name": "GNB PPR Reforma",
      "allocation_percentage": 70.0,
      "current_value": 10664.27,
      "contribution_to_return": 6.64
    }
  ],
  "calculation_date": "2025-01-18"
}
```

---

**Phase 3 Status:** ✅ **COMPLETE**

Ready for Phase 4: Frontend Implementation
