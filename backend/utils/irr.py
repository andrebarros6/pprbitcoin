"""
Money-weighted return (XIRR) over irregularly dated cashflows.

Time-weighted measures such as CAGR answer "how did the fund perform?".
They are the wrong tool once the investor pays money in over time, because
they ignore how much capital was exposed to each period. XIRR answers the
question the saver actually asks: "what annual rate did *my* money earn?"

Newton-Raphson converges fast but can diverge on the shapes real
contribution schedules produce, so a bracketing bisection is used as a
fallback and the result is always verified before being returned.
"""
import datetime as dt
from typing import List, Optional, Sequence, Tuple

DAYS_PER_YEAR = 365.25  # matches the CAGR convention used by the calculator

# A rate at or below -100% would mean losing more than everything paid in;
# the discount factor is undefined there, so the search is bounded just above.
_MIN_RATE = -0.9999
_MAX_RATE = 100.0  # 10,000% a year -- far beyond any plausible portfolio
_TOLERANCE = 1e-7
_MAX_ITERATIONS = 100


def _net_present_value(rate: float, years: Sequence[float], amounts: Sequence[float]) -> float:
    """NPV of the cashflows at the given annual rate."""
    total = 0.0
    for t, amount in zip(years, amounts):
        total += amount / ((1.0 + rate) ** t)
    return total


def _npv_derivative(rate: float, years: Sequence[float], amounts: Sequence[float]) -> float:
    """d(NPV)/d(rate), used by Newton-Raphson."""
    total = 0.0
    for t, amount in zip(years, amounts):
        if t == 0.0:
            continue
        total -= t * amount / ((1.0 + rate) ** (t + 1.0))
    return total


def _prepare(
    cashflows: Sequence[Tuple[dt.date, float]]
) -> Optional[Tuple[List[float], List[float]]]:
    """
    Convert dated cashflows into (years-from-start, amount) arrays.

    Returns None when no rate can exist: fewer than two flows, or flows that
    are all one sign. Without both an outflow and an inflow the NPV never
    crosses zero and any "solution" would be an artefact.
    """
    if len(cashflows) < 2:
        return None

    ordered = sorted(cashflows, key=lambda item: item[0])
    start = ordered[0][0]

    years = [(d - start).days / DAYS_PER_YEAR for d, _ in ordered]
    amounts = [amount for _, amount in ordered]

    if not any(a > 0 for a in amounts) or not any(a < 0 for a in amounts):
        return None

    return years, amounts


def _bisect(years: Sequence[float], amounts: Sequence[float]) -> Optional[float]:
    """
    Find a rate by bracketing a sign change in NPV.

    Slower than Newton-Raphson but cannot diverge, which is why it backs it up.
    """
    low, high = _MIN_RATE, _MAX_RATE
    npv_low = _net_present_value(low, years, amounts)
    npv_high = _net_present_value(high, years, amounts)

    if npv_low * npv_high > 0:
        # No sign change across the bracket, so no root to find within it.
        return None

    for _ in range(_MAX_ITERATIONS * 2):
        mid = (low + high) / 2.0
        npv_mid = _net_present_value(mid, years, amounts)

        if abs(npv_mid) < _TOLERANCE or (high - low) < _TOLERANCE:
            return mid

        if npv_low * npv_mid < 0:
            high, npv_high = mid, npv_mid
        else:
            low, npv_low = mid, npv_mid

    return (low + high) / 2.0


def xirr(cashflows: Sequence[Tuple[dt.date, float]], guess: float = 0.1) -> Optional[float]:
    """
    Annualised money-weighted rate of return for dated cashflows.

    Args:
        cashflows: (date, amount) pairs. Money paid in is negative, money
            taken out -- including the final portfolio value -- is positive.
        guess: starting point for Newton-Raphson.

    Returns:
        The annual rate as a decimal fraction (0.07 == 7% a year), or None
        when the cashflows admit no meaningful rate.
    """
    prepared = _prepare(cashflows)
    if prepared is None:
        return None
    years, amounts = prepared

    rate = guess
    for _ in range(_MAX_ITERATIONS):
        if rate <= _MIN_RATE:
            break

        npv = _net_present_value(rate, years, amounts)
        if abs(npv) < _TOLERANCE:
            return rate

        derivative = _npv_derivative(rate, years, amounts)
        if derivative == 0.0:
            break

        step = npv / derivative
        next_rate = rate - step

        if not (-1e6 < next_rate < 1e6):
            break
        rate = next_rate
    else:
        # Ran out of iterations without converging.
        rate = None

    # Accept Newton's answer only if it genuinely solves the equation and is
    # in range; otherwise fall back to bisection. Newton can converge onto a
    # value that is precise but wrong when the curve is awkward.
    if rate is not None and _MIN_RATE < rate < _MAX_RATE:
        if abs(_net_present_value(rate, years, amounts)) < 1e-4:
            return rate

    return _bisect(years, amounts)
