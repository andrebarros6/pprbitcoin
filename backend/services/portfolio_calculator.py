"""
Portfolio calculation service with financial metrics and backtesting
"""
import pandas as pd
import numpy as np
from datetime import date, datetime
from decimal import Decimal
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from utils.irr import xirr
from models.ppr import PPR, PPRHistoricalData
from models.bitcoin import BitcoinHistoricalData
from models.portfolio import (
    PortfolioCalculationRequest,
    PortfolioCalculationResponse,
    PortfolioReference,
    PerformanceMetrics,
    HistoricalDataPoint,
    AllocationBreakdown,
    InsufficientDataError,
    InvalidDateRangeError,
    PPRNotFoundError,
)


class PortfolioCalculator:
    """
    Service for calculating portfolio performance and metrics
    """

    def __init__(self, db: Session):
        """
        Initialize portfolio calculator

        Args:
            db: Database session
        """
        self.db = db
        self.risk_free_rate = Decimal("0")  # Can be configurable

    def calculate_portfolio(
        self, request: PortfolioCalculationRequest
    ) -> PortfolioCalculationResponse:
        """
        Main method to calculate portfolio performance

        Args:
            request: Portfolio calculation request

        Returns:
            Portfolio calculation response with all metrics

        Raises:
            PPRNotFoundError: If any PPR ID is not found
            InsufficientDataError: If insufficient historical data
            InvalidDateRangeError: If date range is invalid
        """
        # Validate date range
        end_date = request.end_date or date.today()
        if request.start_date >= end_date:
            raise InvalidDateRangeError(
                f"Start date {request.start_date} must be before end date {end_date}"
            )

        # Fetch and validate PPRs
        pprs = self._fetch_and_validate_pprs(request.ppr_allocations)

        # Fetch historical data
        ppr_data = self._fetch_ppr_historical_data(
            request.ppr_allocations, request.start_date, end_date
        )
        bitcoin_data = self._fetch_bitcoin_historical_data(request.start_date, end_date)

        # Merge and align data
        aligned_data = self._align_historical_data(ppr_data, bitcoin_data)

        if aligned_data.empty:
            raise InsufficientDataError(
                f"No overlapping data found for date range {request.start_date} to {end_date}"
            )

        # Calculate portfolio values over time
        portfolio_values = self._calculate_portfolio_values(
            aligned_data, request, pprs
        )

        # Calculate performance metrics
        metrics = self._calculate_performance_metrics(
            portfolio_values, request.initial_investment
        )

        # Build historical data points
        historical_data = self._build_historical_data_points(portfolio_values)

        # Build allocation breakdown
        allocation_breakdown = self._build_allocation_breakdown(
            request, pprs, portfolio_values
        )

        # The counterfactual: the same savings plan without Bitcoin. This is
        # the question the tool exists to answer, so it is computed alongside
        # rather than left to the caller to request separately.
        without_bitcoin = self._calculate_without_bitcoin(
            request, aligned_data, pprs
        )

        return PortfolioCalculationResponse(
            portfolio_config=request,
            metrics=metrics,
            historical_data=historical_data,
            allocation_breakdown=allocation_breakdown,
            calculation_date=date.today(),
            without_bitcoin=without_bitcoin,
        )

    def _calculate_without_bitcoin(
        self,
        request: PortfolioCalculationRequest,
        aligned_data: pd.DataFrame,
        pprs: Dict[str, PPR],
    ) -> Optional[PortfolioReference]:
        """
        Re-run the same plan with the Bitcoin share redistributed across the
        PPR funds, so the two lines differ only in holding Bitcoin or not.

        Returns None when there is no Bitcoin to remove, or when the PPR
        weights cannot be renormalised (a 100% Bitcoin portfolio has no
        PPR-only equivalent to compare against).

        Args:
            request: The original portfolio request
            aligned_data: Already-aligned price data, reused so both runs
                cover exactly the same dates
            pprs: Dictionary of PPR objects

        Returns:
            The comparison portfolio, or None
        """
        if request.bitcoin_percentage <= 0:
            return None

        total_ppr = sum(a.allocation_percentage for a in request.ppr_allocations)
        if total_ppr <= 0:
            return None

        # Scale the PPR weights up to fill the whole portfolio.
        scale = Decimal("100") / total_ppr
        ppr_only = request.model_copy(
            update={
                "bitcoin_percentage": Decimal("0"),
                "ppr_allocations": [
                    a.model_copy(
                        update={"allocation_percentage": a.allocation_percentage * scale}
                    )
                    for a in request.ppr_allocations
                ],
            }
        )

        values = self._calculate_portfolio_values(aligned_data, ppr_only, pprs)
        metrics = self._calculate_performance_metrics(
            values, ppr_only.initial_investment
        )
        history = self._build_historical_data_points(values)

        return PortfolioReference(
            label="Sem Bitcoin (só PPR)",
            metrics=metrics,
            historical_data=history,
        )

    def _fetch_and_validate_pprs(
        self, ppr_allocations: List
    ) -> Dict[str, PPR]:
        """
        Fetch PPRs from database and validate they exist

        Args:
            ppr_allocations: List of PPR allocations

        Returns:
            Dictionary mapping PPR ID to PPR object

        Raises:
            PPRNotFoundError: If any PPR is not found
        """
        pprs = {}
        for allocation in ppr_allocations:
            ppr = self.db.query(PPR).filter(PPR.id == allocation.ppr_id).first()
            if not ppr:
                raise PPRNotFoundError(f"PPR with ID {allocation.ppr_id} not found")
            pprs[str(allocation.ppr_id)] = ppr
        return pprs

    def _fetch_ppr_historical_data(
        self, ppr_allocations: List, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """
        Fetch PPR historical data and combine into a single DataFrame

        Args:
            ppr_allocations: List of PPR allocations
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with PPR prices indexed by date
        """
        ppr_dataframes = []

        for allocation in ppr_allocations:
            # Query historical data
            historical_data = (
                self.db.query(PPRHistoricalData)
                .filter(
                    and_(
                        PPRHistoricalData.ppr_id == allocation.ppr_id,
                        PPRHistoricalData.data >= start_date,
                        PPRHistoricalData.data <= end_date,
                    )
                )
                .order_by(PPRHistoricalData.data.asc())
                .all()
            )

            if not historical_data:
                raise InsufficientDataError(
                    f"No historical data found for PPR {allocation.ppr_id} "
                    f"in date range {start_date} to {end_date}"
                )

            # Convert to DataFrame
            df = pd.DataFrame(
                [
                    {
                        "data": item.data,
                        f"ppr_{allocation.ppr_id}": float(item.valor_quota),
                    }
                    for item in historical_data
                ]
            )
            df["data"] = pd.to_datetime(df["data"])
            df.set_index("data", inplace=True)
            ppr_dataframes.append(df)

        # Merge all PPR dataframes
        if ppr_dataframes:
            combined_df = pd.concat(ppr_dataframes, axis=1)
            return combined_df
        else:
            return pd.DataFrame()

    def _fetch_bitcoin_historical_data(
        self, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """
        Fetch Bitcoin historical data

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with Bitcoin prices indexed by date
        """
        historical_data = (
            self.db.query(BitcoinHistoricalData)
            .filter(
                and_(
                    BitcoinHistoricalData.data >= start_date,
                    BitcoinHistoricalData.data <= end_date,
                )
            )
            .order_by(BitcoinHistoricalData.data.asc())
            .all()
        )

        if not historical_data:
            # If no Bitcoin allocation, this is okay
            return pd.DataFrame()

        df = pd.DataFrame(
            [
                {"data": item.data, "bitcoin_price": float(item.preco_eur)}
                for item in historical_data
            ]
        )
        df["data"] = pd.to_datetime(df["data"])
        df.set_index("data", inplace=True)
        return df

    def _align_historical_data(
        self, ppr_data: pd.DataFrame, bitcoin_data: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Align PPR and Bitcoin historical data to common dates

        Args:
            ppr_data: DataFrame with PPR prices
            bitcoin_data: DataFrame with Bitcoin prices

        Returns:
            Aligned DataFrame with all data
        """
        if bitcoin_data.empty:
            # No Bitcoin data, just use PPR data
            return ppr_data

        # Merge dataframes. concat unions the two date indexes -- PPR quotes
        # only on business days, Bitcoin trades every day -- and returns them
        # in concatenation order, not date order. Sorting is essential: an
        # unsorted index makes ffill carry values backwards in time and makes
        # every daily return meaningless.
        combined = pd.concat([ppr_data, bitcoin_data], axis=1).sort_index()

        # Forward fill missing values (use last known price)
        combined = combined.ffill()

        # Drop rows with any remaining NaN (beginning of series)
        combined = combined.dropna()

        # Trailing days after the last PPR quote would otherwise repeat that
        # quote while Bitcoin keeps moving, which reads as a real divergence.
        last_ppr_quote = ppr_data.dropna(how="all").index.max()
        combined = combined[combined.index <= last_ppr_quote]

        return combined

    def _calculate_portfolio_values(
        self,
        aligned_data: pd.DataFrame,
        request: PortfolioCalculationRequest,
        pprs: Dict[str, PPR],
    ) -> pd.DataFrame:
        """
        Calculate portfolio values over time with rebalancing

        Args:
            aligned_data: Aligned historical data
            request: Portfolio calculation request
            pprs: Dictionary of PPR objects

        Returns:
            DataFrame with portfolio values over time
        """
        initial_investment = float(request.initial_investment)
        bitcoin_pct = float(request.bitcoin_percentage) / 100

        # Calculate initial allocation
        portfolio_values = []
        dates = aligned_data.index

        # Initial units purchased
        initial_units = {}
        initial_date = dates[0]

        # Calculate PPR units
        for allocation in request.ppr_allocations:
            ppr_id = str(allocation.ppr_id)
            allocation_pct = float(allocation.allocation_percentage) / 100
            allocation_amount = initial_investment * allocation_pct
            initial_price = float(aligned_data.loc[initial_date, f"ppr_{allocation.ppr_id}"])
            initial_units[f"ppr_{allocation.ppr_id}"] = allocation_amount / initial_price

        # Calculate Bitcoin units
        if bitcoin_pct > 0:
            bitcoin_allocation = initial_investment * bitcoin_pct
            initial_bitcoin_price = float(aligned_data.loc[initial_date, "bitcoin_price"])
            initial_units["bitcoin"] = bitcoin_allocation / initial_bitcoin_price
        else:
            initial_units["bitcoin"] = 0

        # Track current units (will change with rebalancing)
        current_units = initial_units.copy()
        last_rebalance_date = initial_date

        # Contributions are cash paid in after the start, so the initial
        # investment is the first entry in the invested-capital running total
        # and the first cashflow for the IRR.
        contribution_amount = float(request.contribution_amount)
        contribution_frequency = request.contribution_frequency
        invested_capital = initial_investment
        last_contribution_date = initial_date
        cashflows = [(initial_date.date(), -initial_investment)]

        # Calculate portfolio value for each date
        for current_date in dates:
            # Buy in before valuing, so the contribution is reflected on the
            # day it is made rather than a day late.
            if current_date != initial_date and self._should_contribute(
                current_date, last_contribution_date, contribution_frequency
            ):
                current_units = self._invest_contribution(
                    aligned_data,
                    current_date,
                    current_units,
                    request,
                    contribution_amount,
                )
                invested_capital += contribution_amount
                last_contribution_date = current_date
                cashflows.append((current_date.date(), -contribution_amount))

            # Check if rebalancing is needed
            if self._should_rebalance(
                current_date, last_rebalance_date, request.rebalancing_frequency
            ):
                current_units = self._rebalance_portfolio(
                    aligned_data,
                    current_date,
                    current_units,
                    request,
                )
                last_rebalance_date = current_date

            # Calculate current portfolio value
            ppr_value = 0
            for allocation in request.ppr_allocations:
                col_name = f"ppr_{allocation.ppr_id}"
                current_price = float(aligned_data.loc[current_date, col_name])
                ppr_value += current_units[col_name] * current_price

            bitcoin_value = 0
            if "bitcoin_price" in aligned_data.columns and bitcoin_pct > 0:
                bitcoin_price = float(aligned_data.loc[current_date, "bitcoin_price"])
                bitcoin_value = current_units["bitcoin"] * bitcoin_price

            total_value = ppr_value + bitcoin_value

            portfolio_values.append(
                {
                    "date": current_date.date(),
                    "ppr_value": ppr_value,
                    "bitcoin_value": bitcoin_value,
                    "total_value": total_value,
                    "invested_capital": invested_capital,
                }
            )

        # The IRR treats the closing portfolio value as though it were
        # withdrawn on the final date, which is what makes the paid-in
        # cashflows solvable for a rate.
        if portfolio_values:
            cashflows.append(
                (portfolio_values[-1]["date"], portfolio_values[-1]["total_value"])
            )

        # Carried on the frame rather than on self, so that calculating a
        # comparison portfolio on the same calculator cannot overwrite the
        # main result's cashflows.
        frame = pd.DataFrame(portfolio_values)
        frame.attrs["cashflows"] = cashflows
        return frame

    def _should_contribute(
        self, current_date: datetime, last_contribution: datetime, frequency: str
    ) -> bool:
        """
        Check if a recurring contribution falls due on this date.

        Args:
            current_date: Current date
            last_contribution: Date of the previous contribution
            frequency: Contribution frequency

        Returns:
            True if a contribution should be invested
        """
        if frequency == "none":
            return False

        time_diff = (current_date - last_contribution).days

        if frequency == "monthly":
            return time_diff >= 30
        elif frequency == "quarterly":
            return time_diff >= 90

        return False

    def _invest_contribution(
        self,
        aligned_data: pd.DataFrame,
        contribution_date: datetime,
        current_units: Dict,
        request: PortfolioCalculationRequest,
        amount: float,
    ) -> Dict:
        """
        Buy units with a recurring contribution at target allocations.

        Unlike rebalancing this only adds units -- it never sells to correct
        drift, which is what a saver paying into a plan actually does.

        Args:
            aligned_data: Aligned historical data
            contribution_date: Date the money is invested
            current_units: Units held before the contribution
            request: Portfolio request with target allocations
            amount: Cash being invested

        Returns:
            Units held after the contribution
        """
        new_units = dict(current_units)
        bitcoin_pct = float(request.bitcoin_percentage) / 100

        for allocation in request.ppr_allocations:
            col_name = f"ppr_{allocation.ppr_id}"
            allocation_pct = float(allocation.allocation_percentage) / 100
            price = float(aligned_data.loc[contribution_date, col_name])
            if price > 0:
                new_units[col_name] += (amount * allocation_pct) / price

        if "bitcoin_price" in aligned_data.columns and bitcoin_pct > 0:
            bitcoin_price = float(aligned_data.loc[contribution_date, "bitcoin_price"])
            if bitcoin_price > 0:
                new_units["bitcoin"] += (amount * bitcoin_pct) / bitcoin_price

        return new_units

    def _should_rebalance(
        self, current_date: datetime, last_rebalance: datetime, frequency: str
    ) -> bool:
        """
        Check if portfolio should be rebalanced

        Args:
            current_date: Current date
            last_rebalance: Last rebalancing date
            frequency: Rebalancing frequency

        Returns:
            True if should rebalance
        """
        if frequency == "none":
            return False

        time_diff = (current_date - last_rebalance).days

        if frequency == "monthly":
            return time_diff >= 30
        elif frequency == "quarterly":
            return time_diff >= 90
        elif frequency == "yearly":
            return time_diff >= 365

        return False

    def _rebalance_portfolio(
        self,
        aligned_data: pd.DataFrame,
        rebalance_date: datetime,
        current_units: Dict,
        request: PortfolioCalculationRequest,
    ) -> Dict:
        """
        Rebalance portfolio to target allocations

        Args:
            aligned_data: Aligned historical data
            rebalance_date: Date to rebalance
            current_units: Current units held
            request: Portfolio request with target allocations

        Returns:
            New units after rebalancing
        """
        # Calculate current total value
        total_value = 0
        for allocation in request.ppr_allocations:
            col_name = f"ppr_{allocation.ppr_id}"
            current_price = float(aligned_data.loc[rebalance_date, col_name])
            total_value += current_units[col_name] * current_price

        if "bitcoin_price" in aligned_data.columns:
            bitcoin_price = float(aligned_data.loc[rebalance_date, "bitcoin_price"])
            total_value += current_units["bitcoin"] * bitcoin_price

        # Calculate new units based on target allocations
        new_units = {}
        bitcoin_pct = float(request.bitcoin_percentage) / 100

        for allocation in request.ppr_allocations:
            col_name = f"ppr_{allocation.ppr_id}"
            allocation_pct = float(allocation.allocation_percentage) / 100
            target_value = total_value * allocation_pct
            current_price = float(aligned_data.loc[rebalance_date, col_name])
            new_units[col_name] = target_value / current_price

        # Rebalance Bitcoin
        if "bitcoin_price" in aligned_data.columns and bitcoin_pct > 0:
            target_bitcoin_value = total_value * bitcoin_pct
            bitcoin_price = float(aligned_data.loc[rebalance_date, "bitcoin_price"])
            new_units["bitcoin"] = target_bitcoin_value / bitcoin_price
        else:
            new_units["bitcoin"] = 0

        return new_units

    def _calculate_performance_metrics(
        self, portfolio_values: pd.DataFrame, initial_investment: Decimal
    ) -> PerformanceMetrics:
        """
        Calculate all performance metrics

        Args:
            portfolio_values: DataFrame with portfolio values over time
            initial_investment: Initial investment amount

        Returns:
            Performance metrics
        """
        initial_value = float(initial_investment)
        final_value = portfolio_values.iloc[-1]["total_value"]
        values = portfolio_values["total_value"].values

        # Money paid in over the whole period. Without contributions this is
        # just the initial investment, so the lump-sum maths is unchanged.
        if "invested_capital" in portfolio_values.columns:
            invested_capital = float(portfolio_values.iloc[-1]["invested_capital"])
        else:
            invested_capital = initial_value
        has_contributions = invested_capital > initial_value + 1e-9

        # Total returns, measured against everything paid in. Dividing by the
        # initial investment alone would count contributions as though they
        # were profit.
        total_return = final_value - invested_capital
        total_return_pct = (total_return / invested_capital) * 100

        # Calculate returns series. Contributions add cash to the portfolio
        # without being a gain, so they are removed before measuring the
        # period-on-period return -- otherwise every payday looks like a rally
        # and volatility, Sharpe and drawdown are all overstated.
        value_series = pd.Series(values, dtype="float64")
        if has_contributions:
            capital_series = pd.Series(
                portfolio_values["invested_capital"].values, dtype="float64"
            )
            cash_added = capital_series.diff().fillna(0.0)
            returns = (
                (value_series - cash_added) / value_series.shift(1) - 1.0
            ).replace([np.inf, -np.inf], np.nan).dropna()
        else:
            returns = value_series.pct_change().dropna()

        # Number of periods
        num_days = len(portfolio_values)
        num_years = num_days / 365.25

        # Money-weighted return. This is the correct headline figure once
        # contributions exist, because it accounts for how long each euro was
        # actually invested.
        irr_rate = xirr(portfolio_values.attrs.get("cashflows", []))
        irr_pct = round(irr_rate * 100, 2) if irr_rate is not None else None

        # CAGR compounds a single starting sum, so it is only meaningful for a
        # lump sum. With contributions it is reported as the time-weighted
        # growth implied by the IRR rather than a ratio of two numbers that no
        # longer describe the same pot of money.
        if has_contributions:
            cagr = irr_pct if irr_pct is not None else 0
        elif num_years > 0:
            cagr = (((final_value / initial_value) ** (1 / num_years)) - 1) * 100
        else:
            cagr = 0

        # Annualized return
        annualized_return = cagr

        # Volatility (annualized)
        volatility = returns.std() * np.sqrt(252) * 100  # Assuming daily data, 252 trading days

        # Sharpe Ratio (assuming 0% risk-free rate)
        sharpe_ratio = (annualized_return / volatility) if volatility > 0 else 0

        # Sortino Ratio (downside deviation)
        downside_returns = returns[returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(252) * 100
        sortino_ratio = (annualized_return / downside_deviation) if downside_deviation > 0 else 0

        # Maximum Drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max * 100
        max_drawdown = drawdown.min()

        # Maximum Drawdown Duration
        # Find the longest period underwater
        is_underwater = drawdown < -0.01  # More than 0.01% drawdown
        if is_underwater.any():
            # Group consecutive underwater periods
            underwater_periods = (is_underwater != is_underwater.shift()).cumsum()
            max_dd_duration = (
                is_underwater.groupby(underwater_periods).sum().max()
                if is_underwater.any()
                else 0
            )
        else:
            max_dd_duration = 0

        # Monthly statistics (approximate from daily data)
        # Group by month
        portfolio_values["month"] = pd.to_datetime(portfolio_values["date"]).dt.to_period("M")
        monthly_returns = (
            portfolio_values.groupby("month")["total_value"]
            .last()
            .pct_change()
            .dropna()
            * 100
        )

        best_month = monthly_returns.max() if len(monthly_returns) > 0 else 0
        worst_month = monthly_returns.min() if len(monthly_returns) > 0 else 0
        positive_months = (monthly_returns > 0).sum() if len(monthly_returns) > 0 else 0
        total_months = len(monthly_returns)

        return PerformanceMetrics(
            total_return=Decimal(str(round(total_return, 2))),
            total_return_percentage=Decimal(str(round(total_return_pct, 2))),
            annualized_return=Decimal(str(round(annualized_return, 2))),
            cagr=Decimal(str(round(cagr, 2))),
            volatility=Decimal(str(round(volatility, 2))),
            sharpe_ratio=Decimal(str(round(sharpe_ratio, 2))),
            sortino_ratio=Decimal(str(round(sortino_ratio, 2))),
            max_drawdown=Decimal(str(round(max_drawdown, 2))),
            max_drawdown_duration_days=int(max_dd_duration),
            final_value=Decimal(str(round(final_value, 2))),
            invested_capital=Decimal(str(round(invested_capital, 2))),
            irr=Decimal(str(irr_pct)) if irr_pct is not None else None,
            is_money_weighted=has_contributions,
            best_month=Decimal(str(round(best_month, 2))),
            worst_month=Decimal(str(round(worst_month, 2))),
            positive_months=int(positive_months),
            total_months=int(total_months),
        )

    def _build_historical_data_points(
        self, portfolio_values: pd.DataFrame
    ) -> List[HistoricalDataPoint]:
        """
        Build historical data points for response

        Args:
            portfolio_values: DataFrame with portfolio values

        Returns:
            List of historical data points
        """
        initial_value = portfolio_values.iloc[0]["total_value"]
        # Peaks are tracked as value per euro invested (see the loop below),
        # so the starting peak is 1.0, not a euro amount.
        peak_value = 1.0

        has_capital = "invested_capital" in portfolio_values.columns

        historical_data = []
        for _, row in portfolio_values.iterrows():
            total_value = row["total_value"]
            # Measure the gain against money paid in so far, otherwise a
            # contribution shows up on the chart as an instant profit.
            invested_so_far = (
                float(row["invested_capital"]) if has_capital else initial_value
            )
            total_return = (
                ((total_value - invested_so_far) / invested_so_far) * 100
                if invested_so_far > 0
                else 0
            )

            # Track the peak on value-per-euro-invested, not raw value. A
            # contribution lifts the raw value without being a gain, which
            # would otherwise reset the peak and hide a real drawdown.
            indexed_value = (
                total_value / invested_so_far if invested_so_far > 0 else 0
            )
            if indexed_value > peak_value:
                peak_value = indexed_value

            # Calculate drawdown
            drawdown = (
                ((indexed_value - peak_value) / peak_value) * 100
                if peak_value > 0
                else 0
            )

            historical_data.append(
                HistoricalDataPoint(
                    data=row["date"],
                    portfolio_value=Decimal(str(round(total_value, 2))),
                    ppr_value=Decimal(str(round(row["ppr_value"], 2))),
                    bitcoin_value=Decimal(str(round(row["bitcoin_value"], 2))),
                    invested_capital=Decimal(str(round(invested_so_far, 2))),
                    total_return=Decimal(str(round(total_return, 2))),
                    drawdown=Decimal(str(round(drawdown, 2))),
                )
            )

        return historical_data

    def _build_allocation_breakdown(
        self,
        request: PortfolioCalculationRequest,
        pprs: Dict[str, PPR],
        portfolio_values: pd.DataFrame,
    ) -> List[AllocationBreakdown]:
        """
        Build allocation breakdown for response

        Args:
            request: Portfolio calculation request
            pprs: Dictionary of PPR objects
            portfolio_values: DataFrame with portfolio values

        Returns:
            List of allocation breakdowns
        """
        initial_value = float(request.initial_investment)
        final_row = portfolio_values.iloc[-1]
        final_value = final_row["total_value"]

        breakdown = []

        # PPR breakdown
        for allocation in request.ppr_allocations:
            ppr_id = str(allocation.ppr_id)
            ppr = pprs[ppr_id]
            allocation_pct = allocation.allocation_percentage
            current_value = (final_row["ppr_value"] * float(allocation_pct)) / float(sum(
                a.allocation_percentage for a in request.ppr_allocations
            ))
            contribution = ((current_value - (initial_value * float(allocation_pct) / 100)) / initial_value) * 100

            breakdown.append(
                AllocationBreakdown(
                    ppr_id=allocation.ppr_id,
                    ppr_name=ppr.nome,
                    allocation_percentage=allocation_pct,
                    current_value=Decimal(str(round(current_value, 2))),
                    contribution_to_return=Decimal(str(round(contribution, 2))),
                )
            )

        return breakdown
